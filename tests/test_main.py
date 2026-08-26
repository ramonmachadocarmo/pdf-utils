from fastapi.testclient import TestClient

from app import main


def test_lifespan_purges_stale_jobs_on_startup(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "purge_stale_jobs", lambda: calls.append(True))

    with TestClient(main.app):
        pass

    assert calls == [True]
