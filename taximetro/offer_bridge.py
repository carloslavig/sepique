"""Ponte entre o serviço de acessibilidade (Java, lê a tela de outros apps)
e o app Python.

O serviço grava o último pedido de corrida detectado (textos da tela) num
arquivo JSON dentro da pasta interna do app; este módulo lê e entrega esse
arquivo pro resto do app, evitando reprocessar o mesmo pedido duas vezes.
"""
import json
import os
from typing import Optional

from kivy.utils import platform

_last_seen_ms = 0


def _files_dir() -> Optional[str]:
    if platform != "android":
        return None
    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        return PythonActivity.mActivity.getFilesDir().getAbsolutePath()
    except Exception:
        return None


def read_last_offer(path: Optional[str] = None) -> Optional[dict]:
    """Lê o último pedido detectado, só se for mais novo que o último lido."""
    global _last_seen_ms
    if path is None:
        base = _files_dir()
        if base is None:
            return None
        path = os.path.join(base, "last_offer.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    detected_at_ms = data.get("detected_at_ms", 0)
    if detected_at_ms <= _last_seen_ms:
        return None
    _last_seen_ms = detected_at_ms
    return data


def reset_last_seen() -> None:
    """Usado nos testes para não vazar estado entre casos."""
    global _last_seen_ms
    _last_seen_ms = 0
