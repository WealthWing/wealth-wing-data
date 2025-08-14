from select import select
from fastapi import HTTPException


from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError
from src.schemas.import_file import ImportFileResponse
from src.database.connect import DBSession
from src.model.models import ImportJob, ImportJobStatus


async def update_import_job_status(
    import_job: ImportJob, new_status: ImportJobStatus, db: DBSession
) -> None:
    if not import_job:
        raise HTTPException(404, "Import job not found")
    import_job.status = new_status
    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)



MAX_ERR = 2000 

async def fail_import_job(db: DBSession, import_job: ImportJob, error_message: str) -> ImportFileResponse:
    if import_job is None:
        raise HTTPException(404, "Import job not found")


    if import_job.status in (ImportJobStatus.COMPLETED, ImportJobStatus.FAILED):
        await db.refresh(import_job)
        return ImportFileResponse.model_validate(import_job)

    import_job.status = ImportJobStatus.FAILED
    import_job.error_message = (error_message or "Failure").strip()[:MAX_ERR]
    import_job.processed_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(500, "Failed to update import job state")

    await db.refresh(import_job)
    return ImportFileResponse.model_validate(import_job)