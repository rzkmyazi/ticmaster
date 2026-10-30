# -*- coding: utf-8 -*-
"""Nettoyage des textes affichés — TIC MASTER #by_Myazirzk.

Les notifications, les annonces et les titres viennent d'utilisateurs et
d'administrateurs. Ils doivent **toujours** être affichés comme du texte :

* jamais de balise HTML visible (« <script>alert('xss')</script> » ne doit pas
  apparaître tel quel dans le panneau) ;
* jamais d'exécution de script (la sortie reste échappée par le gabarit ou
  posée en `textContent` côté navigateur).

Ce module ne fait pas de « sanitisation HTML partielle » (liste blanche de
balises) : il **retire** le balisage et ne garde que le texte lisible. C'est la
seule approche qui ne peut pas être contournée.
"""
from __future__ import annotations

import html
import re
import unicodedata

#: Balises dont le contenu doit disparaître entièrement (pas seulement la balise).
_BLOCS_DANGEREUX = re.compile(
    r"<(script|style|iframe|object|embed|template|noscript|svg|math)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
#: Balises auto-fermantes ou orphelines de la même famille.
_BALISES_SEULES = re.compile(
    r"</?(script|style|iframe|object|embed|template|noscript|svg|math)\b[^>]*>",
    re.IGNORECASE,
)
_COMMENTAIRES = re.compile(r"<!--.*?-->", re.DOTALL)
_BALISES = re.compile(r"<[^>]{0,400}>")
#:Entités qui resteraient illisibles si on ne les décodait pas.
_ENTITES_RESIDUELLES = re.compile(r"&(?:lt|gt|amp|quot|#\d{1,5}|#x[0-9a-f]{1,4});", re.IGNORECASE)
_CARACTERES_INVISIBLES = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b-\u200f\u202a-\u202e\u2060\ufeff]")
_ESPACES = re.compile(r"\s+")
#: Préfixes d'URL de programme qui n'ont aucun sens en texte affiché.
_SCHEMES = re.compile(r"\b(?:javascript|vbscript|data)\s*:", re.IGNORECASE)


def clean_text(raw: str | None, limit: int = 400, fallback: str = "") -> str:
    """Transforme un texte quelconque en texte affichable, sûr et lisible.

    * décode les entités HTML (y compris doublement encodées) ;
    * supprime les blocs `<script>…</script>`, `<style>…</style>`, `<iframe>`… ;
    * supprime toute balise restante et les commentaires HTML ;
    * retire les caractères de contrôle et invisibles ;
    * normalise les espaces et coupe proprement à `limit` caractères.

    Le résultat ne contient **jamais** de `<` ni de `>` : il peut être affiché
    tel quel, il ne peut pas être interprété comme du HTML.
    """
    texte = "" if raw is None else str(raw)

    # 1. Décodage des entités (au plus 3 tours : « &amp;lt;script&amp;gt; »).
    vus = set()
    for _ in range(3):
        if id(texte) in vus:
            break
        vus.add(id(texte))
        decode = html.unescape(texte)
        if decode == texte:
            break
        texte = decode

    # 2. Retrait du balisage et de son contenu dangereux.
    for _ in range(3):                     # <scr<script>ipt> et imbrications
        avant = texte
        texte = _COMMENTAIRES.sub(" ", texte)
        texte = _BLOCS_DANGEREUX.sub(" ", texte)
        texte = _BALISES_SEULES.sub(" ", texte)
        if texte == avant:
            break
    for _ in range(3):
        avant = texte
        texte = _BALISES.sub(" ", texte)
        if texte == avant:
            break

    # 3. Ce qui reste d'entités (après décodage multiples) repart en clair.
    for _ in range(2):
        if not _ENTITES_RESIDUELLES.search(texte):
            break
        texte = html.unescape(texte)
        texte = _BALISES.sub(" ", texte)

    # 4. Caractères invisibles, schémas exécutables, espaces.
    texte = _CARACTERES_INVISIBLES.sub("", texte)
    texte = _SCHEMES.sub("", texte)
    texte = unicodedata.normalize("NFC", texte)
    texte = texte.replace("\u00a0", " ").replace("\u202f", " ")
    texte = _ESPACES.sub(" ", texte).strip()

    # 5. Dernier filet : plus aucun chevron ne doit subsister.
    texte = texte.replace("<", " ").replace(">", " ")
    texte = _ESPACES.sub(" ", texte).strip()

    if not texte:
        return fallback[:limit]

    if len(texte) > limit:
        coupe = texte[:limit]
        espace = coupe.rfind(" ")
        if espace >= limit - 25:           # coupe au mot, sans casser un mot court
            coupe = coupe[:espace]
        texte = coupe.rstrip(" ,;:.-—") + "…"
    return texte


def clean_title(raw: str | None, limit: int = 120, fallback: str = "Notification") -> str:
    """Version courte, pour les titres (jamais vide)."""
    return clean_text(raw, limit=limit, fallback=fallback) or fallback


def looks_like_markup(raw: str | None) -> bool:
    """Le texte d'origine contenait-il du balisage ou des entités ?"""
    if not raw:
        return False
    return bool(re.search(r"<[a-zA-Z/!]|&(?:lt|gt|amp|quot|#\d+);", str(raw)))


def preview(raw: str | None, limit: int = 160) -> str:
    """Aperçu d'un texte long, pour une notification."""
    return clean_text(raw, limit=limit)
