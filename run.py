# -*- coding: utf-8 -*-
"""Lancement local — TIC MASTER #by_Myazirzk."""
import os

from app import create_app

app = create_app(os.environ.get("FLASK_CONFIG"))  # None => lit FLASK_ENV

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
