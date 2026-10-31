from datetime import datetime, timezone
from fastapi import HTTPException
from src.model.models import (
    Account,
    Category,
    Project,
    Subscription,
    Transaction,
    User,
)
from sqlalchemy import select
from src.schemas.transaction import TransactionCreate, TransactionResponse
import hashlib
from src.database.connect import DBSession
import re
from typing import Iterable, Mapping
from uuid import UUID



async def create_transaction_in_db(
    transaction_data: TransactionCreate, db: DBSession, user_id: str
) -> TransactionResponse:
    try:
        user = await _get_user_or_404(db=db, user_id=user_id)
        category = await _get_category_or_404(
            db=db,
            category_id=transaction_data.category_id,
            organization_id=user.organization_id,
        )
        account = await _get_account_or_404(
            db=db,
            account_id=transaction_data.account_id,
            organization_id=user.organization_id,
        )
        project = await _get_project_or_404(
            db=db,
            project_id=transaction_data.project_id,
            organization_id=user.organization_id,
        )
        subscription = await _get_subscription_or_404(
            db=db,
            subscription_id=transaction_data.subscription_id,
            organization_id=user.organization_id,
        )

        date = transaction_data.date or datetime.now(timezone.utc)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        title = transaction_data.title.strip()
        if not title:
            raise HTTPException(status_code=422, detail="title must not be empty")

        transaction = Transaction(
            user_id=user.uuid,
            account_id=account.uuid if account else None,
            project_id=project.uuid if project else None,
            category_id=category.uuid,
            subscription_id=subscription.uuid if subscription else None,
            amount=transaction_data.amount,
            currency=transaction_data.currency or "USD",
            date=date,
            title=title,
            type=transaction_data.type or "expense",
            description=transaction_data.description,
            fingerprint=generate_fingerprint(
                date=date,
                title=title,
                amount_cents=transaction_data.amount,
            ),
            subscription_candidate=(
                False
                if subscription
                else transaction_data.subscription_candidate
            ),
        )

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        return TransactionResponse(
            account_id=transaction.account_id,
            account_name=account.account_name if account else None,
            category=category.title,
            category_id=transaction.category_id,
            project_id=transaction.project_id,
            uuid=transaction.uuid,
            title=transaction.title,
            amount=transaction.amount,
            description=transaction.description,
            date=transaction.date,
            currency=transaction.currency,
            type=transaction.type,
            user_id=transaction.user_id,
            subscription_candidate=transaction.subscription_candidate,
            subscription_id=transaction.subscription_id,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create transaction: {e}"
        )


async def _get_user_or_404(db: DBSession, user_id: str | UUID) -> User:
    result = await db.execute(select(User).where(User.uuid == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _get_category_or_404(
    db: DBSession,
    category_id: UUID,
    organization_id: UUID | None,
) -> Category:
    result = await db.execute(select(Category).where(Category.uuid == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if category.organization_id and category.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def _get_account_or_404(
    db: DBSession,
    account_id: UUID | None,
    organization_id: UUID | None,
) -> Account | None:
    if account_id is None:
        return None

    result = await db.execute(
        select(Account)
        .join(User, Account.user_id == User.uuid)
        .where(
            Account.uuid == account_id,
            User.organization_id == organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


async def _get_project_or_404(
    db: DBSession,
    project_id: UUID | None,
    organization_id: UUID | None,
) -> Project | None:
    if project_id is None:
        return None

    result = await db.execute(
        select(Project)
        .join(User, Project.user_id == User.uuid)
        .where(
            Project.uuid == project_id,
            User.organization_id == organization_id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _get_subscription_or_404(
    db: DBSession,
    subscription_id: UUID | None,
    organization_id: UUID | None,
) -> Subscription | None:
    if subscription_id is None:
        return None

    result = await db.execute(
        select(Subscription)
        .join(User, Subscription.user_id == User.uuid)
        .where(
            Subscription.uuid == subscription_id,
            User.organization_id == organization_id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription


internal_transaction_types = {
    # Direct spending
    "debit_card": "expense",
    "fee_transaction": "expense",
    "billpay": "expense",
    "ach_debit": "expense",

    # Incoming money (default classifications)
    "check_deposit": "income",
    "ach_credit": "income",

    # Transfers between accounts
    "acct_xfer": "transfer",
    "transfer": "transfer",
    "chase_to_partnerfi": "transfer",

    # Ambiguous: require description or account context
    "debit": "unknown",
    "credit": "unknown",
    "loan_pmt": "unknown",
    "withdrawal": "unknown",
    "deposit": "unknown",
}

description_transaction_types = {
    "online transfer to": "transfer",
    "online transfer from": "transfer",
    "payment to chase card": "transfer",
    "payment to credit card": "transfer",
    "credit card payment": "transfer",
    "withdrawal": "transfer",
}


def get_internal_type(type_, description):
    normalized_type = (type_ or "").strip().lower()
    transaction_type = internal_transaction_types.get(
        normalized_type, "unknown"
    )

    if transaction_type != "unknown":
        return transaction_type

    normalized_description = (description or "").strip().lower()

    for keyword, mapped_type in description_transaction_types.items():
        if keyword in normalized_description:
            return mapped_type

    return "unknown"

credit_card_internal_types = {
    "sale": "expense",
    "refund": "refund",
    "payment": "payment",
    "adjustment": "adjustment",
}

def get_credit_card_internal_type(type):
    normalized_type = (type or "").strip().lower()
    return credit_card_internal_types.get(normalized_type, "unknown")
    

def get_amount_cents(amount_str: str) -> int:
    amount = float(amount_str.replace("$", "").replace(",", "").strip())
    return int(round(amount * 100))

DATE_FIELD_ALIASES = (
    "Post Date",
    "Posting Date",
    "Date",
)

DATE_FORMATS = (
    "%m/%d/%Y",
    "%Y-%m-%d",
    "%m/%d/%y",
)

def first_present_value(
    row: Mapping[str, str],
    keys: Iterable[str],
) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return value.strip()
    return None

def parse_date(
    value: str,
    formats: Iterable[str],
) -> datetime:
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")


def get_date_from_row(row: dict) -> datetime:
    date_str = first_present_value(row, DATE_FIELD_ALIASES)
    if not date_str:
        raise ValueError("No date field found in row")

    date_obj = parse_date(date_str, DATE_FORMATS)
    
    print(f"Parsed date: {date_obj} from string: {date_str}")
    return date_obj.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=timezone.utc,
    )


def generate_fingerprint(date, title, amount_cents):
    if isinstance(date, datetime):
        date = date.isoformat()
    return hashlib.sha256(f"{date}{title}{amount_cents}".encode()).hexdigest()[:32]


def clean_description(description: str) -> str:
    cleaned = re.sub(r"PPD ID: \d+", "", description)
    cleaned = re.sub(r"ID: \d+", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = " ".join(cleaned.split()[:5])
    return cleaned.title()
