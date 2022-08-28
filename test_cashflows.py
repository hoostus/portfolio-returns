import unittest
import datetime
from decimal import Decimal
from typing import List

from beancount import loader
from cashflows import Cashflow, get_cashflows


def simplify_cashflows(cashflows: List[Cashflow]) -> List[Cashflow]:
    """For ease of comparison, strip the context from each cashflow in 'cashflows'.

    """
    return [Cashflow(date=f.date, amount=f.amount, inflow_accounts=f.inflow_accounts,
                     outflow_accounts=f.outflow_accounts) for f in cashflows]


class TestCashflows(unittest.TestCase):

    @loader.load_doc()
    def test_simple(self, entries, errors, options_map):
        """
        1792-01-01 commodity USD
        2015-12-01 commodity ABC

        2015-12-01 open Equity:Opening-Balances
        2015-12-01 open Assets:Brokerage
        2015-12-01 open Assets:Cash
        2015-12-01 open Income:CapitalGains

        2015-12-01 * "Opening balance"
            Assets:Cash           3,000 USD
            Equity:Opening-Balances

        2015-12-01 price ABC 1.00 USD

        2015-12-01 * "Buy 1,000 shares"
            Assets:Brokerage      1,000 ABC {1.00 USD}
            Assets:Cash          -1,000 USD

        2016-12-01 price ABC 2.00 USD

        2016-12-01 * "Buy 1,000 more shares"
            Assets:Brokerage      1,000 ABC {2.00 USD}
            Assets:Cash          -2,000 USD

        2017-12-01 price ABC 1.50 USD

        2017-12-01 * "Sell 2,000 shares"
            Assets:Brokerage     -1,000 ABC {1.00 USD}
            Assets:Brokerage     -1,000 ABC {2.00 USD}
            Assets:Cash           2,500 USD
            Income:CapitalGains     500 USD
        """
        expected_cashflows = [
            Cashflow(
                date=datetime.date(2015, 12, 1),
                amount=Decimal(1000),
                inflow_accounts=set(['Assets:Cash']),
            ),
            Cashflow(
                date=datetime.date(2016, 12, 1),
                amount=Decimal(2000),
                inflow_accounts=set(['Assets:Cash']),
            ),
            Cashflow(
                date=datetime.date(2017, 12, 1),
                amount=Decimal(-2500),
                outflow_accounts=set(['Assets:Cash']),
            ),
        ]
        actual_cashflows = get_cashflows(
            entries=entries, interesting_accounts=['Assets:Brokerage'],
            internal_accounts=['Income:CapitalGains'], date_from=datetime.date(2015, 12, 1),
            date_to=datetime.date(2017, 12, 1), currency='USD')
        self.assertEqual(expected_cashflows, simplify_cashflows(actual_cashflows))

        # Test 'date_from=None', which should be equivalent.
        actual_cashflows = get_cashflows(
            entries=entries, interesting_accounts=['Assets:Brokerage'],
            internal_accounts=['Income:CapitalGains'], date_from=None,
            date_to=datetime.date(2017, 12, 1), currency='USD')
        self.assertEqual(expected_cashflows, simplify_cashflows(actual_cashflows))

    @loader.load_doc()
    def test_stock_conversion(self, entries, errors, options_map):
        """
        2018-01-01 commodity USD
        2018-01-01 commodity HOOLI

        2018-01-01 open Assets:Brokerage
        2018-01-01 open Assets:Cash

        2018-01-01 * "Buy"
           Assets:Brokerage 100 HOOLI {1 USD}
           Assets:Cash

        2018-04-01 commodity IOOLI

        2018-04-01 * "Conversion"
           Assets:Brokerage -100 HOOLI {}
           Assets:Brokerage 50 IOOLI {2 USD}

        2018-12-31 price HOOLI 1.5 USD
        2018-12-31 price IOOLI 3 USD
        """
        expected_cashflows = [
            Cashflow(
                date=datetime.date(2018, 1, 1),
                amount=Decimal(100),
                inflow_accounts=set(['Assets:Cash']),
            ),
            Cashflow(
                date=datetime.date(2018, 12, 31),
                amount=Decimal(-150),
            ),
        ]
        actual_cashflows = get_cashflows(
            entries=entries, interesting_accounts=['Assets:Brokerage'], internal_accounts=[],
            date_from=datetime.date(2018, 1, 1), date_to=datetime.date(2018, 12, 31),
            currency='USD')
        self.assertEqual(expected_cashflows, simplify_cashflows(actual_cashflows))

    @loader.load_doc()
    def test_multi_currency(self, entries, errors, options_map):
        """
        1792-01-01 commodity USD
        1999-01-01 commodity EUR
        2015-12-01 commodity ABC

        2015-12-01 open Equity:Opening-Balances
        2015-12-01 open Assets:Brokerage
        2015-12-01 open Assets:Cash
        2015-12-01 open Income:CapitalGains
        2015-12-01 open Income:Dividends

        2015-12-01 * "Opening balance"
            Assets:Cash           3,000 USD
            Equity:Opening-Balances

        2015-12-01 price EUR 2 USD

        2015-12-01 * "Buy in EUR"
            Assets:Brokerage      500 ABC {1.00 EUR}
            Assets:Cash          -1,000 USD @ 0.5 EUR

        2016-06-01 * "Receive dividend in EUR"
            Assets:Brokerage        50 EUR
            Income:Dividends       -100 USD @ 0.5 EUR

        2016-12-01 price EUR 1 USD

        2016-12-01 * "Buy more in EUR"
            Assets:Brokerage      1,000 ABC {2.00 EUR}
            Assets:Cash          -2,000 USD @ 1 EUR

        2018-12-01 * "Sell and withdraw all holdings"
            Assets:Brokerage       -500 ABC {1.00 EUR}
            Assets:Brokerage     -1,000 ABC {2.00 EUR}
            Assets:Brokerage        -50 EUR
            Income:CapitalGains  -1,000 USD @ 1 EUR
            Assets:Cash           3,550 USD @ 1 EUR
        """
        expected_cashflows = [
            Cashflow(
                date=datetime.date(2015, 12, 1),
                amount=Decimal('1000.00'),
                inflow_accounts=set(['Assets:Cash']),
            ),
            Cashflow(
                date=datetime.date(2016, 12, 1),
                amount=Decimal('2000.00'),
                inflow_accounts=set(['Assets:Cash']),
            ),
            Cashflow(
                date=datetime.date(2018, 12, 1),
                amount=Decimal('-3550.00'),
                outflow_accounts=set(['Assets:Cash']),
            ),
        ]
        actual_cashflows = get_cashflows(
            entries=entries, interesting_accounts=['Assets:Brokerage'],
            internal_accounts=['Income:CapitalGains', 'Income:Dividends'],
            date_from=datetime.date(2015, 12, 1), date_to=datetime.date(2018, 12, 1),
            currency='USD')
        self.maxDiff = None
        self.assertEqual(expected_cashflows, simplify_cashflows(actual_cashflows))
