import logging
import os
from ipaddress import ip_address
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from jwt import (
    PyJWTError,
    decode,
    PyJWKClient,
)


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.JWKS_URL = os.getenv("COGNITO_JWKS_URL")
        self.COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
        self.AWS_REGION = os.getenv("AWS_REGION")
        self.COGNITO_ISSUER = os.getenv("COGNITO_ISSUER")
        self.CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
        local_user_id = (os.getenv("LOCAL_SWAGGER_USER_ID") or "").strip()
        self.local_swagger_configured = bool(local_user_id)
        self.local_swagger_user_id = None
        if local_user_id:
            try:
                self.local_swagger_user_id = UUID(local_user_id)
            except ValueError:
                logger.warning(
                    "Local Swagger authentication bypass is unavailable: "
                    "LOCAL_SWAGGER_USER_ID must be a valid UUID from user_table.uuid"
                )

    def _is_local_swagger_request(self, request: Request) -> bool:
        if not self.local_swagger_configured or request.client is None:
            return False

        docs_url = request.app.docs_url
        if not docs_url:
            return False

        try:
            if not ip_address(request.client.host).is_loopback:
                return False

            url = urlsplit(str(request.url))
            referer = urlsplit(request.headers.get("referer", ""))
            docs_path = request.scope.get("root_path", "").rstrip("/") + docs_url
            return (
                url.hostname in {"localhost", "127.0.0.1", "::1"}
                and referer.scheme == url.scheme
                and referer.netloc == url.netloc
                and referer.path in {docs_path, docs_path.rstrip("/") + "/"}
            )
        except ValueError:
            return False

    async def dispatch(self, request: Request, call_next) -> Response:
        public_paths = [
            "/public",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/secure-endpoint",
            "/health",
        ]

        # Allow access to public paths
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        token = request.headers.get("Authorization")

        if not token and self._is_local_swagger_request(request):
            if self.local_swagger_user_id is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": (
                            "LOCAL_SWAGGER_USER_ID must be a valid UUID from "
                            "user_table.uuid. Update your local .env and restart the server."
                        )
                    },
                )
            request.state.local_swagger_user_id = self.local_swagger_user_id
            return await call_next(request)

        if not token:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token[7:]

        try:
            jwks_client = PyJWKClient(self.JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.CLIENT_ID,
                issuer=self.COGNITO_ISSUER,
            )

            user_uuid = payload.get("sub")
            if not user_uuid:
                return JSONResponse(
                    status_code=400, content={"detail": "Invalid token payload"}
                )

            request.state.user = payload
        except PyJWTError as e:
            return JSONResponse(
                status_code=401, content={"detail": "Invalid token", "error": str(e)}
            )

        response = await call_next(request)

        return response
