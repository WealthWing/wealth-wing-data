from datetime import datetime
from typing import List
from fastapi import HTTPException
from sqlalchemy import Select, and_, desc, or_
from src.model.param_models import StandardParams, FilterByInputs


class ParamsService:
    """
    Parameters

    stmt (Select): The SQLAlchemy statement to modify.
    model: The SQLAlchemy model that contains the date column.
    params: RdbStandardParams
    search_fields: List[str] Name of the fields to search on.

    Returns:
    Select: The updated select statement with the filters applied.
    """

    def apply_search(
        self, stmt: Select, model, fields: List[str], search: str | None
    ) -> Select:
        """Apply search to the query."""
        if not search:
            return stmt

        conditions = []
        for field_name in fields:
            if not hasattr(model, field_name):
                raise HTTPException(status_code=400, detail="Invalid search field.")

            column_attr = getattr(model, field_name, None)

            if column_attr is not None:
                conditions.append(column_attr.ilike(f"%{search}%"))

        if conditions:
            stmt = stmt.where(or_(*conditions))

        return stmt

    def apply_sort(self, stmt: Select, model, order: str, sort_by: str) -> Select:
        """Apply sorting to the query."""

        if not hasattr(model, sort_by):
            raise HTTPException(status_code=400, detail="Invalid sort_by field.")
        column = getattr(model, sort_by)

        if order.lower() == "desc":
            return stmt.order_by(desc(column))
        return stmt.order_by(column)

    def apply_pagination(self, stmt: Select, page: int, page_size: int) -> Select:
        """Apply pagination to the query."""
        offset = (page - 1) * page_size

        return stmt.offset(offset).limit(page_size)

    def apply_filter(
        self, stmt: Select, model, filters: List[FilterByInputs]
    ) -> Select:
        """Apply filters to the query."""
        conditions = []
        for filter in filters:
            or_clauses = []
            column_attr = getattr(model, filter.field_name, None)
            if column_attr is not None:
                for val in filter.values:
                    if not val or str(val).lower() == "null":
                        or_clauses.append(column_attr.is_(None))
                    else:
                        or_clauses.append(column_attr.like(f"%{val}%"))
            elif filter.field_name == "owned":
                or_clauses.append(model.owner_id.is_(filter.values[0]))

            if or_clauses:
                conditions.append(or_(*or_clauses))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt

    def apply_date_filter(
        self,
        stmt: Select,
        model,
        from_date: datetime,
        to_date: datetime,
        date_field: str,
    ) -> Select:
        """Apply date filter to the query"""

        if not hasattr(model, date_field):
            raise HTTPException(status_code=400, detail="Invalid date field.")

        column_attr = getattr(model, date_field, None)

        if from_date and to_date:
            stmt = stmt.where(column_attr.between(from_date, to_date))
        elif from_date:
            stmt = stmt.where(column_attr >= from_date)
        elif to_date:
            stmt = stmt.where(column_attr <= to_date)
        return stmt
    
    def process_query(
        self,
        stmt: Select,
        model,
        params: StandardParams,
        search_fields: List[str] = None,
    ) -> Select:

        if params.from_date or params.to_date:
            stmt = self.apply_date_filter(
                stmt, model, params.from_date, params.to_date, "created_at"
            )

        if params.filter_by_inputs:
            stmt = self.apply_filter(stmt, model, params.filter_by_inputs)

        if search_fields and params.search:
            stmt = self.apply_search(
                stmt=stmt, model=model, fields=search_fields, search=params.search
            )

        if params.sort_by:
            stmt = self.apply_sort(
                stmt=stmt, model=model, order=params.sort_order, sort_by=params.sort_by
            )

        if params.page_size:
            stmt = self.apply_pagination(stmt, params.page, params.page_size)

        return stmt    
