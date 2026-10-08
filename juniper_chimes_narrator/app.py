#!/usr/bin/env python3
"""
juniper_chimes_narrator.app
~~~~~~~~~~~~~~~~~~~~~~~~~~
Flask Application Server for the Band Director Narrator.
"""

import os
import threading
from flask import Flask, render_template, jsonify, send_from_directory
from juniper_chimes_narrator.narrator import BandDirectorNarrator, CACHE_DIR

HTTP_PORT = int(os.environ.get("HTTP_PORT", 5012))
WS_URL = os.environ.get("WS_URL", "ws://127.0.0.1:65432")

app = Flask(__name__, template_folder="templates")
narrator = BandDirectorNarrator(ws_url=WS_URL, bpm=120)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(CACHE_DIR, filename)


@app.route("/api/state")
def get_state():
    with narrator.lock:
        return jsonify(narrator.app_state)


def main():
    # Start WebSocket clock listener thread
    threading.Thread(target=narrator.start_ws_listener, daemon=True).start()
    # Start Band Director narration loop thread
    threading.Thread(target=narrator.start_narration_loop, daemon=True).start()

    print(f"[BAND DIRECTOR SERVER] Running at http://0.0.0.0:{HTTP_PORT}")
    app.run(host="0.0.0.0", port=HTTP_PORT, debug=False)


if __name__ == "__main__":
    main()
