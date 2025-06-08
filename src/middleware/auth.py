import os
from fastapi import FastAPI, Request, HTTPException, Response
from requests import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from jwt import (
    PyJWTError,
    decode,
    PyJWKClient,
)
from src.model.models import User

# from src.database.connect import SessionLocal, session

JWKS_URL = os.environ.get("COGNITO_JWKS_URL")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID")
AWS_REGION = os.environ.get("AWS_REGION")
COGNITO_ISSUER = os.environ.get("COGNITO_ISSUER")
CLIENT_ID = os.environ.get("COGNITO_CLIENT_ID")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.jwk_client = PyJWKClient(JWKS_URL)

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
            jwks_client = PyJWKClient(JWKS_URL)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=CLIENT_ID,
                issuer=COGNITO_ISSUER,
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
