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
import csv
import boto3
import io


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

    if not import_job or import_job.status != ImportJobStatus.PENDING:
        raise HTTPException(400, "Invalid import job")

    key = "Chase6791_Activity_20250415.CSV"
    try:
        file_content = s3_client.get_s3_file(key=key)
        csv_reader = csv.DictReader(io.StringIO(file_content))

        for row in csv_reader:
            print(row)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read CSV file: {e}")

    return {"message": "Import job completed successfully", "status": "success"}
