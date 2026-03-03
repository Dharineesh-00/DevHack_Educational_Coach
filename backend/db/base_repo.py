"""
Abstract repository interface for user mastery metrics.

Any concrete implementation (SQLAlchemy, Supabase, Redis, etc.) must
subclass :class:`MetricsRepository` and implement every abstract method.
Swap the implementation by passing a different subclass into the
orchestrator — no business logic changes required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MetricsRepository(ABC):
    """
    Defines the persistence contract for learner mastery data.

    All methods are async so that any I/O-bound backend (SQL, HTTP-based
    vector DB, etc.) can be used without blocking the event loop.
    """

    @abstractmethod
    async def update_user_mastery(
        self,
        user_id: str,
        concept: str,
        score: int,
    ) -> None:
        """
        Persist or update a mastery score for a user/concept pair.

        Args:
            user_id: Unique identifier for the learner.
            concept: DSA concept being tracked (e.g. ``"binary_search"``).
            score:   Mastery score (0–100 recommended, but not enforced here).
        """
