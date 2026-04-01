from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
import enum
import datetime
from database import Base

class RoleEnum(str, enum.Enum):
    customer = "customer"
    admin = "admin"

class VerificationStatusEnum(str, enum.Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspended = "suspended"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=RoleEnum.customer.value)
    verification_status = Column(String, default=VerificationStatusEnum.unverified.value)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    # KYC Storage Fields
    kyc_front_doc = Column(String)
    kyc_back_doc = Column(String)
    kyc_selfie = Column(String)
    kyc_selfie_left = Column(String)
    kyc_selfie_right = Column(String)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    accounts = relationship("Account", back_populates="owner")
    loans = relationship("Loan", back_populates="owner")
    notifications = relationship("Notification", back_populates="owner")

class AccountTypeEnum(str, enum.Enum):
    checking = "checking"
    savings = "savings"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True)
    balance = Column(Float, default=0.0)
    account_type = Column(String, default=AccountTypeEnum.checking.value)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="accounts")
    transactions_from = relationship("Transaction", foreign_keys='Transaction.from_account_id', back_populates="from_account")
    transactions_to = relationship("Transaction", foreign_keys='Transaction.to_account_id', back_populates="to_account")

class TransactionTypeEnum(str, enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"
    transfer = "transfer"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    from_account = relationship("Account", foreign_keys=[from_account_id], back_populates="transactions_from")
    to_account = relationship("Account", foreign_keys=[to_account_id], back_populates="transactions_to")

class LoanStatusEnum(str, enum.Enum):
    active = "active"
    paid = "paid"
    defaulted = "defaulted"

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    balance_remaining = Column(Float, nullable=False)
    interest_rate = Column(Float, default=5.5)  # annual %
    term_months = Column(Integer, default=12)
    monthly_payment = Column(Float, nullable=False)
    status = Column(String, default=LoanStatusEnum.active.value)
    purpose = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="loans")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String, nullable=False)
    category = Column(String, default="info")  # info, alert, success
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="notifications")
