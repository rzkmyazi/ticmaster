# -*- coding: utf-8 -*-
"""Entretien des notifications — TIC MASTER #by_Myazirzk.

Deux opérations, toujours sans risque tant que `--apply` n'est pas passé :

1. **texte**  — nettoie les notifications enregistrées avant la V2.2
   (balises HTML, scripts, entités). Aucune ligne n'est supprimée.
2. **doublons** — regroupe les notifications strictement identiques d'une même
   personne (même type, même titre, même texte) et ne garde que la plus
   récente. Par défaut, uniquement les annonces : deux messages identiques
   envoyés à deux moments différents restent deux notifications distinctes.

Exemples :
    python tools/repair_notifications.py                 # état des lieux
    python tools/repair_notifications.py --apply         # corrige le texte
    python tools/repair_notifications.py --doublons --apply
    python tools/repair_notifications.py --doublons --kind message --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

os.environ.setdefault("FLASK_ENV", os.environ.get("FLASK_ENV", "production"))


def _app():
    from app import create_app
    return create_app(os.environ.get("FLASK_CONFIG"))


def etat_des_lieux(app) -> None:
    from sqlalchemy import or_

    from app.extensions import db
    from app.models import Notification

    with app.app_context():
        total = Notification.query.count()
        balises = Notification.query.filter(or_(
            Notification.title.like("%<%"), Notification.title.like("%&%"),
            Notification.body.like("%<%"), Notification.body.like("%&%"),
        )).count()
        sans_texte = Notification.query.filter(
            Notification.body.like("Contenu retiré%")).count()
        groupes = db.session.query(
            Notification.user_id, Notification.kind, Notification.title, Notification.body
        ).group_by(
            Notification.user_id, Notification.kind, Notification.title, Notification.body
        ).having(db.func.count(Notification.id) > 1).all()
        en_trop = 0
        for user_id, kind, title, body in groupes:
            n = Notification.query.filter_by(user_id=user_id, kind=kind,
                                             title=title, body=body).count()
            en_trop += n - 1
        print(f"Notifications en base ......... {total}")
        print(f"Contenant encore du balisage . {balises}")
        print(f"Corps « contenu retiré » ..... {sans_texte}")
        print(f"Groupes en double ............ {len(groupes)} ({en_trop} lignes en trop)")


def nettoyer_texte(app, apply: bool) -> int:
    from app.extensions import db
    from app.models import Notification
    from app.notifications import sanitize_rows

    with app.app_context():
        if not apply:
            from sqlalchemy import or_
            reste = Notification.query.filter(or_(
                Notification.title.like("%<%"), Notification.title.like("%&%"),
                Notification.body.like("%<%"), Notification.body.like("%&%"),
            )).count()
            print(f"[simulation] {reste} notification(s) à nettoyer — relancer avec --apply")
            db.session.rollback()
            return reste
        corrigees = sanitize_rows(limit=100000)
        print(f"{corrigees} notification(s) nettoyée(s).")
        return corrigees


def supprimer_doublons(app, kind: str | None, apply: bool) -> int:
    from app.extensions import db
    from app.models import Notification

    with app.app_context():
        base = Notification.query
        if kind:
            base = base.filter(Notification.kind == kind)
        rows = base.order_by(Notification.created_at.desc(), Notification.id.desc()).all()

        vues: dict[tuple, int] = {}
        a_supprimer: list[Notification] = []
        for row in rows:
            cle = (row.user_id, row.kind, row.title, row.body)
            if cle in vues:              # on garde la plus récente
                a_supprimer.append(row)
            else:
                vues[cle] = row.id

        compteur = Counter(r.title[:40] for r in a_supprimer)
        print(f"{len(a_supprimer)} doublon(s) identifié(s)"
              + (f" (type {kind})" if kind else ""))
        for titre, n in compteur.most_common(10):
            print(f"  · {titre:<42} {n} en trop")

        if not apply:
            print("[simulation] aucune suppression — relancer avec --apply")
            db.session.rollback()
            return len(a_supprimer)

        for row in a_supprimer:
            db.session.delete(row)
        db.session.commit()
        print(f"{len(a_supprimer)} doublon(s) supprimé(s) : une seule copie conservée par personne.")
        return len(a_supprimer)


def main() -> int:
    parser = argparse.ArgumentParser(description="Entretien des notifications TIC MASTER")
    parser.add_argument("--apply", action="store_true", help="écrit réellement en base")
    parser.add_argument("--texte", action="store_true", help="nettoie le balisage (défaut)")
    parser.add_argument("--doublons", action="store_true", help="supprime les doublons")
    parser.add_argument("--kind", default="annonce",
                        help="type concerné par la déduplication (défaut : annonce)")
    args = parser.parse_args()

    app = _app()
    etat_des_lieux(app)

    if args.doublons:
        supprimer_doublons(app, args.kind or None, args.apply)
    else:
        nettoyer_texte(app, args.apply)

    print("\nÉtat après opération :")
    etat_des_lieux(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
