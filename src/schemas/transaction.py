from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date, datetime
from typing import Literal

from src.model.models import AccountTypeEnum


class TransactionBase(BaseModel):
    category_id: UUID
    account_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    title: str
    amount: int
    description: Optional[str] = None
    date: Optional[datetime] = None
    currency: Optional[str] = "USD"
    type: Optional[str] = "expense"
    subscription_candidate: bool = False
    subscription_id: Optional[UUID] = None


class TransactionCreate(TransactionBase):
    account_id: UUID


class TransactionResponse(TransactionBase):
    uuid: UUID
    user_id: UUID
    category: Optional[str] = None
    account_name: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionCandidateResponse(TransactionResponse):
    frequency: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionUpdate(BaseModel):
    category_id: Optional[UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = None
    date: Optional[datetime] = None
    currency: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionsAllRequest(BaseModel):
    category_ids: list[UUID] | None = None
    category_names: list[str] | None = None
    account_ids: list[UUID] | None = None
    account_names: list[str] | None = None
    merchant_search: str | None = None
    transaction_types: list[str] | None = None

    minimum_amount_cents: int | None = Field(
        default=None,
        ge=0,
        description="Minimum transaction amount magnitude in cents.",
    )
    maximum_amount_cents: int | None = Field(
        default=None,
        ge=0,
        description="Maximum transaction amount magnitude in cents.",
    )

    account_type: Optional[AccountTypeEnum] = None

    @model_validator(mode="after")
    def validate_amount_range(self) -> "TransactionsAllRequest":
        if (
            self.minimum_amount_cents is not None
            and self.maximum_amount_cents is not None
            and self.minimum_amount_cents > self.maximum_amount_cents
        ):
            raise ValueError("minimum_amount_cents cannot exceed maximum_amount_cents")
        return self


class TransactionsAllResponse(BaseModel):
    transactions: list[TransactionResponse] = []
    has_more: bool = False
    total_pages: int = 0
    total_count: int = 0

    class Config:
        from_attributes = True


class TransactionSummaryRequest(BaseModel):
    from_date: date
    to_date: date
    account_types: list[AccountTypeEnum] = Field(
        default_factory=lambda: [
            AccountTypeEnum.CHECKING,
            AccountTypeEnum.CREDIT_CARD,
        ],
        min_length=1,
    )

    @field_validator("account_types")
    @classmethod
    def deduplicate_account_types(
        cls, value: list[AccountTypeEnum]
    ) -> list[AccountTypeEnum]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_date_range(self) -> "TransactionSummaryRequest":
        if self.from_date > self.to_date:
            raise ValueError("from_date cannot be after to_date")
        return self


class TransactionSummaryResponse(BaseModel):
    gross_expense: int
    refunds: int
    net_spending: int
    income: int
    net_activity: int
    expense_transaction_count: int
    refund_transaction_count: int
    income_transaction_count: int
    average_expense: float
    average_monthly_spending: float
    from_date: date
    to_date: date
    included_account_types: list[AccountTypeEnum]


class CashFlowHistoryRequest(BaseModel):
    from_date: date
    to_date: date
    category_ids: list[UUID] | None = None
    account_ids: list[UUID] | None = None
    project_ids: list[UUID] | None = None
    granularity: Literal["day", "week", "month"] = "month"

    @model_validator(mode="after")
    def validate_date_range(self) -> "CashFlowHistoryRequest":
        if self.from_date > self.to_date:
            raise ValueError("from_date cannot be after to_date")
        return self


class CashFlowPeriodResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    income: int
    expense: int
    refunds: int
    net: int
    transaction_count: int


class CashFlowHistoryResponse(BaseModel):
    timezone: str
    from_date: date
    to_date: date
    granularity: Literal["day", "week", "month"]
    periods: list[CashFlowPeriodResponse]


class SubscriptionCandidateCountResponse(BaseModel):
    count: int


class SubscriptionCandidateItem(BaseModel):
    merchant: str
    amount: float
    frequency: str
    transactions: int


class SubscriptionCandidatesResponse(BaseModel):
    has_subscription_candidates: bool
    candidates: list[SubscriptionCandidateItem] = []


class TransactionUpdateSubscriptionRequest(BaseModel):
    subscription_id: UUID
    transaction_name: str


class TransactionUpdateSubscriptionResponse(BaseModel):
    updated_count: int
    subscription_id: UUID
    transaction_name: str


class TransactionByNamePeriodResponse(BaseModel):
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


class TransactionByNameMetaResponse(BaseModel):
    title: str
    period: TransactionByNamePeriodResponse
    total_transactions: int


class TransactionByNameStatsResponse(BaseModel):
    total_spent: float
    average_per_month: float
    max_single_charge: float
    min_single_charge: float
    last_transaction_date: Optional[datetime] = None
    first_transaction_date: Optional[datetime] = None


class TransactionByNameYearComparisonResponse(BaseModel):
    current_year_total: float
    previous_year_total: float
    difference: float
    percentage_change: float


class TransactionsByNameResponse(BaseModel):
    meta: TransactionByNameMetaResponse
    stats: TransactionByNameStatsResponse
    year_comparison: Optional[TransactionByNameYearComparisonResponse] = None
    transactions: list[TransactionResponse] = []

    class Config:
        from_attributes = True
