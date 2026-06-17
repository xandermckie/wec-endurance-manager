"""Desktop launcher: start the local Flask server and open the game in a browser."""

from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser

# Frozen builds use AppData for saves/cache and ship read-only assets in the bundle.
from paths import init_user_data, is_frozen

if is_frozen():
    os.environ.setdefault("ENABLE_SCHEDULER", "false")
    os.environ.setdefault("FLASK_SECRET_KEY", "wec-endurance-manager-desktop")
    init_user_data()

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}/"


def _open_browser() -> None:
    time.sleep(1.5)
    webbrowser.open(URL)


def main() -> int:
    from app import app

    if is_frozen():
        threading.Thread(target=_open_browser, daemon=True).start()
        print(f"WEC Endurance Manager running at {URL}")
        print("Close this window to stop the game.")
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    else:
        print(f"Open {URL} in your browser (or use: python app.py)")
        app.run(host=HOST, port=PORT, debug=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
