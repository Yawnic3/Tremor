from datetime import date, timedelta
import math
import pytest
from backend.app.analytics import StudyError, aggregate, study
from backend.app.prices import Price, PriceSeries


def fixture():
    market, stock = [], []
    m, s = 100., 100.
    for i in range(230):
        day = date(2025, 1, 1) + timedelta(days=i)
        r = .004*math.sin(i*.7)
        shock = -.01 if i == 180 else .02 if i == 181 else 0
        m *= 1+r
        s *= 1+.0003+1.2*r+shock
        market.append(Price(date=day, close=m))
        stock.append(Price(date=day, close=s))
    def series(ticker, rows):
        return PriceSeries(ticker=ticker, provider='fixture', synthetic=False, adjusted=True,
                           fetched_at='', warning='', prices=rows)
    return series('TEST', stock), series('SPY', market), stock[180].date


def test_known_answer_market_model():
    stock, market, day = fixture()
    result = study(stock, market, day)
    assert result.alpha == pytest.approx(.0003, abs=1e-12)
    assert result.beta == pytest.approx(1.2, abs=1e-10)
    assert result.estimation_n == 120
    for car in result.cars:
        assert car.value == pytest.approx(.01, abs=1e-10)


def test_missing_history_and_data_separation():
    stock, market, day = fixture()
    with pytest.raises(StudyError):
        study(stock, market, date(2025, 1, 2))
    stock.prices.pop(175)
    with pytest.raises(StudyError, match='missing'):
        study(stock, market, day)
    stock, market, day = fixture()
    stock.adjusted = False
    with pytest.raises(StudyError, match='adjusted'):
        study(stock, market, day)


def test_aggregation_honesty():
    result = aggregate('[0,+5]', [.01, .02, .03, .04, .05], 50)
    assert result.mean_car == pytest.approx(.03)
    assert result.n_events == 5 and result.company_observations == 50
    assert result.ci_low == pytest.approx(.010363, abs=1e-5)
    assert result.significant
    assert not aggregate('[0,+5]', [.01], 100).significant
    assert aggregate('[0,+5]', [], 0).mean_car is None
    assert not aggregate('[0,+5]', [.01]*5, 5).significant
