"""Minimal OpenID Connect authorization-code client with PKCE.

Only the operations AstrBot needs are implemented: discovery, authorization URL
construction, code exchange, ID-token verification against the provider JWKS,
and a userinfo fallback. No state is kept here; the caller owns the one-time
``state``/``nonce``/``code_verifier`` map.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

_DISCOVERY_TIMEOUT_SECONDS = 15.0
_TOKEN_TIMEOUT_SECONDS = 15.0
_MAX_RESPONSE_BYTES = 1024 * 1024


class OidcError(RuntimeError):
    """Raised when the OIDC flow cannot complete."""


class OidcClient:
    """A small, strict OIDC client for one configured provider."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self.issuer = str(config.get("issuer") or "").rstrip("/")
        self.client_id = str(config.get("client_id") or "")
        self.client_secret = str(config.get("client_secret") or "")
        self.scopes = str(config.get("scopes") or "openid profile email")
        if not self.issuer or not self.client_id:
            raise OidcError("OIDC issuer and client_id are required")
        self._discovery: dict[str, Any] | None = None
        self._jwks: dict[str, Any] | None = None

    async def _get_json(self, url: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=_DISCOVERY_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
        except httpx.HTTPError as exc:
            raise OidcError("OIDC provider is unreachable") from exc
        if response.status_code >= 400 or len(response.content) > _MAX_RESPONSE_BYTES:
            raise OidcError("OIDC provider returned an invalid response")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OidcError("OIDC provider returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise OidcError("OIDC provider returned an invalid document")
        return payload

    async def discovery(self) -> dict[str, Any]:
        if self._discovery is None:
            document = await self._get_json(
                f"{self.issuer}/.well-known/openid-configuration"
            )
            if document.get("issuer", "").rstrip("/") != self.issuer:
                raise OidcError("OIDC discovery issuer mismatch")
            if not document.get("authorization_endpoint") or not document.get(
                "token_endpoint"
            ):
                raise OidcError("OIDC discovery is missing required endpoints")
            self._discovery = document
        return self._discovery

    async def build_authorization_url(
        self,
        redirect_uri: str,
    ) -> tuple[str, str, str, str]:
        """Return ``(authorize_url, state, nonce, code_verifier)``."""
        document = await self.discovery()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": self.scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return (
            f"{document['authorization_endpoint']}?{urlencode(params)}",
            state,
            nonce,
            code_verifier,
        )

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        document = await self.discovery()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        try:
            async with httpx.AsyncClient(
                timeout=_TOKEN_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    document["token_endpoint"],
                    data=data,
                    headers={"Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise OidcError("OIDC token endpoint is unreachable") from exc
        if response.status_code >= 400 or len(response.content) > _MAX_RESPONSE_BYTES:
            raise OidcError("OIDC token exchange failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OidcError("OIDC token endpoint returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise OidcError("OIDC token endpoint returned an invalid document")
        return payload

    async def verify_id_token(self, id_token: str, nonce: str) -> dict[str, Any]:
        if not id_token:
            raise OidcError("OIDC token response is missing an id_token")
        signing_key = await self._signing_key(id_token)
        try:
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=[signing_key.algorithm_name],
                audience=self.client_id,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise OidcError("OIDC id_token verification failed") from exc
        if nonce and claims.get("nonce") != nonce:
            raise OidcError("OIDC nonce mismatch")
        return claims

    async def _signing_key(self, id_token: str) -> jwt.PyJWK:
        """Fetch and cache the JWKS, returning the key that signed the token.

        The JWKS is fetched with the async HTTP client so a slow provider never
        blocks the event loop.
        """
        document = await self.discovery()
        jwks_uri = document.get("jwks_uri")
        if not jwks_uri:
            raise OidcError("OIDC discovery is missing jwks_uri")
        try:
            header = jwt.get_unverified_header(id_token)
        except jwt.PyJWTError as exc:
            raise OidcError("OIDC id_token header is invalid") from exc
        algorithm = header.get("alg")
        if algorithm not in {"RS256", "ES256", "PS256"}:
            raise OidcError("OIDC id_token uses an unsupported algorithm")
        kid = header.get("kid")
        if self._jwks is None:
            self._jwks = await self._get_json(str(jwks_uri))
        keys = self._jwks.get("keys")
        if not isinstance(keys, list):
            raise OidcError("OIDC JWKS is malformed")
        for jwk in keys:
            if not isinstance(jwk, dict):
                continue
            if kid is not None and jwk.get("kid") != kid:
                continue
            try:
                return jwt.PyJWK.from_dict(jwk, algorithm=algorithm)
            except jwt.PyJWTError as exc:
                raise OidcError("OIDC signing key is invalid") from exc
        raise OidcError("OIDC signing key not found")

    async def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        document = await self.discovery()
        userinfo_endpoint = document.get("userinfo_endpoint")
        if not access_token or not userinfo_endpoint:
            raise OidcError("OIDC userinfo is unavailable")
        try:
            async with httpx.AsyncClient(
                timeout=_TOKEN_TIMEOUT_SECONDS,
                follow_redirects=False,
            ) as client:
                response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.HTTPError as exc:
            raise OidcError("OIDC userinfo endpoint is unreachable") from exc
        if response.status_code >= 400 or len(response.content) > _MAX_RESPONSE_BYTES:
            raise OidcError("OIDC userinfo request failed")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OidcError("OIDC userinfo returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise OidcError("OIDC userinfo returned an invalid document")
        return payload
