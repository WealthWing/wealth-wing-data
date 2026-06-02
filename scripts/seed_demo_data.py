from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database.connect import sessionmanager
from src.services.seed_data import seed_demo_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed WealthWing demo data for an existing organization and user."
    )
    parser.add_argument(
        "--organization-id",
        type=UUID,
        required=True,
        help="Existing organization UUID to seed data into.",
    )
    parser.add_argument(
        "--user-id",
        type=UUID,
        required=True,
        help="Existing user UUID. The user must belong to --organization-id.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Number of months of recurring transactions to seed.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    try:
        async with sessionmanager.session() as db:
            summary = await seed_demo_data(
                db=db,
                organization_id=args.organization_id,
                user_id=args.user_id,
                months=args.months,
            )
    finally:
        await sessionmanager.close()

    print("Seed completed")
    print(f"  organization_id: {summary.organization_id}")
    print(f"  user_id: {summary.user_id}")
    print(f"  checking_account_id: {summary.checking_account_id}")
    print(f"  credit_card_account_id: {summary.credit_card_account_id}")
    print("  created:")
    for key, value in summary.created.items():
        print(f"    {key}: {value}")
    print(f"  skipped_transactions: {summary.skipped_transactions}")


if __name__ == "__main__":
    asyncio.run(main())
