Beancount Returns Calculator
============================
This will calculator money-weighted and dollar-weighted returns
for a portfolio for [beancount](http://furius.ca/beancount/), the
double-entry plaintext accounting software.


Table of Contents
=================
   * [Quick Usage](#quick-usage)
   * [Dependencies](#dependencies)
   * [Introduction](#introduction)
   * [Dollar-weighted Returns](#dollar-weighted-returns)
   * [Time-weighted Returns](#time-weighted-returns)
   * [Internal vs. external cashflows](#internal-vs-external-cashflows)
   * [Multi-currency issues](#multi-currency-issues)
   * [Parameters in more detail](#parameters-in-more-detail)

Quick Usage
===========
```sh
python returns.py
    --account Assets:US:Vanguard
    --account Assets:US:Fidelity
    --internal Income:CapitalGains
    --internal Income:Dividends
    --year 2018
    portfolio.bean
```

Dependencies
============
* [dateutil](https://dateutil.readthedocs.io/en/stable/) - used for relative date processing
* [scipy])(https://www.scipy.org/) - for Internal Rate of Return (XIRR) calculations
* [beancount](http://furius.ca/beancount/) - obviously :)

Introduction
============

Dollar-weighted Returns
=======================

Time-weighted Returns
=====================

Internal vs. external cashflows
===============================

Multi-currency issues
=====================

Parameters in more detail
=========================
--currency
--account
--internal
--year
--to
--from
--time-weighted
--debug-inflows
--debug-outflows