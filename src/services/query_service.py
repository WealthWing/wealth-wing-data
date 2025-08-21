from typing import Type
from sqlalchemy.orm import DeclarativeMeta, joinedload
from sqlalchemy import func, select
from src.model.models import User
from src.util.types import UserPool

class QueryService:
    def org_filtered_query(
        self,
        model: Type[DeclarativeMeta],
        account_attr: str = None,
        category_attr: str = None,
        current_user: UserPool = None,
    ):
        q = select(model).where(
            model.user_id.in_(
                select(User.uuid).where(
                    User.organization_id == current_user.organization_id
                )
            )
        )
        if account_attr:
            q = q.options(joinedload(getattr(model, account_attr)))
        if category_attr:
            q = q.options(joinedload(getattr(model, category_attr)))
        return q
    
def get_query_service():
    return QueryService()    