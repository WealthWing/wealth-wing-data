from src.database.connect import Base
from sqlalchemy import  Column, DateTime, Integer, String, Enum, Float, ForeignKey, Numeric, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import datetime
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
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    updated_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC), onupdate=datetime.datetime.now(datetime.UTC))
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
    
    