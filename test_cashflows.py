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
