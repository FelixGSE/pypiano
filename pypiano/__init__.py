"""Programmatically play piano on top of mingus and fluidsynth."""

# Loads mingus' fluidsynth bindings first, so libfluidsynth is found before any other module imports them
from pypiano import _fluidsynth  # noqa: F401
from pypiano.piano import Piano

__all__ = ["Piano"]
