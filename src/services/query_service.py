from typing import Type
from sqlalchemy.orm import DeclarativeMeta, selectinload
from sqlalchemy import func, select
from src.model.models import User
from src.util.types import UserPool

class QueryService:
    """
    Service class for constructing organization-filtered SQLAlchemy queries.

    Methods
    -------
    org_filtered_query(
    ) -> Select:
        Constructs a SQLAlchemy select query for the given model, filtered by the organization
        of the current user. Optionally applies selectinload for specified relationship attributes.

        Parameters
        ----------
        model : Type[DeclarativeMeta]
            The SQLAlchemy model to query.
        account_attr : str, optional
            The name of the account relationship attribute to eager load.
        category_attr : str, optional
            The name of the category relationship attribute to eager load.
        current_user : UserPool, optional
            The current user object, used to filter by organization.

        Returns
        -------
        Select
            A SQLAlchemy select query object filtered by organization and with optional eager loading.
    """
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
            q = q.options(selectinload(getattr(model, account_attr)))
        if category_attr:
            q = q.options(selectinload(getattr(model, category_attr)))
        return q
    
def get_query_service():
    return QueryService()    