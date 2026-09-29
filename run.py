"""
Entry point for running the Abuyog Community College Consultation System
locally.

Usage (see README.md for the full walkthrough):
    python run.py
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads variables from a local .env file, if present

from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
