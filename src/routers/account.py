from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload
from src.schemas.user import Perm
from src.schemas.account import AccountCreate, AccountResponse, AccountUpdate, AccountOptionResponse
from src.model.models import Account, User
from src.database.connect import DBSession
from src.util.user import get_current_user, has_permission
from src.util.types import UserPool
from typing import List
from src.services.query_service import QueryService, get_query_service

account_router = APIRouter()

# TODO - it should show the organization level accounts, not just the user level accounts

@account_router.post("/create", status_code=201, response_model=AccountResponse)
async def create_account(
    account_data: AccountCreate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    if not has_permission(current_user, Perm.WRITE):
        raise HTTPException(403, "User does not have permission to create accounts")
    try:
        account = account_data.model_dump(exclude_unset=False)
        new_account = Account(user_id=current_user.sub, **account)

        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)

        return new_account
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create account: {e}")
    


@account_router.get("/all", response_model=list[AccountResponse])
async def get_accounts(
    db: DBSession, current_user: UserPool = Depends(get_current_user), query_service: QueryService = Depends(get_query_service)
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view accounts")

    try:
        base_stmt = query_service.org_filtered_query(
            model=Account,
            account_attr=None,
            category_attr=None,
            current_user=current_user,
        ).order_by(desc(Account.created_at))

        result = await db.execute(base_stmt)
        accounts = result.scalars().all()
        
        return accounts or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve accounts: {e}")
    


@account_router.get("/options", response_model=List[AccountOptionResponse])
async def get_account_options(
    db: DBSession, current_user: UserPool = Depends(get_current_user)
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view accounts")

    try:
        stmt = select(Account).filter(Account.user_id == current_user.sub)
        result = await db.execute(stmt)
        accounts = result.scalars().all()

        if not accounts:
            raise HTTPException(status_code=404, detail="No accounts found")

        return [
            AccountOptionResponse(value=account.uuid, label=account.account_name)
            for account in accounts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve account options: {e}")    


@account_router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    if not has_permission(current_user, Perm.READ):
        raise HTTPException(403, "User does not have permission to view accounts")

    try:
        stmt = (
            select(Account)
            .filter(Account.uuid == account_id, Account.user_id == current_user.sub)
            .options(joinedload(Account.transactions))
        )
        
        result = await db.execute(stmt)
        account = result.scalars().first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        return account
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve account: {e}")
    

@account_router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    account_data: AccountUpdate,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    if not has_permission(current_user, Perm.WRITE):
        raise HTTPException(403, "User does not have permission to update accounts")
    try:
        stmt = select(Account).where(Account.uuid == account_id, Account.user_id == current_user.sub)
        result = await db.execute(stmt)
        account = result.scalars().first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        for key, value in account_data.model_dump(exclude_unset=True).items():
            if getattr(account, key) != value:
                setattr(account, key, value)
                
        db.add(account)
        await db.commit()
        await db.refresh(account)

        return account
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update account: {e}")    
    
@account_router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    db: DBSession,
    current_user: UserPool = Depends(get_current_user),
):
    if not has_permission(current_user, Perm.DELETE):
        raise HTTPException(403, "User does not have permission to delete accounts")
    try:
        stmt = select(Account).where(Account.uuid == account_id, Account.user_id == current_user.sub)
        result = await db.execute(stmt)
        account = result.scalars().first()

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        await db.delete(account)
        await db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {e}")    