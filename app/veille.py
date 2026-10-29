# -*- coding: utf-8 -*-
"""Veille 24 h/24 — TIC MASTER #by_Myazirzk.

L'offre gratuite de Render endort un service web après **15 minutes** sans
requête : la visite suivante tombe sur la page « service waking up » pendant
une cinquantaine de secondes.

Pour que le site reste joignable **à n'importe quelle heure**, un fil
d'arrière-plan s'appelle lui-même : un ``GET /sante`` (qui ne fait qu'un
``SELECT 1``) toutes les 10 minutes. Chaque requête entrante remet à zéro le
compteur d'inactivité de Render : le service ne s'endort donc plus et répond
immédiatement, à toute heure.

Le fil démarre automatiquement sur Render, qui fournit la variable
``RENDER_EXTERNAL_URL``. Ailleurs (poste de développement), il ne fait rien.

Réglages facultatifs :
  VEILLE           « 1 » pour forcer la veille hors Render
  VEILLE_URL       adresse appelée (défaut : <RENDER_EXTERNAL_URL>/sante)
  VEILLE_INTERVAL  secondes entre deux appels (défaut : 600, minimum : 60)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

_log = logging.getLogger("ticmaster.veille")

DEFAULT_URL = "https://ticmaster.onrender.com/sante"
DEFAULT_INTERVAL = 600          # 10 min : bien en dessous du seuil de 15 min
TIMEOUT = 45

_started = False
_thread: threading.Thread | None = None
_lock = threading.Lock()

#: Journal des derniers passages (consultable par le super administrateur).
#: Il est aussi écrit sur disque : un redémarrage du serveur web ne perd donc
#: ni l'historique, ni la preuve que le site est bien réveillé.
historique: list[dict] = []


def _fichier() -> Path:
    base = Path(__file__).resolve().parent.parent / "instance"
    base.mkdir(parents=True, exist_ok=True)
    return base / "veille.json"


def _charger() -> None:
    try:
        with open(_fichier(), encoding="utf-8") as fichier:
            data = json.load(fichier)
        if isinstance(data, list):
            historique[:] = data[-20:]
    except Exception:  # noqa: BLE001 - fichier absent ou illisible : on repart de zéro
        pass


def _enregistrer() -> None:
    try:
        with open(_fichier(), "w", encoding="utf-8") as fichier:
            json.dump(historique[-20:], fichier, ensure_ascii=False)
    except Exception:  # noqa: BLE001 - disque en lecture seule : sans conséquence
        pass


def _boucle(url: str, intervalle: int) -> None:  # pragma: no cover - fil de fond
    # Premier passage rapidement après le démarrage (le service Render vient
    # peut-être d'être réveillé par un redémarrage), puis toutes les `intervalle`.
    attente = min(30, intervalle)
    while True:
        time.sleep(attente)
        attente = intervalle
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
            raison = getattr(exc, "reason", exc)
            etat = "erreur"
            detail = f"{type(exc).__name__}: {raison}"[:90]

        entry = {
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "etat": etat,
            "detail": detail,
            "duree": round(time.time() - debut, 2),
        }
        historique.append(entry)
        del historique[:-20]  # on ne garde que les 20 derniers passages
        _enregistrer()
        if etat == "ok":
            _log.info("veille : %s → %s en %ss", url, detail, entry["duree"])
        else:
            _log.warning("veille : échec sur %s (%s)", url, detail)


def _url_par_defaut() -> str:
    """Adresse publique du service, fournie automatiquement par Render."""
    externe = (os.environ.get("RENDER_EXTERNAL_URL") or "").rstrip("/")
    if externe:
        return externe + "/sante"
    return DEFAULT_URL


def actif_sur_ce_serveur() -> bool:
    return bool(os.environ.get("RENDER_EXTERNAL_URL")) or os.environ.get(
        "VEILLE", "0"
    ).strip() in ("1", "true", "True", "yes", "oui")


def start() -> bool:
    """Démarre la veille. Idempotent, sans effet sur un poste de développement."""
    global _started, _thread
    if not actif_sur_ce_serveur():
        return False
    with _lock:
        if _started:
            return False
        url = os.environ.get("VEILLE_URL") or _url_par_defaut()
        try:
            intervalle = max(60, int(os.environ.get("VEILLE_INTERVAL", DEFAULT_INTERVAL)))
        except ValueError:
            intervalle = DEFAULT_INTERVAL
        _charger()
        _thread = threading.Thread(
            target=_boucle, args=(url, intervalle), name="veille-render", daemon=True
        )
        _thread.start()
        _started = True
        _log.info("veille démarrée : %s toutes les %s s", url, intervalle)
        return True


def etat() -> dict:
    """État de la veille (utilisé par la page Paramètres du super administrateur)."""
    if not historique:
        _charger()  # un redémarrage du serveur ne doit pas effacer l'historique
    return {
        "active": _started,
        "disponible": actif_sur_ce_serveur(),
        "url": os.environ.get("VEILLE_URL") or _url_par_defaut(),
        "intervalle": int(os.environ.get("VEILLE_INTERVAL", DEFAULT_INTERVAL) or DEFAULT_INTERVAL),
        "derniers": list(reversed(historique[-5:])),
    }
