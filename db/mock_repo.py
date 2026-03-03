"""
In-memory mock implementation of :class:`MetricsRepository`.

Writes every mastery update to the application log at INFO level.
No external dependencies — safe to use in development, testing, and
CI without a real database.

Swap this out for a SQLAlchemy or Supabase implementation by replacing
the ``repo`` argument passed to :func:`orchestrator.run`.
"""

from __future__ import annotations

import logging

from db.base_repo import MetricsRepository

logger = logging.getLogger(__name__)


class MockMetricsRepository(MetricsRepository):
    """
    Logs mastery updates instead of writing to a database.

    This serves as the default repository for local development.
    Replace with a real implementation when a database is available::

        from db.sql_repo import SQLMetricsRepository  # future
        repo = SQLMetricsRepository(engine)
        result = await orchestrator.run(code, repo=repo)
    """

    async def update_user_mastery(
        self,
        user_id: str,
        concept: str,
        score: int,
    ) -> None:
        logger.info(
            "[MockRepo] update_user_mastery | user_id=%r  concept=%r  score=%d",
            user_id,
            concept,
            score,
        )
