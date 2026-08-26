import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import APP_VERSION
from app.main import app
from app.services.updater import UpdateInfo, _fetch_latest_release, _parse_version, check_for_update

client = TestClient(app)


def test_parse_version():
    assert _parse_version("v1.2.3") == (1, 2, 3)
    assert _parse_version("1.2") == (1, 2)


def test_fetch_latest_release_parses_response_body():
    payload = json.dumps({"tag_name": "v1.0.0"}).encode()
    response = MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    with patch("app.services.updater.urlopen", return_value=response) as mock_urlopen:
        data = _fetch_latest_release()
    assert data == {"tag_name": "v1.0.0"}
    mock_urlopen.assert_called_once()


def test_check_for_update_network_failure_returns_current():
    with patch("app.services.updater._fetch_latest_release", side_effect=OSError("offline")):
        info = check_for_update()
    assert info == UpdateInfo(
        current_version=APP_VERSION,
        latest_version=APP_VERSION,
        update_available=False,
        release_url=None,
        download_url=None,
    )


def test_check_for_update_newer_release_available():
    release = {
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/ramonmachadocarmo/pdf-utils/releases/tag/v99.0.0",
        "assets": [
            {"name": "source.zip", "browser_download_url": "https://example.com/source.zip"},
            {"name": "PDF-Utils-Setup.exe", "browser_download_url": "https://example.com/setup.exe"},
        ],
    }
    with patch("app.services.updater._fetch_latest_release", return_value=release):
        info = check_for_update()
    assert info.update_available is True
    assert info.latest_version == "99.0.0"
    assert info.download_url == "https://example.com/setup.exe"
    assert info.release_url == release["html_url"]


def test_check_for_update_current_release_not_available():
    release = {"tag_name": f"v{APP_VERSION}", "html_url": "https://example.com", "assets": []}
    with patch("app.services.updater._fetch_latest_release", return_value=release):
        info = check_for_update()
    assert info.update_available is False
    assert info.download_url is None


def test_update_check_endpoint():
    release = {"tag_name": "v99.0.0", "html_url": "https://example.com", "assets": []}
    with patch("app.services.updater._fetch_latest_release", return_value=release):
        res = client.get("/api/update-check")
    assert res.status_code == 200
    data = res.json()
    assert data["update_available"] is True
    assert data["latest_version"] == "99.0.0"
    assert data["current_version"] == APP_VERSION
