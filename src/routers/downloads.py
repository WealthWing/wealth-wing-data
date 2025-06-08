from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from src.database.connect import DBSession
from io import StringIO
import csv
#from src.model.models import Scope
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from fastapi.responses import StreamingResponse


#def get_csv_stream(scopes):
#    buf = StringIO()
#    w = csv.writer(buf)
#    total_cost_sum = 0
#
#    for scope in scopes:
#        # Write the scope name as a header row
#        w.writerow([scope.scope_name])
#        # Write the column headers for expenses
#        w.writerow(["Expense", "Spent"])
#
#        # Write each expense under the scope
#        for expense in scope.expenses:
#            expense_name = expense.title 
#            spent = f"-${expense.amount / 100:.2f}"  
#            w.writerow([expense_name, spent])
#        
#        total_cost_sum += scope.total_cost    
#            
#        w.writerow([])
#
#    w.writerow(['Total Cost Sum', f"${total_cost_sum / 100:.2f}"])
#    buf.seek(0)
#    return buf
#
#
downloads_router = APIRouter()
#
#
#@downloads_router.get("/csv/{project_id}")
#async def download_csv(
#    project_id: str,
#    db: DBSession
#):
#    try:
#        stmt = (
#            select(Scope)
#            .options(joinedload(Scope.expenses))
#            .filter(Scope.project_id == project_id)
#            .order_by(Scope.created_at.desc())
#        )
#
#        scopes = await db.execute(stmt)
#        result = scopes.unique().scalars().all()
#
#        return StreamingResponse(
#            get_csv_stream(result),
#            media_type="text/csv",
#            headers={"Content-Disposition": "attachment; filename={project_id}.csv"},
#        )
#
#    except Exception as e:
#        raise HTTPException(status_code=500, detail=f"Failed to create store: {e}")
