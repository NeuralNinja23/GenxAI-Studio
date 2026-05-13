# app/arbormind/phase_3/circularity_monitor.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

# AttentionState: ONE definition, in attention.py.
# No duplicate. No alias. No hack.
from .attention import AttentionState


class CircularityMonitor:
    """
    Detects Ω steady-state (zero-entropy loops).

    This monitor:
    - observes attention evolution
    - never selects
    - never mutates
    """

    def __init__(self, epsilon: float, patience: int):
        self._epsilon = epsilon
        self._patience = patience
        self._history: List[AttentionState] = []

    def observe(self, attention: AttentionState) -> bool:
        """
        Returns True if circularity detected.
        """
        self._history.append(attention)

        if len(self._history) < 2:
            return False

        if self._delta(self._history[-1], self._history[-2]) < self._epsilon:
            stagnant_count = self._count_recent_stagnation()
            return stagnant_count >= self._patience

        return False

    def reset(self) -> None:
        self._history.clear()

    def _count_recent_stagnation(self) -> int:
        count = 0
        for i in range(len(self._history) - 1, 0, -1):
            if self._delta(self._history[i], self._history[i - 1]) < self._epsilon:
                count += 1
            else:
                break
        return count

    def _delta(self, a: AttentionState, b: AttentionState) -> float:
        keys = set(a.weights) | set(b.weights)
        return sum(abs(a.weights.get(k, 0.0) - b.weights.get(k, 0.0)) for k in keys)
