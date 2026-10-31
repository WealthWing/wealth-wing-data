from datetime import datetime, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.database.connect import Base
from src.model.models import Category, Organization, Transaction, User, UserRole
from src.util.category import get_category_id_from_row


class CategoryResolutionTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self.addAsyncCleanup(engine.dispose)
        async with engine.begin() as connection:
            await connection.run_sync(
                Base.metadata.create_all,
                tables=[
                    Organization.__table__,
                    User.__table__,
                    Category.__table__,
                    Transaction.__table__,
                ],
            )

        self.db = async_sessionmaker(engine, expire_on_commit=False)()
        self.addAsyncCleanup(self.db.close)
        self.organization_id = uuid4()
        self.other_organization_id = uuid4()
        self.user_id = uuid4()
        self.other_user_id = uuid4()
        self.db.add_all(
            [
                Organization(uuid=self.organization_id, name="Example"),
                Organization(uuid=self.other_organization_id, name="Other"),
                User(
                    uuid=self.user_id,
                    organization_id=self.organization_id,
                    email="user@example.com",
                    role=UserRole.User,
                ),
                User(
                    uuid=self.other_user_id,
                    organization_id=self.other_organization_id,
                    email="other@example.com",
                    role=UserRole.User,
                ),
            ]
        )
        await self.db.commit()

    async def create_category(self, title, organization_id, type_="CUSTOM"):
        category = Category(
            title=title, organization_id=organization_id, type=type_
        )
        self.db.add(category)
        await self.db.commit()
        return category

    async def create_transaction(self, category_id, user_id=None):
        self.db.add(
            Transaction(
                title="Coffee SHOP Downtown",
                user_id=user_id or self.user_id,
                category_id=category_id,
                amount=-100,
                date=datetime(2026, 10, 30, tzinfo=timezone.utc),
                type="expense",
                fingerprint=uuid4().hex,
            )
        )
        await self.db.commit()

    async def test_historical_org_category_takes_precedence_over_row_category(self):
        historical = await self.create_category("Coffee", self.organization_id)
        await self.create_category("Dining", self.organization_id)
        await self.create_transaction(historical.uuid)

        with patch.object(self.db, "execute", wraps=self.db.execute) as execute:
            category_id = await get_category_id_from_row(
                "coffee shop", "Dining", self.organization_id, self.db
            )

        self.assertEqual(category_id, historical.uuid)
        execute.assert_awaited_once()
        compiled = execute.await_args.args[0].compile(
            dialect=postgresql.dialect()
        )
        sql = str(compiled).upper()
        self.assertIn("TRANSACTIONS.TITLE ILIKE", sql)
        self.assertIn("USER_TABLE.ORGANIZATION_ID =", sql)
        self.assertIn("CATEGORIES.ORGANIZATION_ID =", sql)
        self.assertEqual(
            list(compiled.params.values()).count(self.organization_id), 2
        )

    async def test_ignores_historical_global_and_other_org_categories(self):
        expected = await self.create_category("Dining", self.organization_id)
        for owner in (None, self.other_organization_id):
            with self.subTest(owner=owner):
                historical = await self.create_category("Coffee", owner)
                await self.create_transaction(historical.uuid)

                category_id = await get_category_id_from_row(
                    "coffee shop", "Dining", self.organization_id, self.db
                )

                self.assertEqual(category_id, expected.uuid)

    async def test_ignores_transactions_from_other_organizations(self):
        historical = await self.create_category("Coffee", self.organization_id)
        expected = await self.create_category("Dining", self.organization_id)
        await self.create_transaction(historical.uuid, user_id=self.other_user_id)

        category_id = await get_category_id_from_row(
            "coffee shop", "Dining", self.organization_id, self.db
        )

        self.assertEqual(category_id, expected.uuid)

    async def test_reuses_named_org_category_with_case_and_whitespace_differences(self):
        await self.create_category("Dining", None)
        await self.create_category("Dining", self.other_organization_id)
        expected = await self.create_category("Dining", self.organization_id)

        with patch.object(self.db, "execute", wraps=self.db.execute) as execute:
            category_id = await get_category_id_from_row(
                "New merchant", "  DiNiNg  ", self.organization_id, self.db
            )

        self.assertEqual(category_id, expected.uuid)
        self.assertEqual(expected.title, "Dining")
        self.assertEqual(execute.await_count, 2)
        compiled = execute.await_args.args[0].compile(
            dialect=postgresql.dialect()
        )
        sql = str(compiled).upper()
        self.assertIn("LOWER(CATEGORIES.TITLE) =", sql)
        self.assertIn("CATEGORIES.ORGANIZATION_ID =", sql)
        self.assertIn(self.organization_id, compiled.params.values())
        self.assertIn("dining", compiled.params.values())

    async def test_category_name_wildcards_are_matched_literally(self):
        await self.create_category("Dining A", self.organization_id)
        expected = await self.create_category("Dining_%", self.organization_id)

        category_id = await get_category_id_from_row(
            "New merchant", "dining_%", self.organization_id, self.db
        )

        self.assertEqual(category_id, expected.uuid)

    async def test_creates_named_category_with_org_title_slug_and_type(self):
        for name, type_, expected_type in (
            ("Home Supplies", None, "CUSTOM"),
            ("Dining Out", "expense", "expense"),
        ):
            with self.subTest(type=type_):
                category_id = await get_category_id_from_row(
                    "New merchant",
                    f"  {name}  ",
                    self.organization_id,
                    self.db,
                    type=type_,
                )
                category = await self.db.get(Category, category_id)

                self.assertIsInstance(category_id, UUID)
                self.assertEqual(category.title, name)
                self.assertEqual(category.organization_id, self.organization_id)
                self.assertEqual(category.slug, name.lower().replace(" ", "-"))
                self.assertEqual(category.type, expected_type)
                self.assertIsNone(category.description)

    async def test_creates_org_category_when_only_global_or_other_org_names_exist(self):
        await self.create_category("Travel", None)
        await self.create_category("Travel", self.other_organization_id)

        category_id = await get_category_id_from_row(
            "New merchant", "Travel", self.organization_id, self.db
        )
        category = await self.db.get(Category, category_id)

        self.assertEqual(category.organization_id, self.organization_id)
        self.assertEqual(category.title, "Travel")

    async def test_reuses_org_uncategorized_for_missing_or_blank_names(self):
        await self.create_category("Uncategorized", None, "UNCATEGORIZED")
        await self.create_category(
            "Uncategorized", self.other_organization_id, "UNCATEGORIZED"
        )
        expected = await self.create_category(
            "Uncategorized", self.organization_id, "UNCATEGORIZED"
        )

        for name in (None, "", " \t "):
            with self.subTest(category=name):
                category_id = await get_category_id_from_row(
                    "New merchant",
                    name,
                    self.organization_id,
                    self.db,
                    type="expense",
                )

                self.assertEqual(category_id, expected.uuid)

    async def test_creates_org_uncategorized_with_default_metadata(self):
        await self.create_category("Uncategorized", None, "UNCATEGORIZED")
        await self.create_category(
            "Uncategorized", self.other_organization_id, "UNCATEGORIZED"
        )

        category_id = await get_category_id_from_row(
            "New merchant", None, self.organization_id, self.db, type="expense"
        )
        category = await self.db.get(Category, category_id)

        self.assertIsInstance(category_id, UUID)
        self.assertEqual(category.title, "Uncategorized")
        self.assertEqual(category.organization_id, self.organization_id)
        self.assertEqual(category.slug, "uncategorized")
        self.assertEqual(category.type, "UNCATEGORIZED")
        self.assertEqual(category.description, "Default uncategorized category")

    async def test_repeated_rows_reuse_new_category(self):
        first_id = await get_category_id_from_row(
            "First merchant", "New Category", self.organization_id, self.db
        )
        second_id = await get_category_id_from_row(
            "Second merchant", " NEW CATEGORY ", self.organization_id, self.db
        )
        count = await self.db.scalar(
            select(func.count())
            .select_from(Category)
            .where(Category.organization_id == self.organization_id)
        )

        self.assertEqual(first_id, second_id)
        self.assertEqual(count, 1)


class CategoryResolutionErrorTests(IsolatedAsyncioTestCase):
    async def test_missing_organization_is_rejected_before_database_access(self):
        for organization_id in (None, ""):
            with self.subTest(organization_id=organization_id):
                db = AsyncMock()
                db.add = Mock()

                with self.assertRaises(HTTPException) as raised:
                    await get_category_id_from_row(
                        "New merchant", "Dining", organization_id, db
                    )

                self.assertEqual(raised.exception.status_code, 403)
                db.execute.assert_not_awaited()
                db.add.assert_not_called()
                db.commit.assert_not_awaited()

    async def test_category_creation_failures_roll_back_and_return_http_500(self):
        for category in (None, "Dining"):
            for operation in ("add", "commit", "refresh"):
                with self.subTest(category=category, operation=operation):
                    db = AsyncMock()
                    db.add = Mock()
                    db.execute.return_value = Mock(
                        scalar_one_or_none=Mock(return_value=None)
                    )
                    getattr(db, operation).side_effect = RuntimeError(
                        "database unavailable"
                    )

                    with self.assertRaises(HTTPException) as raised:
                        await get_category_id_from_row(
                            "New merchant", category, uuid4(), db
                        )

                    self.assertEqual(raised.exception.status_code, 500)
                    self.assertIn("Failed to create category", raised.exception.detail)
                    db.rollback.assert_awaited_once()
