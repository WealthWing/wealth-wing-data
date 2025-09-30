from typing import List, Optional
from src.database.connect import Base
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Enum,
    BigInteger,
    ForeignKey,
    Numeric,
    Boolean,
    Text,
    select,
)

from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column, column_property
import enum
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    users = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan"
    )


class UserRole(enum.Enum):
    """
    Enumeration of user roles within the system, sorted by importance.

    Attributes:
        SuperAdmin: Represents a user with the highest level of administrative privileges.
        Admin: Represents a user with administrative privileges.
        User_Admin: Represents a user with administrative privileges specific to user management.
        User_Manager: Represents a user with permissions to manage other users.
        User_Editor: Represents a user with permissions to edit content.
        User_Viewer: Represents a user with read-only access.
        User: Represents a standard user with basic access.
    """
    Admin = "Admin"
    User = "User"
    User_Manager = "User_Manager"
    User_Admin = "User_Admin"
    User_Viewer = "User_Viewer"
    User_Editor = "User_Editor"


class User(Base):
    __tablename__ = "user_table"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.uuid"), nullable=True
    )
    email: str = Column(String, unique=True, nullable=False, index=True)
    name: str = Column(String)
    last_name: str = Column(String)
    role: UserRole = Column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="users"
    )
    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    import_jobs = relationship(
        "ImportJob", back_populates="user", cascade="all, delete-orphan"
    )
    accounts = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship("Transaction", back_populates="user")
    projects = relationship("Project", back_populates="user")


class Subscription(Base):
    __tablename__ = "subscriptions"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False)
    category_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.uuid"), nullable=True
    )
    name = Column(String(255), nullable=False)
    amount: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    currency = Column(String(10), default="USD")
    billing_frequency = Column(String(50))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    next_billing_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    status = Column(String(50))
    payment_method = Column(String(50))
    notes = Column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    cancellation_date = Column(DateTime)
    trial_period = Column(Boolean, default=False)
    trial_end_date = Column(DateTime)
    total_amount_spent = Column(Numeric(15, 2))
    contract_length = Column(String(50))
    contract_end_date = Column(DateTime)
    usage_limits = Column(String(255))
    support_contact = Column(String(255))
    website_url = Column(String(255))

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    category: Mapped["Category"] = relationship(
        "Category", back_populates="subscriptions"
    )


class Category(Base):
    __tablename__ = "categories"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.uuid"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False) # e.g., "expense", "income", "transfer"
    slug: Mapped[str] = mapped_column(String(120), nullable=True) # URL-friendly version of the title
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    subscriptions = relationship("Subscription", back_populates="category")
    transactions = relationship("Transaction", back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.uuid", ondelete="CASCADE"),
        nullable=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.uuid"), nullable=False
    )

    account_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.uuid"), nullable=True
    )
    import_job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_jobs.uuid"), nullable=True
    )

    amount: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # e.g., "expense", "income", "transfer", "refund"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fingerprint = Column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    import_job = relationship("ImportJob", back_populates="transactions")
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    category: Mapped["Category"] = relationship(
        "Category", back_populates="transactions"
    )
    project: Mapped["Project"] = relationship("Project", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")


class Project(Base):
    __tablename__ = "projects"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False
    )
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.uuid"), nullable=True
    )
    project_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    budget: Mapped[BigInteger] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="projects")
    children: Mapped[List["Project"]] = relationship(
        "Project", cascade="all, delete-orphan"
    )
    transactions = relationship("Transaction", back_populates="project")
    total_cost = column_property(
        select(func.sum(Transaction.amount))
        .where(Transaction.project_id == uuid)
        .correlate_except(Transaction)
        .label("total_cost")
    )


class AccountTypeEnum(enum.Enum):
    CREDIT_CARD = "CREDIT_CARD"
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CASH = "CASH"
    INVESTMENT = "INVESTMENT"
    LOAN = "LOAN"
    OTHER = "OTHER"


class Account(Base):
    __tablename__ = "accounts"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[AccountTypeEnum] = mapped_column(
        Enum(AccountTypeEnum, name="account_type"), nullable=False
    )
    institution: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # e.g., "Chase", "Bank of America"
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    last_four: Mapped[str] = mapped_column(String(4), nullable=True)  # e.g., "1234"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), insert_default=utc_now, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        insert_default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    import_jobs = relationship("ImportJob", back_populates="account")


class ImportJobStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.uuid"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer)
    status: Mapped[ImportJobStatus] = mapped_column(
        Enum(ImportJobStatus, name="import_job_status"),
        nullable=False,
        default=ImportJobStatus.PENDING,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="import_jobs")
    account = relationship(
        "Account", back_populates="import_jobs", foreign_keys=[account_id]
    )
    transactions = relationship("Transaction", back_populates="import_job")
