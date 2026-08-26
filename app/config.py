from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "storage"
UPLOADS = STORAGE / "uploads"
OUTPUTS = STORAGE / "outputs"
STATIC = Path(__file__).resolve().parent / "static"

APP_VERSION = "1.0.0"
GITHUB_REPO = "ramonmachadocarmo/pdf-utils"

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB
JOB_TTL_SECONDS = 24 * 60 * 60  # purge job dirs older than this on startup

