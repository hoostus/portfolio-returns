"""Extract cashflows from transactions.

"""
import datetime
import functools
import logging
import operator
import re
import dataclasses

from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import List, Optional, Set

import beancount
from beancount.core.data import Account, Currency, Transaction

def add_position(p, inventory):
    if isinstance(p, beancount.core.data.Posting):
        inventory.add_position(p)
    elif isinstance(p, beancount.core.data.TxnPosting):
        inventory.add_position(p.posting)
    else:
        raise Exception("Not a Posting or TxnPosting", p)

def is_interesting_posting(posting, interesting_accounts):
    """ Is this posting for an account we care about? """
    for pattern in interesting_accounts:
        if re.match(pattern, posting.account):
            return True
    return False

def is_internal_account(posting, internal_accounts):
    for pattern in internal_accounts:
        if re.match(pattern, posting.account):
            return True
    return False

def is_interesting_entry(entry, interesting_accounts):
    """ Do any of the postings link to any of the accounts we care about? """
    accounts = [p.account for p in entry.postings]
    for posting in entry.postings:
        if is_interesting_posting(posting, interesting_accounts):
            return True
    return False

def iter_interesting_postings(date, entries, interesting_accounts):
    for e in entries:
        if e.date <= date:
            for p in e.postings:
                if is_interesting_posting(p, interesting_accounts):
                    yield p

def get_inventory_as_of_date(date, entries, interesting_accounts):
    inventory = beancount.core.inventory.Inventory()
    for p in iter_interesting_postings(date, entries, interesting_accounts):
        add_position(p, inventory)
    return inventory

def get_value_as_of(postings, date, currency, price_map, interesting_accounts):
    inventory = get_inventory_as_of_date(date, postings, interesting_accounts)
    balance = inventory.reduce(beancount.core.convert.convert_position, currency, price_map, date)
    amount = balance.get_currency_units(currency)
    return amount.number

@dataclasses.dataclass
class Cashflow:
    date: datetime.date
    amount: Decimal
    inflow_accounts: Set[Account] = dataclasses.field(default_factory=set)
    outflow_accounts: Set[Account] = dataclasses.field(default_factory=set)
    entry: Optional[Transaction] = None

def get_cashflows(entries: List[Transaction], interesting_accounts: List[str], internal_accounts:
                  List[str], date_from: Optional[datetime.date], date_to: datetime.date,
                  currency: Currency) -> List[Cashflow]:
    """Extract a series of cashflows affecting 'interesting_accounts'.

    A cashflow is represented by any transaction involving (1) an account in 'interesting_accounts'
    and (2) an account not in 'interesting_accounts' or 'internal_accounts'. Positive cashflows
    indicate inflows, and negative cashflows indicate outflows.

    'interesting_accounts' and 'internal_accounts' are regular expressions that must match at the
    beginning of account names.

    Return a list of cashflows that occurred between 'date_from' and 'date_to', inclusive. If
    'interesting_accounts' had a balance at the beginning of 'date_from', the first cashflow will
    represent the market value of that balance as an inflow. The cashflows will be denominated in
    units of 'currency'.

    """
    price_map = beancount.core.prices.build_price_map(entries)
    only_txns = beancount.core.data.filter_txns(entries)
    interesting_txns = [txn for txn in only_txns if is_interesting_entry(txn, interesting_accounts)]
    # pull it into a list, instead of an iterator, because we're going to reuse it several times
    interesting_txns = list(interesting_txns)

    cashflows = []

    for entry in interesting_txns:
        if date_from is not None and not date_from <= entry.date: continue
        if not entry.date <= date_to: continue

        cashflow = Decimal(0)
        inflow_accounts = set()
        outflow_accounts = set()
        # Imagine an entry that looks like
        # [Posting(account=Assets:Brokerage, amount=100),
        #  Posting(account=Income:Dividend, amount=-100)]
        # We want that to net out to $0
        # But an entry like
        # [Posting(account=Assets:Brokerage, amount=100),
        #  Posting(account=Assets:Bank, amount=-100)]
        # should net out to $100
        # we loop over all postings in the entry. if the posting
        # if for an account we care about e.g. Assets:Brokerage then
        # we track the cashflow. But we *also* look for "internal"
        # cashflows and subtract them out. This will leave a net $0
        # if all the cashflows are internal.

        for posting in entry.postings:
            converted = beancount.core.convert.convert_amount(
                beancount.core.convert.get_weight(posting), currency, price_map, entry.date)
            if converted.currency != currency:
                logging.error(f'Could not convert posting {converted} from {entry.date} on line {posting.meta["lineno"]} to {currency}. IRR will be wrong.')
                continue
            value = converted.number

            if is_interesting_posting(posting, interesting_accounts):
                cashflow += value
            elif is_internal_account(posting, internal_accounts):
                cashflow += value
            else:
                if value > 0:
                    outflow_accounts.add(posting.account)
                else:
                    inflow_accounts.add(posting.account)
        # calculate net cashflow & the date
        if cashflow.quantize(Decimal('.01')) != 0:
            cashflows.append(Cashflow(date=entry.date, amount=cashflow,
                                      inflow_accounts=inflow_accounts,
                                      outflow_accounts=outflow_accounts,
                                      entry=entry))

    if date_from is not None:
        start_value = get_value_as_of(interesting_txns, date_from + relativedelta(days=-1),
                                      currency, price_map, interesting_accounts)
        # if starting balance isn't $0 at starting time period then we need a cashflow
        if start_value != 0:
            cashflows.insert(0, Cashflow(date=date_from, amount=start_value))
    end_value = get_value_as_of(interesting_txns, date_to, currency, price_map, interesting_accounts)
    # if ending balance isn't $0 at end of time period then we need a cashflow
    if end_value != 0:
        cashflows.append(Cashflow(date=date_to, amount=-end_value))

    return cashflows
