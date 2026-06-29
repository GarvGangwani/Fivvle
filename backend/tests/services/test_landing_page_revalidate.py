"""Tests for landing page ISR revalidation helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.landing_page_revalidate import revalidate_published_landing_pages


@pytest.mark.asyncio
async def test_revalidate_skips_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "")
    monkeypatch.setenv("REVALIDATE_SECRET", "")

    from app.config import get_settings

    get_settings.cache_clear()

    result = await revalidate_published_landing_pages(["watchtower"])
    assert result is None

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_revalidate_posts_to_frontend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "http://localhost:3000/api/revalidate")
    monkeypatch.setenv("REVALIDATE_SECRET", "test-secret")

    from app.config import get_settings

    get_settings.cache_clear()

    mock_post = AsyncMock(
        return_value=httpx.Response(
            200,
            request=httpx.Request("POST", "http://localhost:3000/api/revalidate"),
            json={"revalidated": True, "slug": "watchtower"},
        ),
    )

    class _MockClient:
        async def __aenter__(self) -> _MockClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        post = mock_post

    with patch(
        "app.services.landing_page_revalidate.httpx.AsyncClient",
        return_value=_MockClient(),
    ):
        result = await revalidate_published_landing_pages(["watchtower"])

    assert result is not None
    mock_post.assert_awaited_once()
    call_kwargs = mock_post.await_args.kwargs
    assert call_kwargs["json"] == {"slug": "watchtower"}
    assert call_kwargs["headers"]["X-Revalidate-Secret"] == "test-secret"

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_revalidate_invalidates_old_and_new_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_REVALIDATE_URL", "http://localhost:3000/api/revalidate")
    monkeypatch.setenv("REVALIDATE_SECRET", "test-secret")

    from app.config import get_settings

    get_settings.cache_clear()

    mock_post = AsyncMock(
        return_value=httpx.Response(
            200,
            request=httpx.Request("POST", "http://localhost:3000/api/revalidate"),
            json={"revalidated": True},
        ),
    )

    class _MockClient:
        async def __aenter__(self) -> _MockClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        post = mock_post

    with patch(
        "app.services.landing_page_revalidate.httpx.AsyncClient",
        return_value=_MockClient(),
    ):
        await revalidate_published_landing_pages(["old-slug-12", "new-slug-34"])

    assert mock_post.await_count == 2
    slugs = [call.kwargs["json"]["slug"] for call in mock_post.await_args_list]
    assert slugs == ["old-slug-12", "new-slug-34"]

    get_settings.cache_clear()
