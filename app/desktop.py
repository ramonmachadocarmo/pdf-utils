"""Desktop entry point: runs the FastAPI app in-process and shows it in a native window."""

import socket
import sys
import threading
import time
from urllib.parse import quote

import uvicorn
import webview

from app.main import app

HOST = "127.0.0.1"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _startup_file() -> str | None:
    """Path passed by Windows when this exe is launched via file association / "Open with"."""
    for arg in sys.argv[1:]:
        if arg.lower().endswith((".pdf", ".xml")):
            return arg
    return None


def main() -> None:
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    while not server.started:
        time.sleep(0.05)

    url = f"http://{HOST}:{port}"
    startup_file = _startup_file()
    if startup_file:
        url += f"?open={quote(startup_file)}"

    webview.settings["ALLOW_DOWNLOADS"] = True
    webview.create_window("PDF Utils", url, width=1280, height=860, min_size=(960, 640))
    webview.start()

    server.should_exit = True
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
