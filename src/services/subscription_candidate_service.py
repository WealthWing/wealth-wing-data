from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from uuid import UUID
from sqlalchemy import select, update
from statistics import median
from src.database.connect import DBSession
from src.model.models import Subscription, Transaction
from dateutil.relativedelta import relativedelta


MIN_OCCURRENCES = 3
MIN_INTERVAL_DAYS = 24
MAX_INTERVAL_DAYS = 40
INTERVAL_MATCH_RATIO = 0.6
AMOUNT_STABILITY_RATIO = 0.7
MAX_AMOUNT_VARIANCE_RATIO = 0.2
LOOKBACK_DAYS = 400
EXCLUDED_TYPES = {"income", "transfer", "refund", "payment", "adjustment", "unknown"}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")
_IGNORED_TOKENS = {
    "inc",
    "llc",
    "co",
    "corp",
    "payment",
    "purchase",
    "pos",
    "debit",
    "credit",
    "visa",
    "card",
    "online",
    "store",
}
_NOISY_SUFFIX_TOKENS = {
    "com",
    "www",
    "us",
    "usa",
    "billing",
    "bill",
    "subscription",
    "subscriptions",
    "services",
    "service",
}


@dataclass(frozen=True)
class CandidateTxn:
    uuid: UUID
    date: datetime
    amount: int


@dataclass(frozen=True)
class CandidateSummary:
    merchant: str
    amount: float
    frequency: str
    transactions: int


def normalize_merchant_key(title: str) -> str:
    normalized = _NON_ALNUM_RE.sub(" ", (title or "").lower())
    tokens = [t for t in normalized.split() if t and t not in _IGNORED_TOKENS and not t.isdigit()]
    return " ".join(tokens[:4]).strip()


def canonical_merchant_key(title: str) -> str:
    key = normalize_merchant_key(title)
    if not key:
        return ""

    tokens = key.split()
    while tokens and tokens[-1] in _NOISY_SUFFIX_TOKENS:
        tokens.pop()

    return " ".join(tokens[:3]).strip()


def infer_frequency(dates: list[datetime]) -> str:
    if len(dates) < 2:
        return "unknown"
    
    ordered = sorted(dates)
    intervals = [
        (ordered[i].date() - ordered[i - 1].date()).days for i in range(1, len(ordered))
    ]
    if not intervals:
        return "unknown"

    typical_days = median(intervals)
    if typical_days <= 10:
        return "weekly"
    if typical_days <= 20:
        return "biweekly"
    if typical_days <= 45:
        return "monthly"
    if typical_days <= 120:
        return "quarterly"
    if typical_days <= 400:
        return "yearly"
    return "irregular"

def calculate_next_billing_date(current_billing_date: datetime, billing_cycle: str) -> datetime:
    """
    Calculate next billing date from the most recent billing date.
    
    Args:
        current_billing_date: The last/current billing date
        billing_cycle: One of 'weekly', 'monthly', 'quarterly', 'yearly'
    
    Returns:
        Next future billing date
    """
    today = datetime.now()
    next_date = current_billing_date
    
    # Define cycle increments
    cycle_map = {
        'weekly': relativedelta(weeks=1),
        'monthly': relativedelta(months=1),
        'quarterly': relativedelta(months=3),
        'yearly': relativedelta(years=1),
    }
    
    if billing_cycle not in cycle_map:
        raise ValueError(f"Unknown billing cycle: {billing_cycle}")
    
    increment = cycle_map[billing_cycle]
    
    # Keep adding billing cycles until we find the next future date
    while next_date <= today:
        next_date += increment
    
    return next_date


# def build_candidate_summaries(
#     candidate_rows: list[tuple[str, int, datetime]]
# ) -> list[CandidateSummary]:
#     grouped: dict[str, list[tuple[str, int, datetime]]] = defaultdict(list)
#     for title, amount, date in candidate_rows:
#         if date is None:
#             continue
#         key = canonical_merchant_key(title or "")
#         if not key:
#             continue
#         grouped[key].append((title or "", amount, date))

#     summaries: list[CandidateSummary] = []
#     for key, txns in grouped.items():
#         amounts = [abs(amount) for _, amount, _ in txns if amount is not None]
#         if not amounts:
#             continue

#         dates = [date for _, _, date in txns]
#         amount_dollars = round(median(amounts) / 100, 2)
#         merchant = (txns[0][0] or key.title()).strip()

#         summaries.append(
#             CandidateSummary(
#                 merchant=merchant,
#                 amount=amount_dollars,
#                 frequency=infer_frequency(dates),
#                 transactions=len(txns),
#             )
#         )

#     summaries.sort(key=lambda item: (-item.transactions, item.merchant.lower()))
#     return summaries


async def get_subscription_name_keys(db: DBSession, user_id: UUID) -> set[str]:
    rows = (await db.execute(
        select(Subscription.name).where(Subscription.user_id == user_id)
    )).all()

    keys: set[str] = set()
    for (name,) in rows:
        key = canonical_merchant_key(name or "")
        if key:
            keys.add(key)
    return keys


def group_looks_recurring(transactions: list[CandidateTxn]) -> bool:
    if len(transactions) < MIN_OCCURRENCES:
        return False

    ordered = sorted(transactions, key=lambda tx: tx.date)
    intervals = [
        (ordered[i].date.date() - ordered[i - 1].date.date()).days
        for i in range(1, len(ordered))
    ]
    if not intervals:
        return False

    interval_hits = sum(MIN_INTERVAL_DAYS <= days <= MAX_INTERVAL_DAYS for days in intervals)
    if (interval_hits / len(intervals)) < INTERVAL_MATCH_RATIO:
        return False

    amounts = [abs(tx.amount) for tx in ordered if tx.amount is not None]
    if not amounts:
        return False

    baseline = median(amounts)
    if baseline <= 0:
        return False

    stable_count = sum(
        abs(amount - baseline) / baseline <= MAX_AMOUNT_VARIANCE_RATIO
        for amount in amounts
    )
    return (stable_count / len(amounts)) >= AMOUNT_STABILITY_RATIO

async def transaction_is_subscription_candidate(
    db: DBSession,
    user_id: UUID,
    title: str,
    amount: int,
    date: datetime,
    extra_transactions: list[Transaction] | None = None
) -> bool:
    cutoff = date - timedelta(days=400)
    min_amount = int(abs(amount) * 0.8)
    max_amount = int(abs(amount) * 1.2)

    rows = (await db.execute(
        select(Transaction.date)
        .where(
            Transaction.user_id == user_id,
            Transaction.title == title,
            Transaction.date >= cutoff,
            Transaction.amount.between(min_amount, max_amount),
        )
    )).all()

    # include the new transaction
    dates = [tx_date for (tx_date,) in rows]
   
    if extra_transactions:
        for tx in extra_transactions:
            if (
                tx.title == title
                and abs(tx.amount - amount) <= abs(amount) * 0.2
            ):
                dates.append(tx.date)

    dates.append(date)
    # need at least 3 to form a pattern
    if len(dates) < 3:
        return False

    ordered = sorted(dates)

    # check monthly-ish spacing
    intervals = [
        (ordered[i].date() - ordered[i - 1].date()).days
        for i in range(1, len(ordered))
    ]

    monthly_hits = sum(24 <= days <= 40 for days in intervals)
    if monthly_hits / len(intervals) < 0.6:
        return False

    # check day-of-month consistency (±3 days)
    doms = [d.day for d in ordered]
    center = int(median(doms))

    dom_hits = sum(abs(d - center) <= 3 for d in doms)
    if dom_hits / len(doms) < 0.7:
        return False

    return True


async def mark_subscription_candidates(
    db: DBSession,
    user_id: UUID,
    account_id: UUID | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    subscription_name_keys = await get_subscription_name_keys(db=db, user_id=user_id)

    stmt = select(
        Transaction.uuid,
        Transaction.title,
        Transaction.amount,
        Transaction.date,
        Transaction.type,
    ).where(
        Transaction.user_id == user_id,
        Transaction.date >= cutoff,
    )
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)

    rows = (await db.execute(stmt)).all()

    grouped: dict[str, list[CandidateTxn]] = defaultdict(list)
    for tx_uuid, title, amount, date, tx_type in rows:
        if (tx_type or "").lower() in EXCLUDED_TYPES:
            continue
        if date is None:
            continue
        key = canonical_merchant_key(title or "")
        if not key:
            continue
        if key in subscription_name_keys:
            continue
        grouped[key].append(CandidateTxn(uuid=tx_uuid, date=date, amount=amount))

    candidate_ids = {
        tx.uuid
        for txns in grouped.values()
        if group_looks_recurring(txns)
        for tx in txns
    }

    scope_filters = [
        Transaction.user_id == user_id,
        Transaction.date >= cutoff,
    ]
    if account_id is not None:
        scope_filters.append(Transaction.account_id == account_id)

    await db.execute(
        update(Transaction)
        .where(*scope_filters)
        .values(subscription_candidate=False)
    )

    if candidate_ids:
        await db.execute(
            update(Transaction)
            .where(Transaction.uuid.in_(candidate_ids))
            .values(subscription_candidate=True)
        )

    return len(candidate_ids)
