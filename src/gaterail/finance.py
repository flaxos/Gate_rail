"""Corporate finance ledger for GateRail."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CorporateFinance:
    """Track cashflow, debt, and profitability."""

    cash: float = 10_000.0
    debt: float = 4_000.0
    annual_interest_rate: float = 0.10
    min_daily_payment: float = 100.0
    revenue_today: float = 0.0
    costs_today: float = 0.0
    history: list[dict[str, float]] = field(default_factory=list)

    def reset_daily_totals(self) -> None:
        """Reset per-day rollup metrics."""

        self.revenue_today = 0.0
        self.costs_today = 0.0

    def record_revenue(self, amount: float) -> None:
        """Add revenue and cash."""

        if amount <= 0:
            return
        self.revenue_today += amount
        self.cash += amount

    def record_cost(self, amount: float) -> None:
        """Add cost and reduce cash."""

        if amount <= 0:
            return
        self.costs_today += amount
        self.cash -= amount

    @property
    def daily_interest_rate(self) -> float:
        """Simple daily interest rate assumption (365-day year)."""

        return self.annual_interest_rate / 365.0

    def accrue_daily_interest(self) -> float:
        """Accrue one day of debt interest."""

        if self.debt <= 0:
            return 0.0
        interest = self.debt * self.daily_interest_rate
        self.debt += interest
        return interest

    def pay_debt(self, amount: float | None = None) -> float:
        """Pay debt from cash; returns amount actually paid."""

        if self.debt <= 0 or self.cash <= 0:
            return 0.0
        requested = self.min_daily_payment if amount is None else max(0.0, amount)
        payment = min(requested, self.cash, self.debt)
        self.cash -= payment
        self.debt -= payment
        return payment

    def close_day(self) -> dict[str, float]:
        """Store and return snapshot of the day."""

        snapshot = {
            "cash": self.cash,
            "debt": self.debt,
            "revenue": self.revenue_today,
            "costs": self.costs_today,
            "net": self.revenue_today - self.costs_today,
        }
        self.history.append(snapshot)
        return snapshot

    @property
    def insolvent(self) -> bool:
        """Whether company cannot continue operations."""

        return self.cash < 0 and self.debt > 0
