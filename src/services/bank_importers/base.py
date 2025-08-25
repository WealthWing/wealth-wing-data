from src.model.models import ImportJob, ImportJobStatus
from src.database.connect import DBSession
from src.util.s3 import S3Client
from src.util.types import UserPool


class BaseBankImporter:
    def __init__(self, file_content, db: DBSession, s3_client: S3Client, current_user: UserPool ):
        self.file_content = file_content
        self.db = db
        self.s3_client = s3_client
        self.current_user = current_user

    def parse_csv_transactions(self, import_job: ImportJob):
        raise NotImplementedError

    @staticmethod
    def can_handle_file(file_name: str, file_type: str, account_type: ImportJobStatus, metadata=None) -> bool:
        """Optional: Used for format detection/auto-selection."""
        return False