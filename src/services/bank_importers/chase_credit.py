import csv
import io
from model.models import ImportJob
from src.services.bank_importers.base import BaseBankImporter


class ChaseCreditImporter(BaseBankImporter):
    async def parse_csv_transactions(self, import_job: ImportJob):
        current_user = self.current_user
        db = self.db

        csv_reader = csv.DictReader(io.StringIO(self.file_content))
        transactions_and_fps = []
        fingerprints = []
