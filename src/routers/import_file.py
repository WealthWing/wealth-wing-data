import hashlib
from src.model.models import User, ImportJob, ImportJobStatus
from sqlalchemy import select
from fastapi import APIRouter, Depends, File, HTTPException
from src.database.connect import DBSession
from src.schemas.import_file import (
    ImportFileCreate,
    ImportFileResponse,
    ImportCompleteRequest,
)
from src.util.types import UserPool
from src.util.user import get_current_user
from src.util.s3 import S3Client, get_s3_client
from src.model.models import Transaction
import csv
import io
from src.util.import_file import update_import_job_status
from src.util.category import get_category_id_from_row
from src.util.transaction import (
    get_amount_cents,
    get_internal_type,
    get_date_from_row,
    generate_fingerprint,
    clean_description,
)
from src.util.project import get_project_id_from_row
from src.services.import_manager import get_importer


import_router = APIRouter()


@import_router.post("/start", status_code=201, response_model=ImportFileResponse)
async def create_import_job(
    import_data: ImportFileCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    s3_client: S3Client = Depends(get_s3_client),
):

    # Create a new import job
    import_job = ImportJob(
        user_id=current_user.sub,
        status=ImportJobStatus.PENDING,
        file_url=None,
        account_id=import_data.account_id,
        file_name=import_data.file_name,
        file_type=import_data.file_type,
        file_size=import_data.file_size,
    )

    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)

    s3_key = f"{current_user.sub}/{import_job.uuid}"
    # Generate a presigned URL for the user to upload the file
    presigned_url = s3_client.generate_presigned_url(
        key=s3_key, content_type=import_data.file_type
    )
    setattr(import_job, "file_url", presigned_url)
    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)

    return ImportFileResponse(
        uuid=import_job.uuid,
        file_url=import_job.file_url,
        file_type=import_job.file_type,
        file_size=import_job.file_size,
        file_name=import_job.file_name,
        status=import_job.status,
        uploaded_at=import_job.uploaded_at,
        account_id=import_job.account_id,
    )


@import_router.post("/complete", status_code=200)
async def import_complete(
    import_data: ImportCompleteRequest,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    s3_client: S3Client = Depends(get_s3_client),
):
    job = select(ImportJob).filter_by(
        uuid=import_data.import_job_id, user_id=current_user.sub
    )
    result = await db.execute(job)
    import_job = result.scalar_one_or_none()
    if not import_job:
        raise HTTPException(400, "Invalid import job")

    key = "Chase6791_Activity_20250415.CSV"
    try:
        await update_import_job_status(
            import_job=import_job,
            new_status=ImportJobStatus.PENDING,
            db=db,
        )
        file_content = s3_client.get_s3_file(key=key)

        if not file_content:
            raise HTTPException(status_code=404, detail="File not found in S3")

        importer = get_importer(
            file_content=file_content,
            file_name=import_job.file_name,
            file_type=import_job.file_type,
            db=db,
            s3_client=s3_client,
            current_user=current_user,
        )
        parsed_transactions = await importer.parse_csv_transactions(import_job)
        # If all are new, unique_transactions will equal all transactions; if some dups, only new ones are imported
        db.add_all(parsed_transactions)
        await db.commit()

        await update_import_job_status(
            import_job=import_job,
            new_status=ImportJobStatus.COMPLETED,
            db=db,
        )

        return {
            "status": "success",
            "transactions_imported": len(parsed_transactions),
            "import_job": str(import_job.uuid),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read CSV file: {e}")
