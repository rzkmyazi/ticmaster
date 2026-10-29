# -*- coding: utf-8 -*-
"""
TIC MASTER #by_Myazirzk — point d'entrée WSGI pour PythonAnywhere.
===============================================================

Fichier **réellement déployé** sur https://myazirzk1.pythonanywhere.com
(emplacement : /var/www/myazirzk1_pythonanywhere_com_wsgi.py).

Il est auto-suffisant : au premier appel de l'application web, il
  • crée le fichier `.env` (clé secrète aléatoire, super administrateur),
  • lance `python seed.py bootstrap` (tables + 12 modules + compte Myazirzk),
  • pose un marqueur pour ne plus jamais recommencer,
puis sert l'application Flask normale.

Sur PythonAnywhere gratuit il n'y a pas de PostgreSQL : la base est SQLite,
dans /home/<utilisateur>/ticmaster/instance/ticmaster.db.

Pour adapter à un autre compte, changez seulement les deux constantes ci-dessous.
"""
import json
import os
import secrets
import shutil
import subprocess
import sys

USER_HOME = os.path.expanduser("~")
PROJ = os.path.join(USER_HOME, "ticmaster")
MARK = os.path.join(USER_HOME, ".tic_bootstrap_done")
ENVFILE = os.path.join(PROJ, ".env")

sys.path.insert(0, PROJ)
os.chdir(PROJ)

STATUS = {"done": os.path.exists(MARK)}


def _write_env():
    """Crée .env une seule fois, avec une clé secrète aléatoire."""
    if os.path.exists(ENVFILE):
        return
    with open(ENVFILE, "w", encoding="utf-8") as f:
        f.write("FLASK_ENV=production\n")
        f.write("COOKIE_SECURE=1\n")
        f.write("SITE_NAME=TIC MASTER\n")
        f.write("SECRET_KEY=%s\n" % secrets.token_hex(32))
        f.write("SUPER_ADMIN_USERNAME=Myazirzk\n")
        f.write("SUPER_ADMIN_PASSWORD=Fiaram131213!!\n")
        f.write("AUTH_SESSION_HOURS=8\n")
        f.write("LOGIN_MAX_ATTEMPTS=5\n")
        f.write("LOGIN_LOCK_MINUTES=15\n")


if not STATUS["done"]:
    try:
        _write_env()
        py = shutil.which("python3.12") or "/usr/local/bin/python3.12"
        r = subprocess.run([py, "seed.py", "bootstrap"], cwd=PROJ,
                           capture_output=True, text=True, timeout=150)
        STATUS["rc"] = r.returncode
        STATUS["out"] = (r.stdout or "")[-2000:]
        STATUS["err"] = (r.stderr or "")[-2000:]
        if r.returncode == 0 and os.path.exists(os.path.join(PROJ, "instance", "ticmaster.db")):
            with open(MARK, "w") as m:
                m.write("ok")
            STATUS["done"] = True
    except Exception as exc:  # noqa: BLE001
        STATUS["error"] = "%s: %s" % (type(exc).__name__, exc)

# Note : la veille 24 h/24 est assurée par le service Render lui-même, qui
# s'appelle toutes les 10 minutes (voir app/veille.py). PythonAnywhere gratuit
# ne peut pas la déclencher : son proxy sortant refuse les sites non listés.

if STATUS["done"]:
    from wsgi import app as application          # noqa: E402
else:
    def application(environ, start_response):
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [json.dumps(STATUS, indent=1, ensure_ascii=False).encode("utf-8")]
