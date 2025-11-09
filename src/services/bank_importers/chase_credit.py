import csv
import io
from model.models import ImportJob
from src.services.bank_importers.base import BaseBankImporter
from util.transaction import clean_description, generate_fingerprint, get_amount_cents, get_date_from_row, get_internal_type


class ChaseCreditImporter(BaseBankImporter):
    async def parse_csv_transactions(self, import_job: ImportJob):
        current_user = self.current_user
        db = self.db

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