from src.model.models import User, ImportJob, ImportJobStatus
from sqlalchemy import select
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from src.database.connect import DBSession
from src.util.generate_presigned_url import generate_presigned_url
from src.schemas.import_file import ImportFileCreate, ImportFileResponse
from src.util.types import UserPool
from src.util.user import get_current_user

import_router = APIRouter()

@import_router.post("/start", status_code=201, response_model=ImportFileResponse)
async def create_import_job(
    import_data: ImportFileCreate,
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    # Check if user exists
    user_stmt = select(User).where(User.uuid == current_user.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate a presigned URL for the user to upload the file
    presigned_url = await generate_presigned_url(import_job.uuid)

    # Create a new import job
    import_job = ImportJob(
        user_id=user.uuid,
        status=ImportJobStatus.PENDING,
        file_url=presigned_url if presigned_url else None,
        account_id=import_data.account_id,
        file_name=import_data.file_name,
        
    )

    db.add(import_job)
    await db.commit()
    await db.refresh(import_job)



    return {"import_job_id": import_job.uuid, "presigned_url": presigned_url}

@import_router.get("/complete", status_code=200)
async def import_complete(
    import_job_id: str,
    db: DBSession
):
    job = select(ImportJob).where(ImportJob.uuid == import_job_id)
    result = await db.execute(job)
    import_job = result.scalar_one_or_none()
    
    if not import_job:
        raise HTTPException(status_code=404, detail="Import job not found")
    





