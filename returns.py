#!/usr/bin/env python

import logging
import sys
import itertools
import functools
import operator
import math
import collections
import datetime
import decimal
from dateutil.relativedelta import relativedelta
from pprint import pprint
from scipy import optimize
import beancount.loader
import beancount.utils
import beancount.core
import beancount.core.realization
import beancount.core.data
import beancount.parser

# TODO: investor return (money-weighted)
# TODO: portfolio returns (time-weighted) for 1-month, 3-months, year-to-date, 1-year, 3-years, 5-years, and 10-years
# TODO: growth of $10,000 chart
# TODO: TEST: leaving off the year & using all the data fails

# https://github.com/peliot/XIRR-and-XNPV/blob/master/financial.py

def xnpv(rate,cashflows):
    """
    Calculate the net present value of a series of cashflows at irregular intervals.
    Arguments
    ---------
    * rate: the discount rate to be applied to the cash flows
    * cashflows: a list object in which each element is a tuple of the form (date, amount), where date is a python datetime.date object and amount is an integer or floating point number. Cash outflows (investments) are represented with negative amounts, and cash inflows (returns) are positive amounts.
    
    Returns
    -------
    * returns a single value which is the NPV of the given cash flows.
    Notes
    ---------------
    * The Net Present Value is the sum of each of cash flows discounted back to the date of the first cash flow. The discounted value of a given cash flow is A/(1+r)**(t-t0), where A is the amount, r is the discout rate, and (t-t0) is the time in years from the date of the first cash flow in the series (t0) to the date of the cash flow being added to the sum (t).  
    * This function is equivalent to the Microsoft Excel function of the same name. 
    """

    chron_order = sorted(cashflows, key = lambda x: x[0])
    t0 = chron_order[0][0] #t0 is the date of the first cash flow

    return sum([cf/(1+rate)**((t-t0).days/365.0) for (t,cf) in chron_order])

def xirr(cashflows,guess=0.1):
    """
    Calculate the Internal Rate of Return of a series of cashflows at irregular intervals.
    Arguments
    ---------
    * cashflows: a list object in which each element is a tuple of the form (date, amount), where date is a python datetime.date object and amount is an integer or floating point number. Cash outflows (investments) are represented with negative amounts, and cash inflows (returns) are positive amounts.
    * guess (optional, default = 0.1): a guess at the solution to be used as a starting point for the numerical solution. 
    Returns
    --------
    * Returns the IRR as a single value
    
    Notes
    ----------------
    * The Internal Rate of Return (IRR) is the discount rate at which the Net Present Value (NPV) of a series of cash flows is equal to zero. The NPV of the series of cash flows is determined using the xnpv function in this module. The discount rate at which NPV equals zero is found using the secant method of numerical solution. 
    * This function is equivalent to the Microsoft Excel function of the same name.
    * For users that do not have the scipy module installed, there is an alternate version (commented out) that uses the secant_method function defined in the module rather than the scipy.optimize module's numerical solver. Both use the same method of calculation so there should be no difference in performance, but the secant_method function does not fail gracefully in cases where there is no solution, so the scipy.optimize.newton version is preferred.
    """
    return optimize.newton(lambda r: xnpv(r,cashflows),guess)

def fmt_d(n):
    return '${:,.0f}'.format(n)

def fmt_pct(n):
    return '{0:.2f}%'.format(n*100)

def add_position(p, inventory):
    if isinstance(p, beancount.core.data.Posting):
        inventory.add_position(p)
    elif isinstance(p, beancount.core.data.TxnPosting):
        inventory.add_position(p.posting)
    else:
        raise Exception("Not a Posting or TxnPosting", p)

def get_date(p):
    if isinstance(p, beancount.core.data.Posting):
        return p.date
    elif isinstance(p, beancount.core.data.TxnPosting):
        return p.txn.date
    else:
        raise Exception("Not a Posting or TxnPosting", p)

def only_postings(p):
    if isinstance(p, beancount.core.data.Posting):
        return True
    elif isinstance(p, beancount.core.data.TxnPosting):
        return True
    else:
        return False

def in_range(from_, to_, p):
    return from_ <= get_date(p) <= to_

def open_close_in_range(entry, from_, to):
    open_ = entry[1][0]
    close_ = entry[1][1]

    open_date = open_.date if open_ else datetime.date.min
    close_date = close_.date if close_ else datetime.date.max

    return not (open_date > to) and not (close_date < from_)

def is_prefix_nonstrict(account_list, account):
    """ If account_list is empty then we should accept all accounts. """
    return (not account_list) or (functools.reduce(operator.__or__, (account.startswith(prefix) for prefix in account_list)))

def is_prefix_strict(account_list, account):
    """ If account_list is empty, then we should reject all accounts. """
    if not account_list:
        return False
    else:
        return functools.reduce(operator.__or__, (account.startswith(prefix) for prefix in account_list))

def get_inventory_as_of_date(date, postings):
    inventory = beancount.core.inventory.Inventory()
    for p in filter(only_postings, postings):
        if get_date(p) <= date:
            add_position(p, inventory)
    return inventory

def get_value_as_of(postings, date, currency, price_map):
        inventory = get_inventory_as_of_date(date, postings)
        balance = inventory.reduce(beancount.core.convert.convert_position, currency, price_map, date)
        amount = balance.get_currency_units(currency)
        return amount.number

def get_cashflows(accounts, from_, to, currency, price_map):
    inflow_accounts = set()
    outflow_accounts = set()

    total_start_value = 0
    total_end_value = 0
    # a list of tuples in the format (date, amount)
    cashflows = []

    for account, (open_, close_) in accounts:
        start_value = get_value_as_of(get_postings(account), from_, currency, price_map)
        end_value = get_value_as_of(get_postings(account), to, currency, price_map)
        print('-', account, fmt_d(start_value), fmt_d(end_value))
        total_start_value += start_value
        total_end_value += end_value

        def is_external(account):
            """ an external account is one that represents cashflow in & out of the
            investment. this is in contrast to an 'internal' account, like dividends """
            return not (is_account(account) or is_internal(account))

        for entry in filter(filter_daterange, get_postings(account)):
            for p in entry.txn.postings:
                if is_external(p.account):
                    # a +600 in the posting means money is flowing out (since it is +600 for the external account)
                    cashflows.append((entry.txn.date, -p.units.number))

                    if p.units.number < 0:
                        inflow_accounts.add(p.account)
                    else:
                        outflow_accounts.add(p.account)
    return (total_start_value, total_end_value, cashflows, inflow_accounts, outflow_accounts)

def get_timeweighted_returns(accounts, currency, price_map):
    today = datetime.date.today()
    dates = [
        today + relativedelta(years=-10),
        today + relativedelta(years=-5),
        today + relativedelta(years=-3),
        today + relativedelta(years=-1),
        datetime.date(today.year, 1, 1),
        today + relativedelta(months=-6),
        today + relativedelta(months=-3),
        today + relativedelta(months=-1),
        today
    ]
    keys = [
        '10-years',
        '5-years',
        '3-years',
        '1-year',
        'ytd',
        '6-months',
        '3-months',
        '1-month',
        'today'
    ]
    assert len(keys) == len(dates)

    # create another list the same size as the one above but populated with
    # 0s. This is where we will accumulate values as we iterate across accounts
    total_values = []
    total_values.extend(itertools.repeat(0, len(dates)))

    # TODO: this isn't right...it ignore contributions & withdrawals...
    for account, (open_, close_) in accounts:
        values = [get_value_as_of(get_postings(account), d, currency, price_map) for d in dates]
        total_values = [i+j for i,j in zip(values, total_values)]

    decimal.getcontext().traps[decimal.DivisionByZero] = 0
    as_pct = [float((total_values[-1] / i) - 1) for i in total_values]
    results = dict(zip(keys, as_pct))
    pprint(results)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Calculate return data."
    )
    parser.add_argument('bean', help='Path to the beancount file.')
    parser.add_argument('--currency', default='USD', help='Currency to use for calculating returns.')
    parser.add_argument('--account', action='append', default=[], help='Account(s) to include when calculating returns. Can be specified multiple times.')
    parser.add_argument('--internal', action='append', default=[], help='Account(s) that represent internal cashflows (i.e. dividends, interest, and capital gains)')
    parser.add_argument('--year', type=int, help='Year. Shorthand for --from/--to.')
    parser.add_argument('--from', dest='from_', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), help='Start date: YYYY-MM-DD, 2016-12-31')
    parser.add_argument('--to', type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'), help='End date YYYY-MM-DD, 2016-12-31')
    parser.add_argument('--time-weighted', action='store_true', help='Generate a suite of time-weighted returns instead.')
    parser.add_argument('--debug-inflows', action='store_true', help='Print list of all inflow accounts in transactions.')
    parser.add_argument('--debug-outflows', action='store_true', help='Print list of all outflow accounts in transactions.')

    args = parser.parse_args()

    if args.year and (args.from_ or args.to):
        raise(parser.error('--year option mutually exclusive with --to/--from options'))

    if args.year:
        args.from_ = datetime.date(args.year, 1, 1)
        args.to = datetime.date(args.year, 12, 31)

    if not args.from_:
        args.from_ = datetime.date.min
    if not args.to:
        args.to = datetime.date.max

    entries, errors, options = beancount.loader.load_file(args.bean, logging.info, log_errors=sys.stderr)
    realized_accounts = beancount.core.realization.postings_by_account(entries)
    price_map = beancount.core.prices.build_price_map(entries)
    account_types = beancount.parser.options.get_account_types(options)
    open_close = beancount.core.getters.get_account_open_close(entries)

    is_account_type = functools.partial(beancount.core.account_types.is_account_type, account_types.assets)
    get_sort_key = functools.partial(beancount.core.account_types.get_account_sort_key, account_types)
    is_account = functools.partial(is_prefix_nonstrict, args.account)
    is_internal = functools.partial(is_prefix_strict, args.internal)
    filter_daterange = functools.partial(in_range, args.from_, args.to)

    # We only want Asset accounts...
    items = open_close.items()
    accounts_filtered = filter(lambda entry: is_account_type(entry[0]), items)

    # ...and we only want accounts that match our --account parameter
    accounts_filtered = filter(lambda entry: is_account(entry[0]), accounts_filtered)

    # ...and we only want accounts that were active during our date range
    accounts_filtered = filter(lambda entry: open_close_in_range(entry, args.from_, args.to), accounts_filtered)

    # ...and we want them sorted for us
    accounts_sorted = sorted(accounts_filtered, key=lambda entry: get_sort_key(entry[0]))

    def get_postings(account):
        return filter(only_postings, realized_accounts[account])

    if args.time_weighted:
        get_timeweighted_returns(accounts_sorted, args.currency, price_map)
    else:
        (start_value, end_value, cashflows, inflow_accounts, outflow_accounts) = get_cashflows(accounts_sorted, args.from_, args.to, args.currency, price_map)
        cashflows.insert(0, (args.from_, start_value))
        cashflows.append((args.to, -end_value))
        #pprint(cashflows)
        # we need to coerce everything to a float for xirr to work...
        r = xirr([(d, float(f)) for (d,f) in cashflows])
        print('XIRR', fmt_pct(r))

        # TODO: convert to annualised rate (since we may have specified multiple years)

        if args.debug_inflows:
            print('>> [inflows]')
            pprint(inflow_accounts)
        if args.debug_outflows:
            print('<< [outflows]')
            pprint(outflow_accounts)
