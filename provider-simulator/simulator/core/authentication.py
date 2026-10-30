import hmac

from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.request import Request


class ApiClient:
    """The authenticated caller. The simulator has a single API key, so there is one client."""

    is_authenticated = True


class ApiKeyAuthentication(BaseAuthentication):
    """Authorization: Bearer <SIMULATOR_API_KEY>."""

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[ApiClient, str] | None:
        parts = get_authorization_header(request).decode(errors="replace").split()
        # Auth schemes are case-insensitive (RFC 9110), so "bearer" is accepted too.
        if not parts or parts[0].lower() != self.keyword.lower():
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed("Malformed Authorization header.")
        if not hmac.compare_digest(parts[1], settings.SIMULATOR_API_KEY):
            raise exceptions.AuthenticationFailed("Invalid API key.")
        return ApiClient(), parts[1]

    def authenticate_header(self, request: Request) -> str:
        # A WWW-Authenticate header makes DRF answer 401 instead of 403 when no key is sent.
        return self.keyword
