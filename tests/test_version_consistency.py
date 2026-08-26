import re
import tomllib

from app.config import APP_VERSION, ROOT


def test_pyproject_version_matches_app_config():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["poetry"]["version"] == APP_VERSION


def test_changelog_has_entry_for_current_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(rf"^## \[{re.escape(APP_VERSION)}\]", changelog, re.MULTILINE), (
        f"CHANGELOG.md has no '## [{APP_VERSION}]' section matching APP_VERSION"
    )
