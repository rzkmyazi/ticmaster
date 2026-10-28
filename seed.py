#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'installation et d'amorçage — TIC MASTER #by_Myazirzk

Exemples :
    python seed.py init --with-demo
    python seed.py superadmin --username Myazirzk
    python seed.py seed
    python seed.py demo
    python seed.py reset-demo
"""
from __future__ import annotations

import argparse
import getpass
import os
import secrets
import sys

from app import create_app
from app.extensions import db
from app.models import (
    Announcement, Attempt, Category, Exercise, Lesson, Message, Module, Option, Question,
    Setting, User, ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_USER, STATUS_ACTIVE,
)
from app.security.core import password_errors, password_ok, generate_password
from app.utils import slugify
from app.seed_content import ANNOUNCEMENTS, CATEGORIES, EXAMS, MODULES


def get_app():
    return create_app()


# ---------------------------------------------------------------------------
def cmd_init(args):
    app = get_app()
    with app.app_context():
        db.create_all()
        defaults = {
            "site_name": "TIC MASTER",
            "site_tagline": "Plateforme de formation aux Technologies de l'Information et de la Communication",
            "support_email": "support@ticmaster.local",
            "maintenance": "0",
            "maintenance_message": "",
        }
        for k, v in defaults.items():
            if not Setting.get(k):
                Setting.set(k, v)
        db.session.commit()
        print("✔ Base de données initialisée :", app.config["SQLALCHEMY_DATABASE_URI"].split("@")[-1])
    if args.with_demo:
        cmd_demo(args)


# ---------------------------------------------------------------------------
def cmd_superadmin(args):
    app = get_app()
    username = args.username or os.environ.get("SUPER_ADMIN_USERNAME", "Myazirzk")
    password = os.environ.get("SUPER_ADMIN_PASSWORD") or args.password
    if not password:
        password = getpass.getpass("Mot de passe du SUPER ADMIN : ")
        confirm = getpass.getpass("Confirmez le mot de passe : ")
        if password != confirm:
            print("✘ Les mots de passe ne correspondent pas.")
            sys.exit(1)
    if not password_ok(password):
        print("✘ Mot de passe trop faible : il faut " + ", ".join(password_errors(password)) + ".")
        sys.exit(1)
    with app.app_context():
        db.create_all()
        existing = User.query.filter_by(username=username).first()
        if existing:
            existing.set_password(password)
            existing.role = ROLE_SUPER_ADMIN
            existing.status = STATUS_ACTIVE
            existing.must_change_password = False
            db.session.commit()
            print(f"✔ Mot de passe du SUPER ADMIN « {username} » mis à jour.")
            return
        user = User(username=username, full_name=args.full_name or "Myazirzk",
                    email=args.email, role=ROLE_SUPER_ADMIN, status=STATUS_ACTIVE,
                    must_change_password=False, bio=args.bio or "Administrateur et fondateur de la plateforme TIC MASTER.")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"✔ SUPER ADMIN « {username} » créé avec succès.")
        print("  Aucune inscription publique n'existe : les comptes suivants seront créés par l'administration.")


# ---------------------------------------------------------------------------
def cmd_seed(args):
    app = get_app()
    with app.app_context():
        db.create_all()
        cats = {}
        for i, (name, desc, icon) in enumerate(CATEGORIES, start=1):
            cat = Category.query.filter_by(slug=slugify(name)).first()
            if not cat:
                cat = Category(name=name, slug=slugify(name), description=desc, icon=icon, order_index=i)
                db.session.add(cat)
                db.session.flush()
            cats[name] = cat

        icons = ["sparkles", "cpu", "settings", "file", "grid", "presentation",
                 "globe", "mail", "shield", "wifi", "code", "sparkles"]
        admin = User.query.filter(User.role.in_([ROLE_SUPER_ADMIN, ROLE_ADMIN])).order_by(User.id).first()
        created_modules = created_questions = 0
        for order, data in enumerate(MODULES, start=1):
            slug = slugify(data["title"])
            if Module.query.filter_by(slug=slug).first():
                continue
            module = Module(
                title=data["title"], slug=slug, summary=data.get("summary", ""),
                description=data.get("description", ""), level=data.get("level", "débutant"),
                category_id=cats[data["category"]].id if data.get("category") in cats else None,
                order_index=order, status="published",
                icon=data.get("icon") or icons[(order - 1) % len(icons)],
                estimated_minutes=data.get("estimated_minutes", 60),
                created_by=admin.id if admin else None,
            )
            db.session.add(module)
            db.session.flush()
            for li, (title, content) in enumerate(data["lessons"], start=1):
                lesson = Lesson(
                    module_id=module.id, title=title, content=content,
                    order_index=li, estimated_minutes=max(10, data.get("estimated_minutes", 60) // len(data["lessons"])),
                    published=True,
                )
                db.session.add(lesson)
            ex_data = data.get("exercise")
            if ex_data:
                ex = Exercise(title=ex_data["title"], description=ex_data.get("description", ""),
                              module_id=module.id, kind="exercise", duration_minutes=15,
                              pass_score=50, published=True, created_by=admin.id if admin else None)
                db.session.add(ex)
                db.session.flush()
                for qi, (text, options, correct, explanation) in enumerate(ex_data["questions"], start=1):
                    q = Question(exercise_id=ex.id, text=text, explanation=explanation, points=1, order_index=qi)
                    db.session.add(q)
                    db.session.flush()
                    for oi, opt_text in enumerate(options, start=1):
                        db.session.add(Option(question_id=q.id, text=opt_text,
                                              is_correct=(oi == correct), order_index=oi))
                    created_questions += 1
            created_modules += 1

        for ex_data in EXAMS:
            if Exercise.query.filter_by(title=ex_data["title"]).first():
                continue
            exam = Exercise(title=ex_data["title"], description=ex_data.get("description", ""),
                            kind="exam", term=ex_data["term"],
                            duration_minutes=ex_data["duration_minutes"],
                            pass_score=ex_data.get("pass_score", 50),
                            max_tab_violations=1, published=True, created_by=admin.id if admin else None)
            db.session.add(exam)
            db.session.flush()
            for qi, (text, options, correct, explanation) in enumerate(ex_data["questions"], start=1):
                q = Question(exercise_id=exam.id, text=text, explanation=explanation, points=1, order_index=qi)
                db.session.add(q)
                db.session.flush()
                for oi, opt_text in enumerate(options, start=1):
                    db.session.add(Option(question_id=q.id, text=opt_text,
                                          is_correct=(oi == correct), order_index=oi))
                created_questions += 1

        for title, body, published in ANNOUNCEMENTS:
            if not Announcement.query.filter_by(title=title).first():
                db.session.add(Announcement(title=title, body=body, published=published,
                                            created_by=admin.id if admin else None))

        db.session.commit()
        print(f"✔ Contenu pédagogique : {created_modules} module(s) créé(s), {created_questions} question(s).")
        print(f"  Modules disponibles : {Module.query.count()} | Exercices/examens : {Exercise.query.count()}")


# ---------------------------------------------------------------------------
def cmd_demo(args):
    app = get_app()
    with app.app_context():
        db.create_all()
        demo_admin = User.query.filter_by(username="admin.demo").first()
        if not demo_admin:
            demo_admin = User(username="admin.demo", full_name="Administrateur Démonstration",
                              email="admin.demo@ticmaster.local", role=ROLE_ADMIN, status=STATUS_ACTIVE,
                              must_change_password=False, avatar_color="#3b82f6",
                              bio="Compte de démonstration illustrant le rôle ADMIN (gestion des utilisateurs et des contenus).")
            demo_admin.set_password("AdminDemo2026!")
            db.session.add(demo_admin)

        demo_user = User.query.filter_by(username="apprenant").first()
        if not demo_user:
            demo_user = User(username="apprenant", full_name="Apprenant Démonstration",
                             email=None, role=ROLE_USER, status=STATUS_ACTIVE, must_change_password=False,
                             avatar_color="#22d3ee",
                             bio="Compte de démonstration illustrant l'espace utilisateur.")
            demo_user.set_password("Apprenant2026!")
            db.session.add(demo_user)
        db.session.commit()
        print("✔ Comptes de démonstration prêts :")
        print("   • admin.demo / AdminDemo2026!      (ADMIN)")
        print("   • apprenant / Apprenant2026!       (UTILISATEUR)")
        print("  ⚠ À supprimer avant toute mise en production réelle.")


def cmd_reset_demo(args):
    app = get_app()
    with app.app_context():
        for username in ("admin.demo", "apprenant"):
            user = User.query.filter_by(username=username).first()
            if user:
                Attempt.query.filter_by(user_id=user.id).delete()
                Message.query.filter_by(sender_id=user.id).delete()
                db.session.delete(user)
        db.session.commit()
        print("✔ Comptes de démonstration supprimés.")


def main():
    parser = argparse.ArgumentParser(description="Installation TIC MASTER")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Crée les tables et les paramètres par défaut")
    p_init.add_argument("--with-demo", action="store_true", help="Crée aussi les comptes de démonstration")
    p_init.set_defaults(func=cmd_init)

    p_super = sub.add_parser("superadmin", help="Crée (ou met à jour) le premier SUPER ADMIN")
    p_super.add_argument("--username", help="Identifiant du super administrateur")
    p_super.add_argument("--password", help="Mot de passe (sinon saisie sécurisée ou variable SUPER_ADMIN_PASSWORD)")
    p_super.add_argument("--full-name", dest="full_name")
    p_super.add_argument("--email")
    p_super.add_argument("--bio")
    p_super.set_defaults(func=cmd_superadmin)

    p_seed = sub.add_parser("seed", help="Charge les 11 modules, exercices et examens")
    p_seed.set_defaults(func=cmd_seed)

    p_demo = sub.add_parser("demo", help="Crée les comptes de démonstration")
    p_demo.set_defaults(func=cmd_demo)

    p_reset = sub.add_parser("reset-demo", help="Supprime les comptes de démonstration")
    p_reset.set_defaults(func=cmd_reset_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
