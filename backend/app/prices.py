import csv
import hashlib
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from backend.app.db import connect
from backend.app.ingestion import request


class Price(BaseModel):
    date: date
    close: float = Field(gt=0, allow_inf_nan=False)


class PriceSeries(BaseModel):
    ticker: str
    provider: str
    synthetic: bool
    adjusted: bool
    fetched_at: str
    warning: str
    prices: list[Price]


class PriceProvider(Protocol):
    def fetch(self, ticker: str) -> PriceSeries: ...


class AlphaVantage:
    def fetch(self, ticker: str) -> PriceSeries:
        key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not key:
            raise ValueError("Configure ALPHA_VANTAGE_API_KEY or import a licensed adjusted-close CSV.")
        payload = request(
            "https://www.alphavantage.co/query",
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "compact",
                "apikey": key,
            },
        ).json()
        data = payload.get("Time Series (Daily)")
        if not data:
            raise ValueError(
                "Price provider returned no prices; check quota or configuration. Cached prices retained."
            )
        return PriceSeries(
            ticker=ticker,
            provider="alpha_vantage",
            synthetic=False,
            adjusted=False,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            warning="Unadjusted daily close. Splits/dividends can distort returns. Free compact "
            "history is generally too short for the 120-day estimation window.",
            prices=[
                Price(date=date.fromisoformat(d), close=float(v["4. close"])) for d, v in sorted(data.items())
            ],
        )


def demo_prices(ticker: str) -> PriceSeries:
    # Deterministic illustration, never persisted as observed market data.
    seed = int(hashlib.sha256(ticker.encode()).hexdigest()[:8], 16)
    prices = []
    current, value, i = date(2024, 1, 1), 80.0 + seed % 150, 0
    while current <= date(2026, 10, 16):
        if current.weekday() < 5:
            market = 0.0002 + 0.008 * math.sin(i * 0.71) + 0.004 * math.cos(i * 0.29)
            residual = 0 if ticker == "SPY" else 0.004 * math.sin(i * 1.13 + seed % 100)
            value *= 1 + market * (1 if ticker == "SPY" else 0.8 + (seed % 50) / 100) + residual
            prices.append(Price(date=current, close=round(value, 6)))
            i += 1
        current += timedelta(days=1)
    return PriceSeries(
        ticker=ticker,
        provider="synthetic_demo",
        synthetic=True,
        adjusted=True,
        fetched_at="2026-10-17T00:00:00+00:00",
        warning="SYNTHETIC PRICES. Illustrative weekday calendar; not market observations.",
        prices=prices,
    )


def init_prices() -> None:
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS price_cache (ticker TEXT PRIMARY KEY, payload TEXT NOT NULL)"
        )


def store(series: PriceSeries) -> None:
    init_prices()
    # One explicit active observed provider per ticker prevents cross-vendor splicing.
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO price_cache VALUES (?,?)", (series.ticker, series.model_dump_json())
        )


def get_prices(ticker: str, demo: bool = False) -> PriceSeries:
    if demo:
        return demo_prices(ticker)
    init_prices()
    with connect() as conn:
        row = conn.execute("SELECT payload FROM price_cache WHERE ticker=?", (ticker,)).fetchone()
    if row:
        return PriceSeries.model_validate_json(row["payload"])
    return PriceSeries(
        ticker=ticker,
        provider="none",
        synthetic=False,
        adjusted=False,
        fetched_at="",
        warning="No cached prices. Import adjusted closes or run fetch-prices.",
        prices=[],
    )


def refresh(ticker: str, provider: PriceProvider | None = None) -> PriceSeries:
    existing = get_prices(ticker)
    if (
        existing.fetched_at
        and (datetime.now(timezone.utc) - datetime.fromisoformat(existing.fetched_at)).total_seconds() < 86400
    ):
        return existing
    series = (provider or AlphaVantage()).fetch(ticker)
    store(series)
    return series


def import_csv(ticker: str, path: Path, provenance: str) -> PriceSeries:
    with path.open(encoding="utf-8-sig") as file:
        prices = [
            Price(date=date.fromisoformat(row["date"]), close=float(row["adjusted_close"]))
            for row in csv.DictReader(file)
        ]
    if len({p.date for p in prices}) != len(prices) or not prices:
        raise ValueError("CSV must contain unique dates and at least one adjusted close.")
    series = PriceSeries(
        ticker=ticker,
        provider="csv:" + provenance,
        synthetic=False,
        adjusted=True,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        warning="User-provided adjusted closes; adjustment and licensing not independently verified.",
        prices=sorted(prices, key=lambda p: p.date),
    )
    store(series)
    return series
