from typing import Optional
from src.database.connect import Base
from sqlalchemy import  Column, DateTime, Integer, String, Enum, Float, ForeignKey, Numeric, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID

class UserRole(enum.Enum):
    Admin = "Admin"
    User = "User"
    User_Manager = "User_Manager"
    User_Admin = "User_Admin"
    User_Viewer = "User_Viewer"
    User_Editor = "User_Editor"


class User(Base):
    __tablename__ = 'user_table'
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email: str = Column(String, unique=True, nullable=False, index=True)
    name: str = Column(String)
    last_name: str = Column(String)
    role: UserRole = Column(Enum(UserRole, name='user_role'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    subscriptions = relationship('Subscription', back_populates='user')
    

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user_table.uuid'), nullable=False)
    name = Column(String(255), nullable=False)
    cost = Column(Numeric(10, 2))
    currency = Column(String(10), default='USD')
    billing_frequency = Column(String(50))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    next_billing_date = Column(DateTime)
    auto_renew = Column(Boolean, default=True)
    status = Column(String(50))
    payment_method = Column(String(50))
    notes = Column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False
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
    
    user = relationship("User", back_populates="subscriptions")
        

class TestTable(Base):
    __tablename__ = 'test_table'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole, name='userrole'), nullable=False)
    
    
class CategoryTypeEnum(Enum):
    SUBSCRIPTIONS = 'Subscriptions and Memberships' # recurring expenses that may be monthly or annual
    VARIABLE_EXPENSES = 'Variable Expenses' #expenses that fluctuate month to month
    SAVINGS_INVESTMENTS = 'Savings and Investments'
    DEBT_PAYEMENTS = 'Debt Payments'
    FIXED_EXPENSES = 'Fixed Expenses' #expenses that remain the same month to month
    DISCRETIONARY_EXPENSES = 'Discretionary Expenses' #expenses that are not necessary for survival   
    MISC = 'Miscellaneous' #expenses that do not fit into any other category 
        
class Categories(Base):
    __tablename__ = 'categories'

    uuid: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped['CategoryTypeEnum'] = mapped_column(
        Enum('CategoryTypeEnum', name='category_type'),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False
    )

    def __repr__(self):
        return f"<Categories(uuid={self.uuid}, name='{self.name}', type='{self.type}')>" 
    
#class Expenses(Base):
#    __tablename__ = 'expenses'
#    
#    uuid: Mapped[UUID] = mapped_column(
#        UUID(as_uuid=True),
#        primary_key=True,
#        default=uuid.uuid4,
#        index=True
#    )
#    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('user_table.uuid'), nullable=False)
#    #category_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('categories.uuid'), nullable=False)
#    subscription_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('subscriptions.uuid'), nullable=False)
#    amount: Mapped[Numeric] = mapped_column(Numeric(10, 2), nullable=False)
#    currency: Mapped[str] = mapped_column(String(10), default='USD')
#    date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
#    created_at: Mapped[datetime] = mapped_column(
#        DateTime(timezone=True),
#        default=datetime.now(timezone.utc),
#        nullable=False
#    )
#    updated_at: Mapped[datetime] = mapped_column(
#        DateTime(timezone=True),
#        default=datetime.now(timezone.utc),
#        onupdate=datetime.now(timezone.utc),
#        nullable=False
#    )
#    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#    
#    subscription = relationship('Subscription', back_populates='user')
    
    
  
          
    
    