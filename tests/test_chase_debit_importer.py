from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from src.services.bank_importers.chase_debit import ChaseDebitImporter


class ChaseDebitImporterTests(IsolatedAsyncioTestCase):
    async def test_parse_accepts_chase_debit_export_with_post_date(self):
        csv_content = (
            "Category,Transaction Date,Description,Post Date,Memo,Type,Amount\n"
            "Shopping,10/29/2026,Example Store,10/30/2026,Card purchase,Sale,-12.34\n"
        )
        subscription_result = Mock()
        subscription_result.scalar_one_or_none.return_value = None
        fingerprints_result = Mock()
        fingerprints_result.scalars.return_value.all.return_value = []
        db = Mock()
        db.execute = AsyncMock(side_effect=[subscription_result, fingerprints_result])
        current_user = SimpleNamespace(sub="user-id", organization_id="organization-id")
        import_job = SimpleNamespace(uuid="job-id", account_id="account-id")

        with (
            patch(
                "src.services.bank_importers.chase_debit.get_category_id_from_row",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.bank_importers.chase_debit.get_project_id_from_row",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.bank_importers.chase_debit.transaction_is_subscription_candidate",
                new=AsyncMock(return_value=False),
            ),
        ):
            importer = ChaseDebitImporter(
                file_content=csv_content,
                db=db,
                s3_client=None,
                current_user=current_user,
            )
            transactions = await importer.parse_csv_transactions(import_job)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(
            transactions[0].date, datetime(2026, 10, 30, tzinfo=timezone.utc)
        )
        self.assertEqual(transactions[0].amount, -1234)
