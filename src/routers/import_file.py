import os
from src.model.param_models import ImportParams
from src.model.models import ImportJob, ImportJobStatus, User
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from fastapi import APIRouter, Depends, HTTPException
from src.database.connect import DBSession
from src.schemas.import_file import (
    ImportFileCreate,
    ImportFileResponse,
    ImportFileListItem,
    ImportCompleteRequest,
)
from src.util.types import UserPool
from src.util.user import get_current_user
from src.util.s3 import S3Client, get_s3_client
from src.services.params import ParamsService
import logging
from src.util.import_file import fail_import_job, update_import_job_status
from src.services.import_manager import get_importer
from src.services.query_service import get_query_service, QueryService

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")

logger = logging.getLogger(__name__)
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

    s3_key = f"{current_user.sub}/{import_job.uuid}/{import_data.file_name.replace(' ', '_')}"
    s3_uri = f"s3://{BUCKET_NAME}/{s3_key}"
    # Generate a presigned URL for the user to upload the file
    presigned_url = s3_client.generate_presigned_url(
        key=s3_key, content_type="text/csv"
    )
    setattr(import_job, "file_url", s3_uri)
    setattr(import_job, "status", ImportJobStatus.PROCESSING)
    setattr(import_job, "file_key", s3_key)

    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)

    return ImportFileResponse(
        uuid=import_job.uuid,
        # Return the presigned URL for the user to upload the file
        file_url=presigned_url,
        file_type=import_job.file_type,
        file_size=import_job.file_size,
        file_name=import_job.file_name,
        status=import_job.status,
        uploaded_at=import_job.uploaded_at,
        account_id=import_job.account_id,
    )


@import_router.post("/complete", status_code=200, response_model=ImportFileResponse)
async def import_complete(
    import_data: ImportCompleteRequest,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
    s3_client: S3Client = Depends(get_s3_client),
    query_service: QueryService = Depends(get_query_service)
):
    base_stmt = query_service.org_filtered_query(
        model=ImportJob,
        account_attr="account",
        current_user=current_user,
    ).filter_by(uuid=import_data.import_job_id)

    result = await db.execute(base_stmt)
    import_job = result.scalar_one_or_none()
    if not import_job:
        logger.error(f"Import job not found for id: {import_data.import_job_id}")
        raise HTTPException(400, "Invalid import job")

    try:
        file_content = s3_client.get_s3_file(key=import_job.file_key)

        if not file_content:
            logger.error(f"File not found in S3 for key: {import_job.file_key}")
            raise HTTPException(status_code=404, detail="File not found in S3")
        
        importer = get_importer(
            file_content=file_content,
            file_name=import_job.file_name,
            file_type=import_job.file_type,
            account_type=import_job.account.account_type,
            db=db,
            s3_client=s3_client,
            current_user=current_user,
        )
        parsed_transactions = await importer.parse_csv_transactions(import_job)
        db.add_all(parsed_transactions)
        await db.commit()

        await update_import_job_status(
            import_job=import_job,
            new_status=ImportJobStatus.COMPLETED,
            db=db,
        )

        return ImportFileResponse.model_validate(import_job)

    except Exception as e:
        logger.error(f"Error processing import job {import_job.uuid}: {e}", exc_info=True)
        await fail_import_job(
            db=db,
            import_job=import_job,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to read CSV file: {e}")


@import_router.get("/imports", status_code=200, response_model=list[ImportFileListItem])
async def get_imports(
    db: DBSession,
    params: ImportParams = Depends(),
    current_user: UserPool = Depends(get_current_user),
    params_service: ParamsService = Depends(ParamsService),
    query_service: QueryService = Depends(get_query_service),
):
    try:
        stmt = query_service.org_filtered_query(
            account_attr="account",
            current_user=current_user,
            model=ImportJob 
        )
        stmt = params_service.process_query(
            stmt=stmt,
            params=params,
            model=ImportJob,
            search_fields=["file_name"],
        )
        result = await db.execute(stmt)
        imports = result.scalars().all()
        return [
            ImportFileListItem(
                account_id=im.account.uuid,
                account_name=im.account.account_name,
                institution=im.account.institution,
                uuid=im.uuid,
                file_name=im.file_name,
                status=im.status,
                uploaded_at=im.uploaded_at,
                error_message=im.error_message,
            )
            for im in imports
        ]
    except Exception as e:
        logger.error(f"Error retrieving imports for user {current_user.sub}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve imports: {e}")
