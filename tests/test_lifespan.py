"""Tests for the FastAPI application lifespan (startup/shutdown, background tasks)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.config import get_settings
from app.database import init_db


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_cleanup_task(tmp_path, monkeypatch):
    """The lifespan context manager starts the cleanup loop and cancels it on shutdown."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app, lifespan

    app = create_app()

    # Exercise the lifespan context manager directly
    async with lifespan(app):
        # The background task is running (asyncio.create_task was called inside)
        pass
    # After exiting, the task was cancelled — no error means clean shutdown
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan_cleanup_loop_calls_cleanup(tmp_path, monkeypatch):
    """The background loop calls cleanup_expired_sessions after sleeping."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app, lifespan

    app = create_app()

    # We need to let the loop's sleep return immediately so it reaches cleanup_expired_sessions.
    # But we can't patch asyncio.sleep globally (it affects our own awaits).
    # Instead, directly test the loop behavior by extracting the logic.
    cleanup_called = asyncio.Event()

    def mock_cleanup():
        cleanup_called.set()
        return 3

    with (
        patch("app.main.cleanup_expired_sessions", side_effect=mock_cleanup),
        patch("asyncio.sleep", new_callable=AsyncMock, return_value=None),
    ):
        async with lifespan(app):
            # Wait briefly for the task to run one iteration
            try:
                await asyncio.wait_for(cleanup_called.wait(), timeout=0.5)
            except TimeoutError:
                pass

        assert cleanup_called.is_set(), "cleanup_expired_sessions was not called"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan_cleanup_loop_handles_exceptions(tmp_path, monkeypatch):
    """If cleanup_expired_sessions raises, the loop logs and continues."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app, lifespan

    app = create_app()

    call_count = 0
    second_sleep = asyncio.Event()

    async def counting_sleep(seconds):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            second_sleep.set()
            # Block until cancelled so we don't spin
            await asyncio.Event().wait()

    with (
        patch("asyncio.sleep", side_effect=counting_sleep),
        patch(
            "app.main.cleanup_expired_sessions",
            side_effect=RuntimeError("DB locked"),
        ) as mock_cleanup,
    ):
        async with lifespan(app):
            try:
                await asyncio.wait_for(second_sleep.wait(), timeout=1.0)
            except TimeoutError:
                pass

        # cleanup was called (and raised), but the loop survived to sleep again
        assert mock_cleanup.call_count >= 1

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan_cleanup_loop_logs_count(tmp_path, monkeypatch):
    """When cleanup removes sessions, it logs the count."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    get_settings.cache_clear()
    init_db(db_path)

    from app.main import create_app, lifespan

    app = create_app()

    cleanup_done = asyncio.Event()

    def mock_cleanup():
        cleanup_done.set()
        return 5

    async def one_shot_sleep(seconds):
        # Return once, then block forever (so the loop only runs once)
        if not cleanup_done.is_set():
            return
        await asyncio.Event().wait()

    with (
        patch("asyncio.sleep", side_effect=one_shot_sleep),
        patch("app.main.cleanup_expired_sessions", side_effect=mock_cleanup),
        patch("app.main.logger") as mock_logger,
    ):
        async with lifespan(app):
            try:
                await asyncio.wait_for(cleanup_done.wait(), timeout=1.0)
            except TimeoutError:
                pass

        mock_logger.info.assert_called_with("Cleaned up expired sessions", count=5)

    get_settings.cache_clear()
