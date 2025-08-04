# Registry/factory for importers
from fastapi import Depends
from src.database.connect import DBSession
from src.util.s3 import S3Client, get_s3_client
from src.util.types import UserPool
from src.util.user import get_current_user
from .bank_importers.chase_debit import ChaseDebitImporter
from enum import Enum


IMPORTERS = [ChaseDebitImporter]


def get_importer(
    file_content,
    file_type: str,
    file_name: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    s3_client: S3Client = Depends(get_s3_client),
    metadata=None,
):
    for importer_cls in IMPORTERS:
        if importer_cls.can_handle_file(file_name=file_name, file_type=file_type, metadata=metadata):
            return importer_cls(file_content=file_content, db=db, s3_client=s3_client, current_user=current_user)
    raise ValueError("No suitable importer found for this file.")
