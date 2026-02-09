import csv
import io

from sqlalchemy import select
from src.model.models import ImportJob
from src.services.bank_importers.base import BaseBankImporter
from src.model.models import Transaction, AccountTypeEnum
from src.util.category import get_category_id_from_row
from src.util.transaction import (
    clean_description,
    generate_fingerprint,
    get_amount_cents,
    get_date_from_row,
    get_credit_card_internal_type
)


class ChaseCreditImporter(BaseBankImporter):
    async def parse_csv_transactions(self, import_job: ImportJob):
        current_user = self.current_user
        db = self.db
        # Capture scalar IDs once; later awaits/commits can expire ORM instances.
        import_job_id = import_job.uuid
        account_id = import_job.account_id

        csv_reader = csv.DictReader(io.StringIO(self.file_content))
        transactions_and_fps = []
        fingerprints = []

        for row in csv_reader:
            transaction_type = row.get("Type", "")
            internal_type = get_credit_card_internal_type(transaction_type)
            transaction_category = row.get("Category", "")
            transaction_description = row.get("Description", "")
            title = clean_description(transaction_description)
            amount_str = row.get("Amount", "0").strip()
            amount_cents = get_amount_cents(amount_str)
            date = get_date_from_row(row)
            fingerprint = generate_fingerprint(
                date=date, title=title, amount_cents=amount_cents
            )
            transaction_memo = row.get("Memo", "")
            category_id = await get_category_id_from_row(
                title=title,
                category=transaction_category,
                organization_id=current_user.organization_id,
                db=db,
                type=internal_type,
            )
            
            transaction = Transaction(
                user_id=current_user.sub,
                account_id=account_id,
                import_job_id=import_job_id,
                project_id=None,
                amount=amount_cents,
                title=title,
                date=date,
                type=internal_type,
                fingerprint=fingerprint,
                category_id=category_id,
                description=transaction_memo,
            )
            fingerprints.append(fingerprint)
            transactions_and_fps.append((transaction, fingerprint))
            
        existing_fp_result = await db.execute(
            select(Transaction.fingerprint).where(
                Transaction.fingerprint.in_(fingerprints),
                Transaction.account_id == account_id,
            )
        )
        existing_fingerprints = set(existing_fp_result.scalars().all())
        # Filter only new transactions (deduplicate)
        unique_transactions = [
            txn for txn, fp in transactions_and_fps if fp not in existing_fingerprints
        ]

        return unique_transactions
        
    @staticmethod
    def can_handle_file(
        file_name: str, file_type: str, account_type: AccountTypeEnum
    ) -> bool:
        if not file_name or not file_type or not account_type:
            return False
        allowed_types = {"csv", "text/csv"}
        file_type_normalized = file_type.strip().lower()
        if file_type_normalized not in allowed_types:
            return False

        if account_type != AccountTypeEnum.CREDIT_CARD:
            return False

        return account_type == AccountTypeEnum.CREDIT_CARD
