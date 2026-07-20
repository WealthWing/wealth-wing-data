from datetime import date
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.model.models import AccountTypeEnum
from src.schemas.transaction import TransactionSummaryRequest
from src.services.query_service import QueryService
from src.services.transaction_summary import (
    _calendar_month_count,
    build_transaction_summary,
)
from src.util.types import UserPool


class TransactionSummaryRequestTests(TestCase):
    def test_defaults_to_checking_and_credit_card_accounts(self):
        request = TransactionSummaryRequest(
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 30),
        )

        self.assertEqual(
            request.account_types,
            [AccountTypeEnum.CHECKING, AccountTypeEnum.CREDIT_CARD],
        )
        self.assertEqual(_calendar_month_count(request), 1)

    def test_calendar_month_count_includes_months_without_transactions(self):
        request = TransactionSummaryRequest(
            from_date=date(2025, 12, 15),
            to_date=date(2026, 2, 1),
        )

        self.assertEqual(_calendar_month_count(request), 3)

    def test_rejects_reversed_date_range(self):
        with self.assertRaises(ValueError):
            TransactionSummaryRequest(
                from_date=date(2026, 7, 1),
                to_date=date(2026, 6, 30),
            )


class BuildTransactionSummaryTests(IsolatedAsyncioTestCase):
    async def test_builds_expected_summary_without_pagination(self):
        result = SimpleNamespace(
            one=lambda: SimpleNamespace(
                gross_expense=320000,
                refunds=30000,
                income=500000,
                expense_transaction_count=42,
                refund_transaction_count=3,
                income_transaction_count=2,
            )
        )
        db = AsyncMock()
        db.execute.return_value = result
        current_user = UserPool(
            sub=uuid4(),
            email="summary@example.com",
            organization_id=uuid4(),
        )
        request = TransactionSummaryRequest(
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 30),
        )

        with patch(
            "src.services.transaction_summary.get_effective_timezone",
            new=AsyncMock(return_value=(ZoneInfo("UTC"), "UTC")),
        ):
            response = await build_transaction_summary(
                db=db,
                current_user=current_user,
                query_service=QueryService(),
                request=request,
            )

        self.assertEqual(
            response.model_dump(mode="json"),
            {
                "gross_expense": 320000,
                "refunds": 30000,
                "net_spending": 290000,
                "income": 500000,
                "net_activity": 210000,
                "expense_transaction_count": 42,
                "refund_transaction_count": 3,
                "income_transaction_count": 2,
                "average_expense": 7619.05,
                "average_monthly_spending": 290000.0,
                "from_date": "2026-06-01",
                "to_date": "2026-06-30",
                "included_account_types": ["CHECKING", "CREDIT_CARD"],
            },
        )

        statement = db.execute.await_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).upper()
        self.assertIn("ABS(TRANSACTIONS.AMOUNT)", sql)
        self.assertIn("TRANSACTIONS.DATE >=", sql)
        self.assertIn("TRANSACTIONS.DATE <", sql)
        self.assertIn("USER_TABLE.ORGANIZATION_ID", sql)
        self.assertIn("CHECKING", sql)
        self.assertIn("CREDIT_CARD", sql)
        self.assertNotIn(" LIMIT ", sql)
        self.assertNotIn(" OFFSET ", sql)

    async def test_rejects_user_without_an_organization(self):
        current_user = UserPool(
            sub=uuid4(),
            email="summary@example.com",
            organization_id=None,
        )
        request = TransactionSummaryRequest(
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 30),
        )

        with self.assertRaises(HTTPException) as raised:
            await build_transaction_summary(
                db=AsyncMock(),
                current_user=current_user,
                query_service=QueryService(),
                request=request,
            )

        self.assertEqual(raised.exception.status_code, 403)
