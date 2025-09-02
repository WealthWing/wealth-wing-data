import os
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from jwt import (
    PyJWTError,
    decode,
    PyJWKClient,
)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.JWKS_URL = os.getenv("COGNITO_JWKS_URL")
        self.COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
        self.AWS_REGION = os.getenv("AWS_REGION")
        self.COGNITO_ISSUER = os.getenv("COGNITO_ISSUER")
        self.CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")

    async def dispatch(self, request: Request, call_next) -> Response:
        public_paths = [
            "/public",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/secure-endpoint" "/health",
        ]

        # Allow access to public paths
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        token = request.headers.get("Authorization")

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
