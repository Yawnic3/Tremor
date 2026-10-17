from pathlib import Path
import pytest
from backend.app.prices import demo_prices, get_prices, import_csv, refresh


def test_demo_deterministic_and_separate(tmp_path, monkeypatch):
    monkeypatch.setenv('EVENTMAP_DB', str(tmp_path / 'test.db'))
    a = demo_prices('AAPL')
    assert a == demo_prices('AAPL') and a.synthetic
    assert len(a.prices) > 500
    assert not get_prices('AAPL').prices


def test_csv_and_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('EVENTMAP_DB', str(tmp_path / 'test.db'))
    path: Path = tmp_path / 'prices.csv'
    path.write_text('date,adjusted_close\n2026-01-02,100\n2026-01-05,101\n')
    series = import_csv('AAPL', path, 'test fixture')
    assert get_prices('AAPL') == series
    class NeverFetch:
        def fetch(self, ticker):
            raise AssertionError('Cache must prevent fetch')
    assert refresh('AAPL', NeverFetch()) == series
    path.write_text('date,adjusted_close\n2026-01-02,-1\n')
    with pytest.raises(ValueError):
        import_csv('AAPL', path, 'bad')
    assert get_prices('AAPL') == series
