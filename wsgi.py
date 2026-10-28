# -*- coding: utf-8 -*-
"""Point d'entrée WSGI pour Gunicorn / PythonAnywhere."""
from app import create_app

app = create_app()
application = app
