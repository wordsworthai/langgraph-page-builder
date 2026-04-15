"""Shared utilities for human feedback (no cross-package imports to avoid cycles)."""

from __future__ import annotations

from typing import Any


def is_true(value: Any) -> bool:
    """Return True iff value is exactly True (not truthy, but identity)."""
    return value is True
