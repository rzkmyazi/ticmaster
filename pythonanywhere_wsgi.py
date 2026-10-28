# -*- coding: utf-8 -*-
"""
Configuration WSGI pour PythonAnywhere — TIC MASTER #by_Myazirzk
==============================================================

À coller **tel quel** dans l'onglet « Web » de PythonAnywhere, dans le fichier
WSGI (bouton « WSGI configuration file »), en remplaçant tout son contenu.

    import os, sys
    path = os.path.expanduser("~/ticmaster")
    ...

Aucune modification n'est nécessaire si le projet est bien dans ~/ticmaster.
Si vous l'avez placé ailleurs, changez seulement la variable PROJECT_DIR.
"""
import os
import sys

PROJECT_DIR = os.path.expanduser("~/ticmaster")

# 1) Le projet doit être importable
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

# 2) Variables d'environnement de production
#    (SECRET_KEY est lue depuis ~/ticmaster/.env si le fichier existe)
os.environ.setdefault("FLASK_ENV", "production")
os.environ.setdefault("COOKIE_SECURE", "1")
os.environ.setdefault("SITE_NAME", "TIC MASTER")
# Sur PythonAnywhere gratuit, pas de PostgreSQL : on reste sur SQLite (~/ticmaster/instance)
if not os.path.exists(os.path.join(PROJECT_DIR, ".env")):
    os.environ.setdefault("SECRET_KEY", "changez-cette-cle-dans-le-fichier-env")

# 3) Application Flask (wsgi.py expose « app » et « application »)
from wsgi import app as application  # noqa: E402
