from src.database.connect import DBSession
from sqlalchemy import select, or_
from src.model.models import Project


async def get_project_id_from_row(
    title: str, organization_id: str, db: DBSession
):
    stmt = select(Project).where(
        Project.project_name.ilike(f"%{title}%"),
        Project.user.has(organization_id=organization_id),
    )
    
    result = await db.execute(stmt)
    if not result:
        return None
    
    project = result.scalar_one_or_none()
    return project.uuid if project else None
