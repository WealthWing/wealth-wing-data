from src.services.bank_importers.base import BaseBankImporter
import csv
import io
from src.model.models import ImportJob
from sqlalchemy import select
from src.model.models import Transaction, AccountTypeEnum
import csv
import re
import io
from src.util.category import get_category_id_from_row
from src.util.transaction import (
    get_amount_cents,
    get_internal_type,
    get_date_from_row,
    generate_fingerprint,
    clean_description,
)
from src.util.project import get_project_id_from_row


class ChaseDebitImporter(BaseBankImporter):
    async def parse_csv_transactions(self, import_job: ImportJob):
        current_user = self.current_user
        db = self.db
        # Parse the CSV content
        csv_reader = csv.DictReader(io.StringIO(self.file_content))    
        transactions_and_fps = []
        fingerprints = []
        for row in csv_reader:
            type_ = row.get("Type")
            internal_type = get_internal_type(type_, row.get("Description"))
            amount_str = row.get("Amount", "0").strip()
            amount_cents = get_amount_cents(amount_str)
            date = get_date_from_row(row)
            title = clean_description(row.get("Description"))
            fingerprint = generate_fingerprint(
                date=date, title=title, amount_cents=amount_cents
            )

            category_id = await get_category_id_from_row(
                title, row.get("Category"), current_user.organization_id, db
            )
            project_id = await get_project_id_from_row(
                title=title, organization_id=current_user.organization_id, db=db
            )

            transaction = Transaction(
                user_id=current_user.sub,
                account_id=import_job.account_id,
                import_job_id=import_job.uuid,
                project_id=project_id,
                amount=amount_cents,
                title=title,
                date=date,
                type=internal_type,
                fingerprint=fingerprint,
                category_id=category_id,
            )
            fingerprints.append(fingerprint)
            transactions_and_fps.append((transaction, fingerprint))

            # Query for all fingerprints at once
        existing_fp_result = await db.execute(
            select(Transaction.fingerprint).where(
                Transaction.fingerprint.in_(fingerprints),
                Transaction.account_id == import_job.account_id,
            )
        )
        existing_fingerprints = set(existing_fp_result.scalars().all())

        # Filter only new transactions (deduplicate)
        unique_transactions = [
            txn for txn, fp in transactions_and_fps if fp not in existing_fingerprints
        ]

        return unique_transactions


    @staticmethod
    def can_handle_file(file_name: str, file_type: str, account_type: AccountTypeEnum) -> bool:
        if not file_name or not file_type or not account_type:
            return False
        allowed_types = {"csv", "text/csv"}
        file_type_normalized = file_type.strip().lower()
        if file_type_normalized not in allowed_types:
            return False

        if account_type != AccountTypeEnum.CHECKING:
            return False

        return account_type == AccountTypeEnum.CHECKING
