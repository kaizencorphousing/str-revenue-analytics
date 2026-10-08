"""Offline tests for src/extract.py: no network, fake session only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import extract  # noqa: E402


class FakeResp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body or {}, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return self.responses.pop(0)


def test_backs_off_on_429_then_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr(extract.time, "sleep", sleeps.append)
    s = FakeSession([FakeResp(429, headers={"Retry-After": "3"}), FakeResp(429), FakeResp(200, {"ok": 1})])
    assert extract.get_json(s, "/x") == {"ok": 1}
    assert sleeps == [3.0, 2.0]  # Retry-After honoured, then exponential fallback


def test_paginates_until_last_page():
    pages = [FakeResp(200, {"data": [i], "meta": {"last_page": 3}}) for i in (1, 2, 3)]
    s = FakeSession(pages)
    assert extract.get_all_pages(s, "/r", {"per_page": 1}) == [1, 2, 3]
    assert [c["page"] for c in s.calls] == [1, 2, 3]


def test_retries_5xx_and_ignores_date_retry_after(monkeypatch):
    sleeps = []
    monkeypatch.setattr(extract.time, "sleep", sleeps.append)
    s = FakeSession([FakeResp(503, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), FakeResp(200, {"ok": 1})])
    assert extract.get_json(s, "/x") == {"ok": 1}
    assert sleeps == [1]


def test_calendar_chunks_are_adjacent_and_non_overlapping():
    from datetime import date
    def day_resp():
        return FakeResp(200, {"data": {"days": []}})
    s = FakeSession([day_resp(), day_resp()])
    extract.fetch_calendar(s, "pid", date(2026, 1, 1), date(2027, 2, 4))  # 400 days
    assert s.calls == [{"start_date": "2026-01-01", "end_date": "2026-12-31"},
                       {"start_date": "2027-01-01", "end_date": "2027-02-04"}]


def test_rejects_reservations_from_other_properties(monkeypatch):
    import pytest
    rows = [{"id": "a", "properties": [{"id": "pid"}]}, {"id": "b", "properties": [{"id": "client"}]}]
    monkeypatch.setattr(extract, "get_all_pages", lambda *a, **k: rows)
    with pytest.raises(SystemExit):
        extract.fetch_reservations(None, "pid")


def test_source_uses_get_only():
    src = Path(extract.__file__).read_text()
    for verb in (".post(", ".put(", ".patch(", ".delete(", ".request(", "requests.post"):
        assert verb not in src
