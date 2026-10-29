# -*- coding: utf-8 -*-
"""Veille 24 h/24 — TIC MASTER #by_Myazirzk.

L'offre gratuite de Render endort un service web après **15 minutes** sans
requête : la visite suivante tombe sur la page « service waking up » pendant
une cinquantaine de secondes.

Pour que le site reste joignable **à n'importe quelle heure**, un fil
d'arrière-plan appelle périodiquement ``/sante`` (qui ne fait qu'un
``SELECT 1``). Il ne s'exécute que si la variable d'environnement ``VEILLE=1``
est présente — c'est le cas sur PythonAnywhere, hébergeur qui ne met jamais
l'application en veille. Render et le poste de développement ne lancent donc
rien.

Réglages facultatifs :
  VEILLE_URL       adresse surveillée (défaut : Render, /sante)
  VEILLE_INTERVAL  secondes entre deux appels (défaut : 300, minimum : 60)
"""
from __future__ import annotations

import logging
import os
import threading
import time
import urllib.error
import urllib.request

_log = logging.getLogger("ticmaster.veille")

DEFAULT_URL = "https://ticmaster.onrender.com/sante"
DEFAULT_INTERVAL = 300
TIMEOUT = 45

_started = False
_thread: threading.Thread | None = None
_lock = threading.Lock()

#: Journal des derniers passages (consultable par le super administrateur).
historique: list[dict] = []


def _boucle(url: str, intervalle: int) -> None:  # pragma: no cover - fil de fond
    while True:
        time.sleep(intervalle)
        debut = time.time()
        etat, detail = "ok", ""
        try:
            requete = urllib.request.Request(url, headers={"User-Agent": "TIC-MASTER-veille/1.0"})
            with urllib.request.urlopen(requete, timeout=TIMEOUT) as reponse:
                detail = f"HTTP {reponse.status}"
                etat = "ok" if reponse.status == 200 else "inattendu"
        except urllib.error.HTTPError as exc:
            etat, detail = "erreur", f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - jamais d'arrêt du fil
            etat, detail = "erreur", type(exc).__name__

        entry = {
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "etat": etat,
            "detail": detail,
            "duree": round(time.time() - debut, 2),
        }
        historique.append(entry)
        del historique[:-20]  # on ne garde que les 20 derniers passages
        if etat == "ok":
            _log.info("veille : %s → %s en %ss", url, detail, entry["duree"])
        else:
            _log.warning("veille : échec sur %s (%s)", url, detail)


def start() -> bool:
    """Démarre la veille si ``VEILLE=1``. Idempotent et sans effet ailleurs."""
    global _started, _thread
    if os.environ.get("VEILLE", "0").strip() not in ("1", "true", "True", "yes", "oui"):
        return False
    with _lock:
        if _started:
            return False
        url = os.environ.get("VEILLE_URL", DEFAULT_URL)
        try:
            intervalle = max(60, int(os.environ.get("VEILLE_INTERVAL", DEFAULT_INTERVAL)))
        except ValueError:
            intervalle = DEFAULT_INTERVAL
        _thread = threading.Thread(
            target=_boucle, args=(url, intervalle), name="veille-render", daemon=True
        )
        _thread.start()
        _started = True
        _log.info("veille démarrée : %s toutes les %s s", url, intervalle)
        return True


def etat() -> dict:
    """État de la veille (utilisé par la page Paramètres du super administrateur)."""
    return {
        "active": _started,
        "url": os.environ.get("VEILLE_URL", DEFAULT_URL),
        "intervalle": int(os.environ.get("VEILLE_INTERVAL", DEFAULT_INTERVAL) or DEFAULT_INTERVAL),
        "derniers": list(reversed(historique[-5:])),
    }
