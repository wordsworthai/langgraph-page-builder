"""Deterministic sampling helpers for eval set generation."""

from typing import Sequence, TypeVar

T = TypeVar("T")


def pick_by_index(options: Sequence[T], index: int) -> T:
    """Pick a deterministic option using modulo indexing."""
    if not options:
        raise ValueError("Cannot sample from empty options.")
    return options[index % len(options)]

