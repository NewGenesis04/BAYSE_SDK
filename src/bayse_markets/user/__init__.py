from __future__ import annotations

import asyncio
import json

import httpx

from bayse_markets._config import Env, TraceConfig, base_url_for
from bayse_markets._logging import get_logger
from bayse_markets._retry import RetryConfig, RetryStrategy
from bayse_markets.exceptions import (
    NetworkError,
    classify_request_sent,
    error_from_response,
)
from bayse_markets.user.models import (
    ApiKey,
    CreateApiKeyRequest,
    ListApiKeysResponse,
    LoginResponse,
    RevokeKeyResponse,
    UserProfile,
)

log = get_logger()


class UserClient:
    """Client for user account management endpoints.

    Bootstraps API key creation via email/password login, then returns
    ``pk_*`` / ``sk_*`` keys for use with :class:`BayseClient`.

    Usage::

        async with UserClient() as user:
            await user.login("you@example.com", "password")
            key = await user.create_api_key("my bot")
            print(f"pk={key.public_key}, sk={key.secret_key}")
    """

    def __init__(
        self,
        *,
        env: Env = Env.PRODUCTION,
        timeout: float = 30.0,
        retry: RetryConfig | None = None,
    ) -> None:
        self._base_url = base_url_for(env)
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self._retry = RetryStrategy(retry or RetryConfig())
        self._trace = TraceConfig()
        self._seq = 0

        self.token: str | None = None
        self.device_id: str | None = None
        self.user_id: str | None = None
        self.public_key: str | None = None

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> UserClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _next_trace_id(self) -> str:
        self._seq += 1
        return f"{self._trace.session_id}-{self._seq:06d}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        params: dict | None = None,
        auth: str | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> dict:
        url = f"{self._base_url}{path}"
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if auth == "token":
            if not self.token or not self.device_id:
                raise RuntimeError(
                    "UserClient not logged in. Call login() first or set token/device_id."
                )
            headers["x-auth-token"] = self.token
            headers["x-device-id"] = self.device_id
        elif auth == "public_key":
            if not self.public_key:
                raise RuntimeError(
                    "public_key not set. Set user.public_key or call create_api_key() first."
                )
            headers["X-Public-Key"] = self.public_key

        if trace_id is None:
            trace_id = self._next_trace_id()
        headers["x-trace-id"] = trace_id

        body_str = json.dumps(body) if body is not None else None

        max_retries = max_retries if max_retries is not None else self._retry.config.max_retries
        replay_is_safe = self._retry.is_idempotent(method)
        attempt = 0

        while True:
            log.debug(
                "UserClient request [%s %s] (attempt %d, trace=%s)",
                method,
                path,
                attempt + 1,
                trace_id,
            )

            try:
                resp = await self._http.request(
                    method, url, headers=headers, content=body_str, params=params
                )
            except httpx.TimeoutException as exc:
                raise NetworkError(
                    message=f"Request timed out after {self._http.timeout} ({type(exc).__name__})",
                    original_exception=exc,
                    request_sent=classify_request_sent(exc),
                )
            except httpx.HTTPError as exc:
                raise NetworkError(
                    message=f"HTTP transport error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                    request_sent=classify_request_sent(exc),
                )

            if resp.status_code < 400:
                data: dict = resp.json()
                log.debug("UserClient response [%d] (trace=%s)", resp.status_code, trace_id)
                return data

            if (
                self._retry.should_retry(attempt, resp.status_code, method=method)
                and attempt < max_retries
            ):
                delay = self._retry.delay(attempt)
                if replay_is_safe:
                    log.debug(
                        "UserClient retry %s %s after %d (attempt %d, delay=%.2fs, trace=%s)",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        delay,
                        trace_id,
                    )
                else:
                    # rotate_api_key returns its secret exactly once. A silent replay
                    # would rotate twice and strand the first secret unrecoverably.
                    log.warning(
                        "UserClient retrying NON-IDEMPOTENT %s %s after %d "
                        "(attempt %d, delay=%.2fs, trace=%s)",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        delay,
                        trace_id,
                    )
                await asyncio.sleep(delay)
                attempt += 1
                continue

            error_data = resp.json()
            error_code = error_data.get("error", "unknown_error")
            error_message = error_data.get("message", "Unknown error")
            raise error_from_response(
                error_code=error_code,
                message=error_message,
                status_code=resp.status_code,
                response_headers=dict(resp.headers),
            )

    async def login(self, email: str, password: str) -> LoginResponse:
        """Authenticate with email and password.

        Stores ``token``, ``device_id``, and ``user_id`` on this instance.
        """
        data = await self._request(
            "POST",
            "/v1/user/login",
            body={"email": email, "password": password},
            auth=None,
        )
        parsed = LoginResponse.model_validate(data)
        self.token = parsed.token
        self.device_id = parsed.device_id
        self.user_id = parsed.user_id
        return parsed

    async def create_api_key(self, name: str) -> ApiKey:
        """Create a new API key.

        The ``secret_key`` is only returned once — save it immediately.

        Also stores ``public_key`` on this instance for subsequent
        ``lookup_user()`` calls.
        """
        data = await self._request(
            "POST",
            "/v1/user/me/api-keys",
            body=CreateApiKeyRequest(name=name).model_dump(mode="json"),
            auth="token",
        )
        parsed = ApiKey.model_validate(data)
        self.public_key = parsed.public_key
        return parsed

    async def list_api_keys(self) -> ListApiKeysResponse:
        """List all active API keys for your account.

        Requires a valid session (call ``login()`` first).

        Returns:
            Response containing the list of API keys and total count.
        """
        data = await self._request(
            "GET",
            "/v1/user/me/api-keys",
            auth="token",
        )
        return ListApiKeysResponse.model_validate(data)

    async def revoke_api_key(self, key_id: str) -> RevokeKeyResponse:
        """Permanently deactivate an API key.

        .. warning::
            Revoking a key is permanent. Any requests signed with the
            revoked key will immediately start returning 401.

        Args:
            key_id: UUID of the API key to revoke.

        Returns:
            Response confirming the revocation.
        """
        data = await self._request(
            "DELETE",
            f"/v1/user/me/api-keys/{key_id}",
            auth="token",
        )
        return RevokeKeyResponse.model_validate(data)

    async def rotate_api_key(self, key_id: str) -> ApiKey:
        """Generate a new secret key while keeping the same key ID.

        .. warning::
            The old secret key stops working immediately. Update all
            services using this key before rotating.

        Args:
            key_id: UUID of the API key to rotate.

        Returns:
            Response containing the new secret key (one-time only).
        """
        data = await self._request(
            "POST",
            f"/v1/user/me/api-keys/{key_id}/rotate",
            auth="token",
        )
        return ApiKey.model_validate(data)

    async def lookup_user(
        self,
        *,
        tag: str | None = None,
        user_id: str | None = None,
    ) -> UserProfile:
        """Resolve a user tag or ID to their public profile.

        Provide exactly one of ``tag`` or ``user_id``.

        Args:
            tag: The user's tag (username). Case-insensitive.
            user_id: The user's ID (UUID).

        Returns:
            Response containing the user's public profile.
        """
        params: dict[str, str] = {}
        if tag is not None:
            params["tag"] = tag
        if user_id is not None:
            params["userId"] = user_id

        data = await self._request(
            "GET",
            "/v1/user/lookup",
            params=params,
            auth="public_key",
        )
        return UserProfile.model_validate(data)
