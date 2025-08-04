from fastapi import HTTPException

from sqlalchemy.dialects.postgresql import UUID

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
