from bisect import bisect_left
from datetime import date
from math import sqrt

import numpy as np
from pydantic import BaseModel

from backend.app.db import list_events
from backend.app.exposure import match
from backend.app.models import Event
from backend.app.prices import PriceSeries, get_prices

WINDOWS = [(-1, 1), (0, 5), (0, 20)]


class StudyError(ValueError):
    pass


class Car(BaseModel):
    window: str
    value: float


class CompanyStudy(BaseModel):
    alpha: float
    beta: float
    estimation_n: int
    event_trading_date: date
    cars: list[Car]


class Aggregate(BaseModel):
    window: str
    mean_car: float | None
    n_events: int
    company_observations: int
    ci_low: float | None
    ci_high: float | None
    t_stat: float | None
    significant: bool
    warning: str


class History(BaseModel):
    type: str
    region: str
    synthetic: bool
    benchmark: str = 'SPY'
    estimation_window: str = '[-140,-21] trading days; 120 returns'
    candidates: int
    skipped_companies: int
    excluded_overlaps: int
    results: list[Aggregate]
    warning: str


def study(company: PriceSeries, market: PriceSeries, event_date: date) -> CompanyStudy:
    if company.synthetic != market.synthetic or not company.adjusted or not market.adjusted:
        raise StudyError('Require matching synthetic/observed status and adjusted closes for both series.')
    calendar = sorted(p.date for p in market.prices)
    if len(set(calendar)) != len(calendar):
        raise StudyError('Duplicate benchmark dates')
    zero = bisect_left(calendar, event_date)
    if zero >= len(calendar) or (calendar[zero]-event_date).days > 7 or zero < 141 or zero+20 >= len(calendar):
        raise StudyError('Insufficient estimation or event-window history')
    dates = calendar[zero-141:zero+21]
    if any((b-a).days > 7 for a, b in zip(dates, dates[1:])):
        raise StudyError('Benchmark calendar has an unexplained gap')
    stock = {p.date: p.close for p in company.prices}
    benchmark = {p.date: p.close for p in market.prices}
    if len(stock) != len(company.prices) or any(d not in stock for d in dates):
        raise StudyError('Company missing benchmark trading dates')
    stock_close = np.array([stock[d] for d in dates])
    market_close = np.array([benchmark[d] for d in dates])
    r = stock_close[1:]/stock_close[:-1]-1
    m = market_close[1:]/market_close[:-1]-1
    # r[0] is relative trading day -140, r[119] day -21, r[140] day 0.
    design = np.column_stack((np.ones(120), m[:120]))
    coefficients, _, rank, _ = np.linalg.lstsq(design, r[:120], rcond=None)
    if rank != 2:
        raise StudyError('Benchmark estimation window has no return variation')
    alpha, beta = (float(v) for v in coefficients)
    abnormal = r - (alpha + beta*m)
    return CompanyStudy(alpha=alpha, beta=beta, estimation_n=120, event_trading_date=calendar[zero],
                        cars=[Car(window=f'[{a:+d},{b:+d}]', value=float(abnormal[140+a:141+b].sum()))
                              for a, b in WINDOWS])


def t_critical(df: int) -> float:
    # Conservative two-sided 95% Student-t critical values, rounded upward.
    table = [(1, 12.707), (2, 4.303), (3, 3.183), (4, 2.777), (5, 2.571), (6, 2.447),
             (7, 2.365), (8, 2.307), (9, 2.263), (10, 2.229), (15, 2.132), (20, 2.086),
             (30, 2.043), (60, 2.001), (120, 1.980)]
    return next((value for boundary, value in reversed(table) if df >= boundary), 12.707)


def aggregate(window: str, event_cars: list[float], observations: int) -> Aggregate:
    n = len(event_cars)
    mean = float(np.mean(event_cars)) if n else None
    se = float(np.std(event_cars, ddof=1)/sqrt(n)) if n > 1 else None
    half = t_critical(n-1)*se if se is not None else None
    low = mean-half if mean is not None and half is not None else None
    high = mean+half if mean is not None and half is not None else None
    significant = bool(n >= 5 and se and low is not None and high is not None and (low > 0 or high < 0))
    return Aggregate(window=window, mean_car=mean, n_events=n, company_observations=observations,
                     ci_low=low, ci_high=high, t_stat=mean/se if se and mean is not None else None,
                     significant=significant, warning=(
                         'Sample too small to be meaningful (minimum 5 independent events).'
                         if n < 5 else 'No estimated variability; inference unavailable.' if not se else
                         'Exploratory evidence only; not a prediction.' if significant else
                         'Not statistically significant at the exploratory 95% level.'))


def history(event: Event) -> History:
    # Historical relative to selected event; never look ahead or include the selected event.
    candidates = sorted([e for e in list_events() if e.id != event.id and e.type == event.type
                         and e.region == event.region and e.synthetic == event.synthetic
                         and e.start < event.start and (event.start.date()-e.start.date()).days > 42],
                        key=lambda e: e.start, reverse=True)
    market = get_prices('SPY', event.synthetic)
    values: dict[str, list[float]] = {f'[{a:+d},{b:+d}]': [] for a, b in WINDOWS}
    skipped, overlaps, observations = 0, 0, 0
    used_dates: list[date] = []
    for past in candidates:
        if any(abs((past.start.date()-d).days) <= 42 for d in used_dates):
            overlaps += 1
            continue
        per_event: dict[str, list[float]] = {key: [] for key in values}
        for company in match(past):
            try:
                result = study(get_prices(company.ticker, event.synthetic), market, past.start.date())
            except StudyError:
                skipped += 1
                continue
            observations += 1
            for car in result.cars:
                per_event[car.window].append(car.value)
        if any(per_event.values()):
            used_dates.append(past.start.date())
            for key in values:
                values[key].append(float(np.mean(per_event[key])))
    return History(type=event.type, region=event.region, synthetic=event.synthetic, candidates=len(candidates),
                   skipped_companies=skipped, excluded_overlaps=overlaps,
                   results=[aggregate(key, value, observations) for key, value in values.items()],
                   warning=('SYNTHETIC DEMONSTRATION. ' if event.synthetic else '') +
                   'Equal-weight company CARs within each event; inference across event means. '
                   '42-day separation reduces overlapping windows, but independence is not assured. '
                   'Current HQ coverage introduces survivorship and location bias. Incomplete or unadjusted '
                   'histories are excluded. Region bins are coarse. Correlation is not causation.')
