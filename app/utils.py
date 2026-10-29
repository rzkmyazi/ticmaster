# -*- coding: utf-8 -*-
"""Utilitaires : slugs, rendu de contenu pédagogique sécurisé, uploads."""
from __future__ import annotations

import os
import re
import secrets
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app
from markupsafe import Markup, escape

_SAFE_SCHEMES = {"http", "https", "mailto"}


def slugify(text: str, max_len: int = 90) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    text = re.sub(r"[-\s]+", "-", text)
    return (text[:max_len].strip("-") or secrets.token_hex(4))


def is_safe_url(url: str) -> bool:
    if not url:
        return False
    if url.startswith("/") and not url.startswith("//"):
        return True
    parsed = urlparse(url)
    return parsed.scheme in _SAFE_SCHEMES and bool(parsed.netloc)


_INLINE_BOLD = re.compile(r"\*\*(.+?)\*\*")
_INLINE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def _inline(text: str) -> str:
    out = str(escape(text))
    out = _LINK.sub(lambda m: f'<a href="{escape(m.group(2))}" target="_blank" rel="noopener noreferrer">{m.group(1)}</a>', out)
    out = _INLINE_BOLD.sub(r"<strong>\1</strong>", out)
    out = _INLINE_ITALIC.sub(r"<em>\1</em>", out)
    out = _INLINE_CODE.sub(r"<code>\1</code>", out)
    return out


def render_content(text: str) -> Markup:
    """Rendu Markdown minimal, 100 % échappé (protection XSS)."""
    if not text:
        return Markup("")
    lines = (text or "").replace("\r\n", "\n").split("\n")
    html: list[str] = []
    in_list = False
    in_code = False
    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                html.append("</code></pre>")
                in_code = False
            else:
                html.append('<pre class="code-block"><code>')
                in_code = True
            continue
        if in_code:
            html.append(str(escape(line)) + "\n")
            continue
        if re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                html.append("<ul>")
                in_list = True
            item = re.sub(r"^\s*[-*]\s+", "", line)
            html.append(f"<li>{_inline(item)}</li>")
            continue
        if in_list:
            html.append("</ul>")
            in_list = False
        if not line.strip():
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level = min(6, len(m.group(1)) + 1)
            html.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
        elif line.startswith(">"):
            html.append(f"<blockquote>{_inline(line.lstrip('> ').strip())}</blockquote>")
        else:
            html.append(f"<p>{_inline(line)}</p>")
    if in_list:
        html.append("</ul>")
    if in_code:
        html.append("</code></pre>")
    return Markup("".join(html))


def human_size(num: int | None) -> str:
    num = num or 0
    for unit in ("o", "Ko", "Mo", "Go"):
        if num < 1024:
            return f"{num:.0f} {unit}" if unit == "o" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} To"


def allowed_file(filename: str) -> bool:
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    return ext in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]


IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
_IMAGE_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
}


def is_real_image(stream) -> bool:
    """Vérifie la signature binaire d'une image (un .php renommé est refusé)."""
    if stream is None:
        return False
    position = stream.tell() if hasattr(stream, "tell") else None
    head = stream.read(12)
    if position is not None:
        stream.seek(position)
    if any(head.startswith(sig) for sig in _IMAGE_MAGIC):
        return True
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def save_upload(file_storage) -> tuple[str, str, int] | tuple[None, str, int]:
    """Enregistre un fichier avec un nom aléatoire. Retourne (nom_stocké, nom_original, taille)."""
    if not file_storage or not file_storage.filename:
        return None, "", 0
    original = file_storage.filename
    if not allowed_file(original):
        return None, original, 0
    ext = original.rsplit(".", 1)[-1].lower()
    stored = f"{secrets.token_hex(16)}.{ext}"
    folder = Path(current_app.config["UPLOAD_FOLDER"])
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    file_storage.save(target)
    size = target.stat().st_size
    return stored, original[:255], size


def paginate(query, page: int, per_page: int = 15):
    page = max(1, int(page or 1))
    return query.paginate(page=page, per_page=per_page, error_out=False)
