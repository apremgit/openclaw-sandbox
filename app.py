#!/usr/bin/env python3
"""
Lightweight Flask app exposing a /health endpoint.

Features
--------
* Returns JSON with a simple "OK" status.
* Optional hook (`perform_extra_checks`) where you can add DB,
  cache, or other service checks without bloating the core code.
* Returns HTTP 200 for healthy, 503 for unhealthy.
* Runs both as a script (`python app.py`) and as a WSGI app
  (`application = app`) for production servers (gunicorn, uWSGI, etc.).
"""

from flask import Flask, jsonify, make_response
import logging
import traceback
import os

# ----------------------------------------------------------------------
# Create the Flask app
# ----------------------------------------------------------------------
app = Flask(__name__)

# Configure minimal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helper – extra health checks (optional)
# ----------------------------------------------------------------------
def perform_extra_checks() -> tuple[bool, dict]:
    """
    Run any additional health checks you need.
    """
    ok = True
    details = {}

    # ---- PostgreSQL (Dynamic check if configurations exist) -----------
    if os.getenv("PGHOST"):
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv("PGHOST"),
                dbname=os.getenv("PGDATABASE", "postgres"),
                user=os.getenv("PGUSER", "postgres"),
                password=os.getenv("PGPASSWORD"),
                connect_timeout=1,
            )
            conn.close()
            details["postgres"] = "ok"
        except Exception as e:
            ok = False
            details["postgres"] = {"status": "down", "error": str(e)}

    return ok, details


# ----------------------------------------------------------------------
# Health‑check endpoint
# ----------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    """
    Simple health‑check endpoint.
    """
    try:
        extra_ok, extra_details = perform_extra_checks()

        if extra_ok:
            payload = {"status": "ok"}
            status_code = 200
        else:
            payload = {"status": "failed", "details": extra_details}
            status_code = 503

        payload.update(extra_details)
        return make_response(jsonify(payload), status_code)

    except Exception:
        err_msg = traceback.format_exc()
        logger.exception("Unhandled exception in /health")
        payload = {"status": "failed", "error": "internal_error", "trace": err_msg}
        return make_response(jsonify(payload), 503)


@app.route("/", methods=["GET"])
def index():
    return (
        "🩺 Flask health‑check service – hit <a href='/health'>/health</a>",
        200,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
