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
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column, column_property
import enum
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(enum.Enum):
    Admin = "Admin"
    User = "User"
    User_Manager = "User_Manager"
    User_Admin = "User_Admin"
    User_Viewer = "User_Viewer"
    User_Editor = "User_Editor"


class User(Base):
    __tablename__ = "user_table"

    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email: str = Column(String, unique=True, nullable=False, index=True)
    name: str = Column(String)
    last_name: str = Column(String)
    role: UserRole = Column(Enum(UserRole, name="user_role"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    subscriptions = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    expenses = relationship("Expense", back_populates="user")
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
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
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


class CategoryTypeEnum(enum.Enum):
    INCOME = "INCOME"
    SUBSCRIPTIONS_AND_MEMBERSHIPS = "SUBSCRIPTIONS_AND_MEMBERSHIPS"
    VARIABLE_EXPENSES = "VARIABLE_EXPENSES"
    SAVINGS_AND_INVESTMENTS = "SAVINGS_AND_INVESTMENTS"
    DEBT_PAYMENTS = "DEBT_PAYMENTS"
    FIXED_EXPENSES = "FIXED_EXPENSES"
    DISCRETIONARY_EXPENSES = "DISCRETIONARY_EXPENSES"
    MISCELLANEOUS = "MISCELLANEOUS"


class Category(Base):
    __tablename__ = "categories"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[CategoryTypeEnum] = mapped_column(
        PgEnum(CategoryTypeEnum, name="category_type", create_type=False),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    subscriptions = relationship("Subscription", back_populates="category")
    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    __tablename__ = "expenses"

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user_table.uuid"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.uuid", ondelete="CASCADE"), nullable=True
    )
    category_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.uuid"), nullable=False
    )
    """ Deprecated: scope_id not in use"""
    scope_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    amount: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="expenses")
    category: Mapped["Category"] = relationship("Category", back_populates="expenses")
    project: Mapped["Project"] = relationship("Category", back_populates="expenses")





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
    
    total_cost = column_property(
        select(func.sum(Expense.amount))
        .where(Expense.project_id == uuid)
        .correlate_except(Expense)
        .label("total_cost")
    )
   

    


