from datetime import datetime, timezone
from fastapi import HTTPException
from src.model.models import Transaction
from sqlalchemy.orm import Session
from src.schemas.transaction import TransactionCreate
import hashlib
from src.database.connect import DBSession
import re
from typing import Iterable, Mapping



async def create_transaction_in_db(
    transaction_data: TransactionCreate, db: DBSession, user_id: str
) -> Transaction:
    try:
        transaction_dict = transaction_data.model_dump(exclude_unset=False)
        transaction_dict["user_id"] = user_id
        transaction = Transaction(**transaction_dict)

        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create transaction: {e}"
        )

    return transaction


internal_transaction_types = {
    "DEBIT": "expense",
    "CREDIT": "income",
    "CHECK_DEPOSIT": "income",
    "ACH_DEBIT": "expense",
    "ACH_CREDIT": "income",
    "CHASE_TO_PARTNERFI": "expense",
    "ACCT_XFER": "transfer",
    "DEBIT_CARD": "expense",
    "BILLPAY": "expense",
    "LOAN_PMT": "expense",
    "TRANSFER": "transfer",
    "WITHDRAWAL": "expense",
    "DEPOSIT": "income",
    # Fallbacks for common patterns in description
    "Payment to": "expense",
    "Online Payment": "expense",
    "Online Transfer to": "transfer",
    # Credit card Types
}


def get_internal_type(type, description):
    """
    Determines the internal transaction type based on the provided type and description.

    Args:
        type (str): The transaction type to check against known internal types.
        description (str): The transaction description, used for keyword matching if type is not found.

    Returns:
        str: The corresponding internal transaction type if found, otherwise "unknown".
    """
    if type in internal_transaction_types:
        return internal_transaction_types[type]

    for keyword, internal_type in internal_transaction_types.items():
       if keyword.lower() in description.lower():
           return internal_type

    return "unknown"

credit_card_internal_types = {
    "Sale": "expense",
    "Refund": "income",
    "Payment": "payment",
    "Adjustment": "adjustment",
}

def get_credit_card_internal_type(type):
    return credit_card_internal_types.get(type, "unknown")
    

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

