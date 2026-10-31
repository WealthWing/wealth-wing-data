import os
from types import SimpleNamespace
from typing import Annotated
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from jwt import PyJWTError

from src.database.connect import get_db
from src.middleware.auth import AuthMiddleware
from src.model.models import UserRole
from src.schemas.user import Perm
from src.util.types import UserPool
from src.util.user import get_current_user, has_permission


class LocalSwaggerAuthTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(
            uuid=uuid4(),
            email="local@example.com",
            organization_id=uuid4(),
            role=UserRole.User_Viewer,
        )
        env_patch = patch.dict(
            os.environ, {"LOCAL_SWAGGER_USER_ID": str(self.user.uuid)}
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)

        self.db = AsyncMock()
        self.db.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=self.user)
        )
        self.app = FastAPI()
        self.app.add_middleware(AuthMiddleware)

        async def override_db():
            yield self.db

        self.app.dependency_overrides[get_db] = override_db

        @self.app.get("/health/ping")
        async def ping() -> dict:
            return {"message": "healthy"}

        @self.app.get("/private")
        async def private(
            current_user: Annotated[UserPool, Depends(get_current_user)],
        ) -> dict:
            return {
                **current_user.model_dump(mode="json"),
                "can_write": has_permission(current_user, Perm.WRITE),
            }

    async def request(
        self,
        path="/private",
        base_url="http://localhost:5003",
        peer="127.0.0.1",
        headers=None,
    ):
        transport = ASGITransport(app=self.app, client=(peer, 12345))
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            return await client.get(path, headers=headers)

    async def test_local_swagger_uses_existing_user_and_permissions_without_jwt(self):
        with patch("src.middleware.auth.PyJWKClient") as jwks_client:
            response = await self.request(
                headers={"Referer": "http://localhost:5003/docs"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "sub": str(self.user.uuid),
                "email": self.user.email,
                "organization_id": str(self.user.organization_id),
                "role": "User_Viewer",
                "can_write": False,
            },
        )
        jwks_client.assert_not_called()
        statement = self.db.execute.await_args.args[0]
        self.assertEqual(statement.compile().params["uuid_1"], self.user.uuid)

    async def test_ipv4_and_ipv6_loopback_swagger_work(self):
        for base_url, peer in (
            ("http://127.0.0.1:5003", "127.0.0.1"),
            ("http://[::1]:5003", "::1"),
        ):
            with self.subTest(base_url=base_url):
                response = await self.request(
                    base_url=base_url,
                    peer=peer,
                    headers={"Referer": f"{base_url}/docs#/default/private_private_get"},
                )
                self.assertEqual(response.status_code, 200)

    async def test_bypass_is_disabled_without_a_configured_user(self):
        with patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": ""}):
            response = await self.request(
                headers={"Referer": "http://localhost:5003/docs"}
            )

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_malformed_user_id_does_not_break_docs_or_health(self):
        with (
            patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": "<existing-user-uuid>"}),
            self.assertLogs("src.middleware.auth", level="WARNING"),
        ):
            for path in ("/docs", "/openapi.json", "/health/ping"):
                with self.subTest(path=path):
                    response = await self.request(path=path)
                    self.assertEqual(response.status_code, 200)

        self.db.execute.assert_not_awaited()

    async def test_malformed_user_id_returns_a_clear_error_for_local_swagger(self):
        with (
            patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": "<existing-user-uuid>"}),
            self.assertLogs("src.middleware.auth", level="WARNING"),
        ):
            response = await self.request(
                headers={"Referer": "http://localhost:5003/docs"}
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("LOCAL_SWAGGER_USER_ID", response.json()["detail"])
        self.assertIn("valid UUID", response.json()["detail"])
        self.db.execute.assert_not_awaited()

    async def test_malformed_user_id_does_not_bypass_auth_for_other_requests(self):
        with (
            patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": "not-a-uuid"}),
            self.assertLogs("src.middleware.auth", level="WARNING"),
        ):
            response = await self.request()
            self.assertEqual(response.status_code, 401)
            response = await self.request(
                peer="203.0.113.1",
                headers={"Referer": "http://localhost:5003/docs"},
            )
            self.assertEqual(response.status_code, 401)

        self.db.execute.assert_not_awaited()

    async def test_malformed_user_id_does_not_break_valid_bearer_auth(self):
        with (
            patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": "not-a-uuid"}),
            self.assertLogs("src.middleware.auth", level="WARNING"),
            patch("src.middleware.auth.PyJWKClient") as jwks_client,
            patch(
                "src.middleware.auth.decode",
                return_value={"sub": str(self.user.uuid), "email": self.user.email},
            ),
        ):
            response = await self.request(
                headers={
                    "Referer": "http://localhost:5003/docs",
                    "Authorization": "Bearer valid-token",
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sub"], str(self.user.uuid))
        jwks_client.return_value.get_signing_key_from_jwt.assert_called_once_with(
            "valid-token"
        )

    async def test_user_id_accepts_surrounding_whitespace(self):
        with patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": f" {self.user.uuid} "}):
            response = await self.request(
                headers={"Referer": "http://localhost:5003/docs"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sub"], str(self.user.uuid))

    async def test_whitespace_only_user_id_disables_bypass(self):
        with patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": "   "}):
            response = await self.request(
                headers={"Referer": "http://localhost:5003/docs"}
            )

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_direct_api_requests_still_require_a_token(self):
        response = await self.request()

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_non_swagger_and_cross_origin_referrers_require_a_token(self):
        for referer in (
            "http://localhost:5003/",
            "http://localhost:5003/redoc",
            "http://localhost:5003/docs-impersonator",
            "http://localhost:5004/docs",
            "http://localhost:3000/docs",
            "https://localhost:5003/docs",
            "http://127.0.0.1:5003/docs",
            "http://example.com/docs",
            "http://[invalid",
        ):
            with self.subTest(referer=referer):
                response = await self.request(headers={"Referer": referer})
                self.assertEqual(response.status_code, 401)

        self.db.execute.assert_not_awaited()

    async def test_remote_peer_cannot_bypass_with_localhost_headers(self):
        response = await self.request(
            peer="203.0.113.1",
            headers={
                "Referer": "http://localhost:5003/docs",
                "X-Forwarded-For": "127.0.0.1",
                "X-Forwarded-Host": "localhost:5003",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_non_local_host_requires_a_token_even_from_loopback(self):
        response = await self.request(
            base_url="https://api.example.com",
            headers={"Referer": "https://api.example.com/docs"},
        )

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_missing_database_user_does_not_get_a_fabricated_identity(self):
        self.db.execute.return_value.scalar_one_or_none.return_value = None

        response = await self.request(
            headers={"Referer": "http://localhost:5003/docs"}
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("existing database user", response.json()["detail"])

    async def test_supplied_invalid_token_is_still_rejected_on_local_swagger(self):
        with (
            patch("src.middleware.auth.PyJWKClient"),
            patch("src.middleware.auth.decode", side_effect=PyJWTError("invalid")),
        ):
            response = await self.request(
                headers={
                    "Referer": "http://localhost:5003/docs",
                    "Authorization": "Bearer invalid-token",
                }
            )

        self.assertEqual(response.status_code, 401)
        self.db.execute.assert_not_awaited()

    async def test_valid_bearer_token_keeps_its_identity_on_local_swagger(self):
        token_user_id = uuid4()
        self.user.uuid = token_user_id
        with (
            patch("src.middleware.auth.PyJWKClient") as jwks_client,
            patch(
                "src.middleware.auth.decode",
                return_value={"sub": str(token_user_id), "email": self.user.email},
            ) as decode_token,
        ):
            response = await self.request(
                headers={
                    "Referer": "http://localhost:5003/docs",
                    "Authorization": "Bearer valid-token",
                }
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sub"], str(token_user_id))
        jwks_client.return_value.get_signing_key_from_jwt.assert_called_once_with(
            "valid-token"
        )
        self.assertEqual(decode_token.call_args.kwargs["algorithms"], ["RS256"])
        statement = self.db.execute.await_args.args[0]
        self.assertEqual(statement.compile().params["uuid_1"], str(token_user_id))

    async def test_docs_and_openapi_remain_public_without_bypass(self):
        with patch.dict(os.environ, {"LOCAL_SWAGGER_USER_ID": ""}):
            for path in ("/docs", "/openapi.json"):
                with self.subTest(path=path):
                    response = await self.request(path=path)
                    self.assertEqual(response.status_code, 200)

        self.db.execute.assert_not_awaited()


class CurrentUserTests(IsolatedAsyncioTestCase):
    async def test_missing_user_context_returns_unauthorized(self):
        app = FastAPI()
        db = AsyncMock()

        async def override_db():
            yield db

        app.dependency_overrides[get_db] = override_db

        @app.get("/private")
        async def private(
            current_user: Annotated[UserPool, Depends(get_current_user)],
        ) -> UserPool:
            return current_user

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://localhost"
        ) as client:
            response = await client.get("/private")

        self.assertEqual(response.status_code, 401)
        db.execute.assert_not_awaited()
