from datetime import datetime, timezone
from fastapi import HTTPException
from src.model.models import Transaction
from sqlalchemy.orm import Session
from src.schemas.transaction import TransactionCreate
import hashlib
from src.database.connect import DBSession
import re


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
}


def get_internal_type(type, description):
    if type in internal_transaction_types:
        return internal_transaction_types[type]

    for keyword, internal_type in internal_transaction_types.items():
       if keyword.lower() in description.lower():
           return internal_type

    return "unknown"


def get_amount_cents(amount_str: str) -> int:
    amount = float(amount_str.replace("$", "").replace(",", "").strip())
    return int(round(amount * 100))


def get_date_from_row(row: dict) -> str:
    date_str = row.get("Posting Date") or row.get("Date")
    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
    date_obj = date_obj.replace(tzinfo=timezone.utc)
    return date_obj


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
