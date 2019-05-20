Beancount Returns Calculator
============================
This will calculator money-weighted and time-weighted returns
for a portfolio for [beancount](http://furius.ca/beancount/), the
double-entry plaintext accounting software.

Table of Contents
=================

   * [Beancount Returns Calculator](#beancount-returns-calculator)
   * [Table of Contents](#table-of-contents)
   * [Quick Usage](#quick-usage)
   * [Dependencies](#dependencies)
   * [Introduction](#introduction)
   * [Time-weighted Returns](#time-weighted-returns)
   * [Money-weighted Returns](#money-weighted-returns)
   * [Illustrated Example of the Difference](#illustrated-example-of-the-difference)
   * [External vs. internal cashflows](#external-vs-internal-cashflows)
   * [Note on capital gains](#note-on-capital-gains)
   * [Multi-currency issues](#multi-currency-issues)
   * [Parameters in more detail](#parameters-in-more-detail)
   * [TODOs &amp; Bugs](#todos--bugs)

Quick Usage
===========
```sh
python returns.py
    --account Assets:US:Vanguard
    --account Assets:US:Fidelity
    --internal Income:CapitalGainsDistribution
    --internal Income:Dividends
    --year 2018
    portfolio.bean
```

Dependencies
============
* [dateutil](https://dateutil.readthedocs.io/en/stable/) - used for relative date processing
* [scipy](https://www.scipy.org/) - for Internal Rate of Return (XIRR) calculations
* [beancount](http://furius.ca/beancount/) - obviously :)

Introduction
============
This script will determine the rate of return for a portfolio held without beancount.
You can specify which accounts & which timeframes you are interested in. We calculate
"money-weighted returns", which means taking into account the timing & value of cashflows.
In particular, this means you -- the user -- need to tell us which beancount accounts
are real cashflows in & out of the account. See below for more on this.

Time-weighted Returns
=====================
**Warning. Time-weighted returns are not implemented.**

The time-weighted rate of return is the geometric mean of a series of *equal-length* holding periods.

Time-weighted rates of return **do not** take into account the impact of cash flows into and out of the portfolio.

Time-weighted rates of return attempt to remove the impact of cash flows when calculating the return. This makes it ideal for calculating the performance of broad market indices or the impact of a fund manager on the performance of an investment. Time-weighting is important in this context as fund managers do not control the timing of cash flows into and out of their fund – investors control that – so it is not reasonable to include that effect when evaluating the performance of the fund manager.

To calculate the time-weighted return we calculate the holding period return (HPR) of **each day** during the full time period and then find the geometric mean across all of the HPRs.

The formula for a single holding period return is:
```HPR = ((MV1 - MV0 + D1 - CF1)/MV0)```

* HPR: Holding Period Return
* MV1: The market value at the end of the period
* MV0: The market value at the start of the period
* D1: The value of any dividends or interest inflows
* CF1: Cash flows (i.e. deposits subtracted out or withdrawals added back in)

Money-weighted Returns
=======================
The money-weighted rate of return is the Internal Rate of Return (IRR or, in spreadsheets, XIRR).

Money-weighted returns take into account the timing & size of cash flows into and out of the portfolio, in addition to the performance of the underlying portfolio itself. Money-weighted returns can change significantly depending on the timing of large cash flows in & out of the portfolio.

The money-weighted return does not split the time period up into equal-length sub-periods. Instead it searches (via mathematical optimization techniques) for the discount rate that equals the cost of the investment plus all of the cash flows generated.

For the vast majority of investors a money-weighted rate of return is the most appropriate method of measuring the performance of your portfolio as you control inflows and outflows of the investment portfolio.

Illustrated Example of the Difference
=====================================
If you don't buy any new shares, sell any shares, and all dividends are reinvested, then the money-weighted return and the time-weighted return will be the same over a given time period.

Since most people will be buying or selling shares, in practice they will differ.

Imagine you invest like:
1. On January 1st you buy 100 shares of FOO at $100.
1. On January 2nd you buy 100 more shares of FOO, this time at $500 each for $50,000.
1. On January 3rd you sell 100 shares of FOO, this time at $50 each for $5,000.
1. On January 4th, you do nothing. The price of FOO returns to $100.

The time-weighted return is 0%, since it ignores the impact of cash flows and just sees that the starting value (100 shares @ $100) is exactly the same as the ending value (100 shares @ $100).

Date|Total Amount|Shares|Share price|Holding Period Return
----|------------|------|-----------|-------------------
Jan 1 |  $10,000 | 100 | $100| n/a
Jan 2 | $100,000 | 200 | $500| (100,000-10,000-50,000)/10,000 = 400%
Jan 3 |   $5,000 | 100 |  $50| (5,000-100,000+5,000)/100,000 = -90%
Jan 4 |  $10,000 | 100 | $100| (10,000-5,000)/5,000 = 100%

The geometric mean of the Holding Period Returns is
```
=((1 + 4.00) * (1 - .90) * (1 + 1.00)) - 1
=0
```

Since you bought some shares for $50,000 and sold them for $5,000 you don't **feel** like the return was 0%, though.

The money-weighted return for the same investment is -52%.

External vs. internal cashflows
===============================
When calculating money-weighted returns we need to distinguish "real", or external, cashflows
from "apparent", or internal, cashflows.

Imagine that your portfolio pays you a dividend but your account is set to automatically
reinvest dividends. Even though there is an apparent cashflow between accounts nothing has
actually changed; from the rate of return perspective it is as if the money never left
your portfolio.

So we need to know which accounts to ignore when looking for cashflows. In practice,
this is limited to three kinds of things:

* Interest that is reinvested
* Dividends that are reinvested
* Capital gains distributions that are reinvested

Note on capital gains
=====================
There is a difference between a "capital gains distribution" and a "capital gain".

A "capital gains distribution" is when the fund family gives you money. This should
be treated as a dividend, as an "internal cashflow". It is generated by the internal
operation of the fund.

A "capital gain" is what happens when *you* sell a fund. This is an *external*
cashflow.

Even though they are identical for **tax purposes**, they are different for the
purposes of rate of return calculations. You need to ensure they going to two
separate accounts in beancount.

Multi-currency issues
=====================
TBD. I have no idea if this works at all with multiple-currencies....

Parameters in more detail
=========================
* --currency. In order to generate meaningful cashflows we need to convert the securities we hold into a currency. You need to tell the script which currency to use. USD is the default if you don't specify anything.
* --account. Accounts to calculate the rate of return for. This can be specified multiple times. This takes a regular expression to match account names. So "^Assets:US:.\*" would match Assets:US:Schwab and Assets:US:MerrillLynch 
* --internal. Accounts to treat as "internal" when deciding whether to ignore cashflows. This is also takes a regular expression and can be specified multiple times. 
* --to. The start date to use when calculating returns. If not specified, uses the earliest date found in the beancount file.
* --from. The end date to use when calculating returns. If not specified, uses today.
* --year. A shortcut to easily calculate returns for a single calendar year.
* --ytd. A shortcut to calculate returns for the year-to-date.
* --1year, --2year, --3year, --5year, --10year. A shortcut to calculate returns for various time periods.
* --debug-inflows. List all of the accounts that generated an outflow. Useful for debugging whether you've specified all of the --internal accounts you need to.
* --debug-outflows. List all of the accounts that generated an inflow. Useful for debugging whether you've specified all of the --internal accounts you need to.
* --debug-cashflows. List all of the date & amount of cashflows used for the rate of return calculation.

TODOs & Bugs
============
- [ ] Generate growth of $10,000 chart.
- [ ] Definitely needs more testing.
- [ ] Add way to specify individual commodities and track just those
- [ ] As I write up the documentation, I become less certain about the need
to specify internal accounts, if we just track those cashflows won't it have no
effect on the rate of return? I take out $100 and then put $100 back in the same day?
- [ ] double check whether I'm right about capital gains distributions
