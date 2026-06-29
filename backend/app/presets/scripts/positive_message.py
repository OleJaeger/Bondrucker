"""Liefert eine zufaellig ausgewaehlte, aufmunternde Nachricht.

Bewusst ohne Emojis - die Font A des ESC/POS-Druckers unterstuetzt nur
einen begrenzten Zeichensatz.
"""

from __future__ import annotations

import random

_MESSAGES = [
    "Du schaffst das!",
    "Heute ist ein guter Tag fuer einen neuen Anfang.",
    "Du bist staerker, als du denkst.",
    "Kleine Schritte fuehren auch zum Ziel.",
    "Glaub an dich - andere tun es auch.",
    "Jeder Tag bringt eine neue Chance.",
    "Du hast schon so viel gemeistert.",
    "Atme tief durch und laechle.",
    "Dein Einsatz macht einen Unterschied.",
    "Es ist okay, auch mal langsamer zu machen.",
    "Du bist genau richtig, so wie du bist.",
    "Heute wartet etwas Schoenes auf dich.",
    "Sei stolz auf das, was du schon erreicht hast.",
    "Ein Laecheln kann den ganzen Tag veraendern.",
    "Du machst das richtig gut.",
]


def generate() -> str:
    return random.choice(_MESSAGES)
