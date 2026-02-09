from fastapi import HTTPException


from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from src.schemas.import_file import ImportFileResponse
from src.database.connect import DBSession
from src.model.models import ImportJob, ImportJobStatus
from uuid import UUID


async def update_import_job_status(
    import_job_id: UUID, new_status: ImportJobStatus, db: DBSession
) -> ImportJob:
    db_import_job = await db.get(ImportJob, import_job_id)
    if not db_import_job:
        raise HTTPException(404, "Import job not found")
    db_import_job.status = new_status
    db.add(db_import_job)
    await db.commit()
    await db.refresh(db_import_job)
    return db_import_job



MAX_ERR = 2000 

async def fail_import_job(
    db: DBSession, import_job_id: UUID, error_message: str
) -> ImportFileResponse:
    db_import_job = await db.get(ImportJob, import_job_id)
    if db_import_job is None:
        raise HTTPException(404, "Import job not found")

    if db_import_job.status in (ImportJobStatus.COMPLETED, ImportJobStatus.FAILED):
        await db.refresh(db_import_job)
        return ImportFileResponse.model_validate(db_import_job)

    db_import_job.status = ImportJobStatus.FAILED
    db_import_job.error_message = (error_message or "Failure").strip()[:MAX_ERR]
    db_import_job.processed_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(500, "Failed to update import job state")

    await db.refresh(db_import_job)
    return ImportFileResponse.model_validate(db_import_job)
