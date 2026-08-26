import json
from dataclasses import dataclass
from urllib.request import Request, urlopen

from app.config import APP_VERSION, GITHUB_REPO

_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_TIMEOUT = 4


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    update_available: bool
    release_url: str | None
    download_url: str | None


def _parse_version(value: str) -> tuple[int, ...]:
    parts = value.strip().lstrip("vV").split(".")
    return tuple(int(p) for p in parts if p.isdigit())


def _fetch_latest_release() -> dict:
    request = Request(
        _RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "pdf-utils-update-check"},
    )
    with urlopen(request, timeout=_TIMEOUT) as response:
        return json.load(response)


def check_for_update() -> UpdateInfo:
    try:
        release = _fetch_latest_release()
    except Exception:
        return UpdateInfo(
            current_version=APP_VERSION,
            latest_version=APP_VERSION,
            update_available=False,
            release_url=None,
            download_url=None,
        )

    latest_version = str(release.get("tag_name", APP_VERSION)).lstrip("vV")
    download_url = next(
        (
            asset.get("browser_download_url")
            for asset in release.get("assets", [])
            if str(asset.get("name", "")).lower().endswith(".exe")
        ),
        None,
    )

    return UpdateInfo(
        current_version=APP_VERSION,
        latest_version=latest_version,
        update_available=_parse_version(latest_version) > _parse_version(APP_VERSION),
        release_url=release.get("html_url"),
        download_url=download_url,
    )
