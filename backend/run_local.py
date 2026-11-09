"""Run the app locally with graceful browser-session shutdown."""
from __future__ import annotations

import os

os.environ["BLIND_HAM_LOCAL_SESSION"] = "1"

import uvicorn

from backend.app.main import app


def main() -> None:
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="info",
        access_log=False,
    )
    server = uvicorn.Server(config)
    app.state.uvicorn_server = server
    server.run()


if __name__ == "__main__":
    main()
