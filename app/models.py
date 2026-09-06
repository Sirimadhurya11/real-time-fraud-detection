from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Boolean
)
from sqlalchemy.sql import func

from app.database import Base


# =========================================================
# USER
# =========================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


# =========================================================
# TRANSACTION
# =========================================================

class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    transaction_id = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=True,
        index=True
    )

    amount = Column(
        Numeric(12, 2),
        nullable=False
    )

    currency = Column(
        String(3),
        nullable=False
    )

    merchant = Column(
        String(200),
        nullable=False
    )

    location = Column(
        String(200),
        nullable=False
    )

    transaction_time = Column(
        DateTime,
        nullable=False
    )

    risk_score = Column(
        Integer,
        default=0,
        nullable=False
    )

    risk_level = Column(
        String(20),
        default="LOW",
        nullable=False
    )

    decision = Column(
        String(20),
        default="APPROVE",
        nullable=False
    )

    is_fraud = Column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


# =========================================================
# FRAUD ALERT
# =========================================================

class FraudAlert(Base):

    __tablename__ = "fraud_alerts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    transaction_id = Column(
        String(100),
        nullable=False,
        index=True
    )

    risk_score = Column(
        Integer,
        nullable=False
    )

    risk_level = Column(
        String(20),
        nullable=False
    )

    reason = Column(
        String(500),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )