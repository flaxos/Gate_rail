"""Tests for finance revenue/cost tracking and solvency boundaries."""

import math

from gaterail.finance import CorporateFinance


def test_revenue_and_costs_change_cash_and_daily_totals() -> None:
    finance = CorporateFinance(cash=1_000.0, debt=500.0)

    finance.record_revenue(300.0)
    finance.record_cost(125.0)

    assert finance.revenue_today == 300.0
    assert finance.costs_today == 125.0
    assert finance.cash == 1_175.0


def test_interest_accrual_and_debt_payment_with_cap() -> None:
    finance = CorporateFinance(
        cash=250.0,
        debt=1_000.0,
        annual_interest_rate=0.365,
        min_daily_payment=100.0,
    )

    interest = finance.accrue_daily_interest()
    assert math.isclose(interest, 1.0)
    assert math.isclose(finance.debt, 1_001.0)

    paid = finance.pay_debt(500.0)
    assert paid == 250.0
    assert finance.cash == 0.0
    assert finance.debt == 751.0


def test_bankruptcy_threshold_requires_negative_cash_and_positive_debt() -> None:
    healthy = CorporateFinance(cash=0.0, debt=100.0)
    assert not healthy.insolvent

    debt_free = CorporateFinance(cash=-5.0, debt=0.0)
    assert not debt_free.insolvent

    bankrupt = CorporateFinance(cash=-1.0, debt=1.0)
    assert bankrupt.insolvent
