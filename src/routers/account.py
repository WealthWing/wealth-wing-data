from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.schemas.account import AccountCreate, AccountResponse
from src.model.models import Account, User
from src.database.connect import DBSession
from src.util.user import get_current_user
from src.util.types import UserPool

account_router = APIRouter()


@account_router.post("/create", status_code=201)
async def create_account(
    account_data: AccountCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    try:
        account = account_data.model_dump(exclude_unset=False)
        new_account = Account(user_id=current_user.sub, **account)

        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)

        return AccountResponse(
            account_name=new_account.account_name,
            institution=new_account.institution,
            last_four=new_account.last_four,
            account_type=new_account.account_type,
            created_at=new_account.created_at,
            updated_at=new_account.updated_at,
            uuid=new_account.uuid,
            user_id=new_account.user_id,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create account: {e}")
    


@account_router.get("/all", response_model=list[AccountResponse])
async def get_accounts(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    try:
        stmt = (
            select(Account)
            .join(User, Account.user_id == current_user.sub)
            .where(User.organization_id == current_user.organization_id)
        )
        
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        

        return accounts or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve accounts: {e}")

