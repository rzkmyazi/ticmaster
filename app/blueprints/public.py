# -*- coding: utf-8 -*-
"""Pages publiques : accueil, à propos (#by_Myazirzk), santé, PWA."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, redirect, render_template, url_for, Response, send_from_directory

from ..extensions import db
from ..models import Module, Lesson, Exercise, User, Question, ROLE_SUPER_ADMIN, ROLE_ADMIN, STATUS_ACTIVE

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    if g.get("user"):
        return redirect(url_for("user.dashboard"))

    modules = (
        Module.query.filter_by(status="published")
        .order_by(Module.order_index)
        .all()
    )
    stats = {
        "modules": len(modules),
        "lessons": Lesson.query.filter_by(published=True).count(),
        "questions": Question.query.count(),
        "learners": User.query.filter(User.status == STATUS_ACTIVE, User.role == "user").count(),
    }
    return render_template("public/index.html", modules=modules, stats=stats)


@bp.route("/a-propos")
def about():
    """Page « à propos » : cible du lien #by_Myazirzk."""
    super_admins = (
        User.query.filter_by(role=ROLE_SUPER_ADMIN, status=STATUS_ACTIVE)
        .order_by(User.created_at.asc())
        .all()
    )
    admins = (
        User.query.filter_by(role=ROLE_ADMIN, status=STATUS_ACTIVE)
        .order_by(User.created_at.asc())
        .all()
    )
    return render_template("public/about.html", super_admins=super_admins, admins=admins)


@bp.route("/sante")
def health():
    """Health check pour Render / sondes de disponibilité."""
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:  # pragma: no cover
        db_ok = False
    payload = {"status": "ok" if db_ok else "degraded", "database": db_ok, "app": "TIC MASTER"}
    return jsonify(payload), (200 if db_ok else 503)


@bp.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "TIC MASTER — Formation TIC",
        "short_name": "TIC MASTER",
        "description": "Plateforme de formation aux Technologies de l'Information et de la Communication.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#050b1d",
        "theme_color": "#060d20",
        "lang": "fr",
        "dir": "ltr",
        "categories": ["education", "productivity"],
        "icons": [
            {"src": url_for("static", filename="img/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": url_for("static", filename="img/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }
    return Response(
        __import__("json").dumps(data),
        mimetype="application/manifest+json",
    )


@bp.route("/service-worker.js")
def service_worker():
    """Service worker minimal : coquille applicative hors-ligne, sans mise en cache des pages privées."""
    js = """
const CACHE = 'ticmaster-v1';
const ASSETS = [
  '/static/css/app.css',
  '/static/js/app.js',
  '/static/img/logo.svg',
  '/static/img/icon-192.png'
];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;
  // Jamais de cache pour les pages dynamiques et l'API
  if (!url.pathname.startsWith('/static/')) return;
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(request, copy));
      return response;
    }))
  );
});
"""
    return Response(js, mimetype="application/javascript")


@bp.route("/favicon.ico")
def favicon():
    try:
        return send_from_directory(
            current_app.static_folder, "img/icon-192.png", mimetype="image/png"
        )
    except Exception:  # pragma: no cover
        return Response(status=204)
