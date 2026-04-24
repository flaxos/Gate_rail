"""Compatibility package to support running without installation.

This allows commands like ``python -m gaterail.main`` from the repository root
by extending package search path to include ``src/gaterail``.
"""

from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]
_src_package = Path(__file__).resolve().parent.parent / "src" / "gaterail"
if _src_package.exists():
    __path__.append(str(_src_package))
