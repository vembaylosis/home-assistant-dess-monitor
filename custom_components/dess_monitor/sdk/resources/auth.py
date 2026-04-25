from __future__ import annotations

from ..models import Auth
from ..session import Session


class AuthResource:
    """Operations against the auth endpoint.

    Most callers don't touch this directly — :class:`Session` already calls
    ``authSource`` lazily. Use these methods for explicit re-login or to peek
    at the current token.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    async def current(self) -> Auth:
        """Return the cached auth, logging in on first call."""
        return await self._session.get_auth()

    async def login(self) -> Auth:
        """Force a fresh ``authSource`` call, replacing any cached token."""
        return await self._session.get_auth(force_refresh=True)

    async def logout(self) -> None:
        """Drop the cached token. Next request will trigger a re-login."""
        await self._session.invalidate()
