from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from dateutil.relativedelta import relativedelta
from faker import Faker
from sqlalchemy import func, select

from src.database.connect import DBSession
from src.model.models import (
    Account,
    AccountTypeEnum,
    Category,
    Organization,
    Subscription,
    Transaction,
    User,
)
from src.services.subscription_candidate_service import mark_subscription_candidates
from src.util.category import get_category_id_from_row
from src.util.transaction import clean_description, generate_fingerprint


@dataclass
class SeedSummary:
    organization_id: UUID
    user_id: UUID
    checking_account_id: UUID
    credit_card_account_id: UUID
    created: dict[str, int] = field(default_factory=dict)
    skipped_transactions: int = 0


@dataclass(frozen=True)
class SeedTransactionRow:
    account_type: AccountTypeEnum
    day: int
    description: str
    category: str
    type: str
    amount: int
    subscription_name: str | None = None


@dataclass(frozen=True)
class SeedTransactionTemplate:
    account_type: AccountTypeEnum
    day: int
    category: str
    type: str
    min_amount: int
    max_amount: int


async def seed_demo_data(
    db: DBSession,
    organization_id: UUID,
    user_id: UUID,
    months: int = 6,
) -> SeedSummary:
    """
    Create relationship-complete demo data for an existing organization and user.

    The seed is safe to rerun. The organization and user must already exist, and
    the user must belong to the organization. Seeded transactions are deduplicated
    by the same account-scoped fingerprint strategy used by bank imports.
    """
    created: dict[str, int] = {
        "categories": 0,
        "accounts": 0,
        "subscriptions": 0,
        "transactions": 0,
    }

    organization = await _get_organization_or_raise(
        db=db,
        organization_id=organization_id,
    )
    user = await _get_user_in_organization_or_raise(
        db=db,
        user_id=user_id,
        organization_id=organization.uuid,
    )
    organization_id_value = organization.uuid
    user_id_value = user.uuid

    categories_before = await _count_org_categories(
        db=db,
        organization_id=organization_id_value,
    )

    checking, was_created = await _get_or_create_account(
        db=db,
        user_id=user_id_value,
        account_name="Demo Checking",
        account_type=AccountTypeEnum.CHECKING,
        institution="Chase",
        last_four="1234",
    )
    checking_account_id = checking.uuid
    created["accounts"] += int(was_created)

    credit_card, was_created = await _get_or_create_account(
        db=db,
        user_id=user_id_value,
        account_name="Demo Freedom Card",
        account_type=AccountTypeEnum.CREDIT_CARD,
        institution="Chase",
        last_four="9876",
    )
    credit_card_account_id = credit_card.uuid
    created["accounts"] += int(was_created)

    fake = _faker_for("subscription", organization_id_value, user_id_value)
    subscription_name = f"{fake.company()} Pro"
    subscription_category_id = await get_category_id_from_row(
        title=subscription_name,
        category="Subscriptions",
        organization_id=organization_id_value,
        db=db,
        type="expense",
    )
    subscription, was_created = await _get_or_create_subscription(
        db=db,
        user_id=user_id_value,
        category_id=subscription_category_id,
        name=subscription_name,
        amount=-999,
    )
    subscription_id_value = subscription.uuid
    subscription_name_value = subscription.name
    created["subscriptions"] += int(was_created)

    transactions = await _build_transactions(
        db=db,
        organization_id=organization_id_value,
        user_id=user_id_value,
        checking_account_id=checking_account_id,
        credit_card_account_id=credit_card_account_id,
        subscription_id=subscription_id_value,
        subscription_name=subscription_name_value,
        months=max(months, 1),
    )
    inserted, skipped = await _insert_missing_transactions(db, transactions)
    created["transactions"] += inserted
    categories_after = await _count_org_categories(
        db=db,
        organization_id=organization_id_value,
    )
    created["categories"] = max(categories_after - categories_before, 0)

    await mark_subscription_candidates(
        db=db,
        user_id=user_id_value,
        account_id=checking_account_id,
    )
    await db.commit()

    return SeedSummary(
        organization_id=organization_id_value,
        user_id=user_id_value,
        checking_account_id=checking_account_id,
        credit_card_account_id=credit_card_account_id,
        created=created,
        skipped_transactions=skipped,
    )


async def _get_organization_or_raise(
    db: DBSession,
    organization_id: UUID,
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.uuid == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ValueError(f"Organization not found: {organization_id}")
    return organization


async def _get_user_in_organization_or_raise(
    db: DBSession,
    user_id: UUID,
    organization_id: UUID,
) -> User:
    result = await db.execute(
        select(User).where(
            User.uuid == user_id,
            User.organization_id == organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError(
            f"User {user_id} was not found in organization {organization_id}"
        )
    return user


async def _count_org_categories(
    db: DBSession,
    organization_id: UUID,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Category)
        .where(Category.organization_id == organization_id)
    )
    return result.scalar_one()


async def _get_or_create_account(
    db: DBSession,
    user_id: UUID,
    account_name: str,
    account_type: AccountTypeEnum,
    institution: str,
    last_four: str,
) -> tuple[Account, bool]:
    result = await db.execute(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_name == account_name,
        )
    )
    account = result.scalar_one_or_none()
    if account:
        return account, False

    account = Account(
        user_id=user_id,
        account_name=account_name,
        account_type=account_type,
        institution=institution,
        last_four=last_four,
    )
    db.add(account)
    await db.flush()
    return account, True


async def _get_or_create_subscription(
    db: DBSession,
    user_id: UUID,
    category_id: UUID,
    name: str,
    amount: int,
) -> tuple[Subscription, bool]:
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.name == name,
        )
    )
    subscription = result.scalar_one_or_none()
    if subscription:
        return subscription, False

    now = datetime.now(timezone.utc)
    subscription = Subscription(
        user_id=user_id,
        category_id=category_id,
        name=name,
        amount=amount,
        currency="USD",
        billing_frequency="monthly",
        start_date=now - relativedelta(months=6),
        next_billing_date=now + relativedelta(months=1),
        auto_renew=True,
        status="active",
        payment_method="Demo Checking",
        total_amount_spent=abs(amount * 6) / 100,
    )
    db.add(subscription)
    await db.flush()
    return subscription, True


async def _build_transactions(
    db: DBSession,
    organization_id: UUID,
    user_id: UUID,
    checking_account_id: UUID,
    credit_card_account_id: UUID,
    subscription_id: UUID,
    subscription_name: str,
    months: int,
) -> list[Transaction]:
    now = datetime.now(timezone.utc)
    transactions: list[Transaction] = []

    for month_offset in range(months - 1, -1, -1):
        base = (now - relativedelta(months=month_offset)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        month_key = base.strftime("%Y-%m")

        for row in _monthly_seed_rows(
            organization_id=organization_id,
            user_id=user_id,
            subscription_name=subscription_name,
            month_key=month_key,
        ):
            title = clean_description(row.description)
            internal_type = _internal_type_from_seed_type(row.type)
            category_id = await get_category_id_from_row(
                title=title,
                category=row.category,
                organization_id=organization_id,
                db=db,
                type=internal_type,
            )
            account_id = (
                checking_account_id
                if row.account_type == AccountTypeEnum.CHECKING
                else credit_card_account_id
            )
            transactions.append(
                _transaction(
                    user_id=user_id,
                    account_id=account_id,
                    category_id=category_id,
                    title=title,
                    amount=row.amount,
                    date=base.replace(day=row.day),
                    type_=internal_type,
                    description=row.description,
                    subscription_id=(
                        subscription_id
                        if row.subscription_name == subscription_name
                        else None
                    ),
                )
            )

    return transactions


def _monthly_seed_rows(
    organization_id: UUID,
    user_id: UUID,
    subscription_name: str,
    month_key: str,
) -> list[SeedTransactionRow]:
    rows: list[SeedTransactionRow] = []
    for index, template in enumerate(_monthly_seed_templates()):
        is_recurring = template.category in {"Housing", "Income", "Subscriptions"}
        seed_context = (
            organization_id,
            user_id,
            template.account_type.value,
            template.day,
            index,
        )
        if not is_recurring:
            seed_context = (*seed_context, month_key)

        if template.category == "Subscriptions":
            description = subscription_name.upper()
        else:
            fake = _faker_for(
                "transaction",
                *seed_context,
            )
            description = _fake_merchant_description(fake, template.category)

        amount = _fake_amount_cents(
            seed_parts=(
                "amount",
                *seed_context,
            ),
            min_amount=template.min_amount,
            max_amount=template.max_amount,
        )
        rows.append(
            SeedTransactionRow(
                account_type=template.account_type,
                day=template.day,
                description=description,
                category=template.category,
                type=template.type,
                amount=amount,
                subscription_name=(
                    subscription_name
                    if template.category == "Subscriptions"
                    else None
                ),
            )
        )

    return rows


def _monthly_seed_templates() -> list[SeedTransactionTemplate]:
    return [
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 1, "Housing", "DEBIT", -220000, -140000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 2, "Income", "CREDIT", 360000, 620000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 3, "Utilities", "ACH_DEBIT", -18000, -4500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 4, "Utilities", "DEBIT", -12000, -3500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 5, "Bills & Utilities", "DEBIT", -15000, -4000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 6, "Groceries", "DEBIT", -16000, -3500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 7, "Groceries", "DEBIT", -14000, -3000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 8, "Entertainment", "DEBIT", -3500, -899
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 9, "Subscriptions", "DEBIT", -2999, -699
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CHECKING, 10, "Health & Wellness", "DEBIT", -9500, -2500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 11, "Travel", "Sale", -9000, -600
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 12, "Education", "Sale", -12000, -1500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 13, "Shopping", "Sale", -18000, -500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 14, "Gas", "Sale", -9500, -2500
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 15, "Automotive", "Sale", -45000, -5000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 16, "Shopping", "Sale", -15000, -600
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 17, "Groceries", "Sale", -22000, -5000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 18, "Food & Drink", "Sale", -8500, -1200
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 19, "Travel", "Sale", -7500, -900
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 20, "Shopping", "Sale", -12000, -299
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 21, "Entertainment", "Sale", -4500, -899
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 22, "Entertainment", "Sale", -3500, -799
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 23, "Health & Wellness", "Sale", -9000, -1200
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 24, "Shopping", "Sale", -20000, -1000
        ),
        SeedTransactionTemplate(
            AccountTypeEnum.CREDIT_CARD, 25, "Home", "Sale", -18000, -2000
        ),
    ]


def _faker_for(*seed_parts) -> Faker:
    fake = Faker("en_US")
    fake.seed_instance(_stable_seed(*seed_parts))
    return fake


def _stable_seed(*parts) -> int:
    raw = "|".join(str(part) for part in parts)
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _fake_merchant_description(fake: Faker, category: str) -> str:
    merchant = fake.company().replace(",", "").replace(".", "")
    if category == "Income":
        return f"{merchant} PAYROLL".upper()
    if category == "Housing":
        return f"{merchant} RENT".upper()
    if category == "Gas":
        return f"{merchant} OIL {fake.random_number(digits=8)}".upper()
    if category == "Automotive":
        return f"{merchant} AUTO {fake.random_int(min=100, max=9999)}".upper()
    if category == "Travel":
        return f"{merchant} PARKING SERVICES".upper()
    if category == "Education":
        return f"{merchant} LEARNING".upper()
    if category == "Food & Drink":
        return f"{merchant} CAFE".upper()
    if category == "Subscriptions":
        return f"{merchant} SUBSCRIPTION".upper()
    return merchant.upper()


def _fake_amount_cents(
    seed_parts: tuple,
    min_amount: int,
    max_amount: int,
) -> int:
    fake = _faker_for(*seed_parts)
    lower = min(abs(min_amount), abs(max_amount))
    upper = max(abs(min_amount), abs(max_amount))
    amount = fake.random_int(min=lower, max=upper)
    if min_amount > 0 and max_amount > 0:
        return amount
    return -amount


def _internal_type_from_seed_type(seed_type: str) -> str:
    return {
        "ACH_CREDIT": "income",
        "CHECK_DEPOSIT": "income",
        "CREDIT": "income",
        "DEBIT": "expense",
        "ACH_DEBIT": "expense",
        "Sale": "expense",
        "Refund": "income",
        "Payment": "payment",
        "Adjustment": "adjustment",
    }.get(seed_type, "unknown")


def _transaction(
    user_id: UUID,
    account_id: UUID,
    category_id: UUID,
    title: str,
    amount: int,
    date: datetime,
    type_: str = "expense",
    subscription_id: UUID | None = None,
    description: str | None = None,
) -> Transaction:
    return Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        project_id=None,
        subscription_id=subscription_id,
        amount=amount,
        currency="USD",
        date=date,
        title=title,
        type=type_,
        description=description,
        fingerprint=generate_fingerprint(
            date=date,
            title=title,
            amount_cents=amount,
        ),
        subscription_candidate=False,
    )


async def _insert_missing_transactions(
    db: DBSession,
    transactions: list[Transaction],
) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    for transaction in transactions:
        result = await db.execute(
            select(Transaction.uuid).where(
                Transaction.account_id == transaction.account_id,
                Transaction.fingerprint == transaction.fingerprint,
            )
        )
        if result.scalar_one_or_none():
            skipped += 1
            continue

        db.add(transaction)
        inserted += 1

    await db.flush()
    return inserted, skipped
