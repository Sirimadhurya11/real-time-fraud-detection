from datetime import datetime, timedelta
from decimal import Decimal
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import User, Transaction, FraudAlert
from app.schemas import LoginRequest, TransactionCreate
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.fraud_engine import calculate_fraud_risk


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Real-Time Fraud Detection & Risk Engine",
    description="Fintech transaction fraud detection system",
    version="1.0.0"
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# CREATE DEFAULT ADMIN
# =========================================================

def create_default_admin():

    db = next(get_db())

    try:

        existing_user = (
            db.query(User)
            .filter(
                User.username == "admin"
            )
            .first()
        )

        if not existing_user:

            admin = User(
                username="admin",
                password_hash=hash_password("admin123")
            )

            db.add(admin)
            db.commit()

            print("Default admin user created.")

        else:

            print("Default admin user already exists.")

    except Exception as e:

        db.rollback()

        print(
            f"Could not create default admin user: {e}"
        )

    finally:

        db.close()


create_default_admin()


# =========================================================
# HOME
# =========================================================

@app.get("/")
def home():

    return {
        "message":
            "Fraud Detection & Risk Engine API is running"
    }


# =========================================================
# LOGIN PAGE
# =========================================================

@app.get("/login-page")
def login_page():

    login_file = os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)
        ),
        "frontend",
        "login.html"
    )

    if not os.path.exists(login_file):

        raise HTTPException(
            status_code=404,
            detail="Login file not found"
        )

    return FileResponse(login_file)


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.username == login_data.username
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    if not verify_password(
        login_data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        user.username
    )

    return {
        "message": "Login successful",
        "username": user.username,
        "authenticated": True,
        "access_token": access_token,
        "token_type": "bearer"
    }


# =========================================================
# DASHBOARD PAGE
# =========================================================

@app.get("/dashboard-page")
def dashboard_page():

    dashboard_file = os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)
        ),
        "frontend",
        "dashboard.html"
    )

    if not os.path.exists(dashboard_file):

        raise HTTPException(
            status_code=404,
            detail="Dashboard file not found"
        )

    return FileResponse(dashboard_file)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "database": "connected"
    }


# =========================================================
# CREATE / ANALYZE TRANSACTION
# =========================================================

@app.post("/transactions")
def create_transaction(

    transaction: TransactionCreate,

    current_user: str = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db)

):

    # -----------------------------------------------------
    # FIND CURRENT USER
    # -----------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.username == current_user
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail="User not found"
        )


    # -----------------------------------------------------
    # COUNT TRANSACTIONS IN LAST HOUR
    # -----------------------------------------------------

    one_hour_ago = (
        datetime.utcnow()
        - timedelta(hours=1)
    )

    transaction_count = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user.id,
            Transaction.transaction_time
            >= one_hour_ago
        )
        .count()
    )


    # -----------------------------------------------------
    # RUN FRAUD ENGINE
    # -----------------------------------------------------

    fraud_result = calculate_fraud_risk(

        amount=transaction.amount,

        location=transaction.location,

        transaction_count_last_hour=
            transaction_count
    )


    # -----------------------------------------------------
    # GENERATE TRANSACTION ID
    # -----------------------------------------------------

    transaction_id = (
        "TXN-"
        +
        datetime.utcnow().strftime(
            "%Y%m%d%H%M%S%f"
        )
    )


    # -----------------------------------------------------
    # CREATE TRANSACTION
    # -----------------------------------------------------

    new_transaction = Transaction(

        transaction_id=transaction_id,

        user_id=user.id,

        amount=transaction.amount,

        currency=transaction.currency,

        merchant=transaction.merchant,

        location=transaction.location,

        transaction_time=
            transaction.transaction_time,

        risk_score=
            fraud_result["risk_score"],

        risk_level=
            fraud_result["risk_level"],

        decision=
            fraud_result["decision"],

        is_fraud=
            fraud_result["is_fraud"]
    )

    db.add(new_transaction)


    # -----------------------------------------------------
    # CREATE FRAUD ALERT
    # -----------------------------------------------------

    if fraud_result["risk_level"] in {
        "MEDIUM",
        "HIGH"
    }:

        alert = FraudAlert(

            transaction_id=transaction_id,

            risk_score=
                fraud_result["risk_score"],

            risk_level=
                fraud_result["risk_level"],

            reason=
                "; ".join(
                    fraud_result["reasons"]
                )
        )

        db.add(alert)


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    db.commit()

    db.refresh(new_transaction)


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {

        "message":
            "Transaction analyzed successfully",

        "transaction_id":
            transaction_id,

        "risk_score":
            fraud_result["risk_score"],

        "risk_level":
            fraud_result["risk_level"],

        "decision":
            fraud_result["decision"],

        "is_fraud":
            fraud_result["is_fraud"],

        "reasons":
            fraud_result["reasons"]
    }


# =========================================================
# GET ALL TRANSACTIONS
# =========================================================

@app.get("/transactions")
def get_transactions(

    limit: int = 50,

    current_user: str = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db)

):

    if limit < 1 or limit > 100:

        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 100"
        )

    transactions = (

        db.query(Transaction)

        .order_by(
            Transaction.created_at.desc()
        )

        .limit(limit)

        .all()
    )

    return transactions


# =========================================================
# GET SINGLE TRANSACTION
# =========================================================

@app.get("/transactions/{transaction_id}")
def get_transaction(

    transaction_id: str,

    current_user: str = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db)

):

    transaction = (

        db.query(Transaction)

        .filter(
            Transaction.transaction_id
            == transaction_id
        )

        .first()
    )

    if not transaction:

        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    return transaction


# =========================================================
# FRAUD ALERTS
# =========================================================

@app.get("/fraud-alerts")
def get_fraud_alerts(

    current_user: str = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db)

):

    alerts = (

        db.query(FraudAlert)

        .order_by(
            FraudAlert.created_at.desc()
        )

        .all()
    )

    return alerts


# =========================================================
# DASHBOARD API
# =========================================================

@app.get("/dashboard")
def dashboard(

    current_user: str = Depends(
        get_current_user
    ),

    db: Session = Depends(get_db)

):

    total_transactions = (

        db.query(Transaction)
        .count()
    )


    total_alerts = (

        db.query(FraudAlert)
        .count()
    )


    high_risk = (

        db.query(Transaction)

        .filter(
            Transaction.risk_level == "HIGH"
        )

        .count()
    )


    medium_risk = (

        db.query(Transaction)

        .filter(
            Transaction.risk_level == "MEDIUM"
        )

        .count()
    )


    low_risk = (

        db.query(Transaction)

        .filter(
            Transaction.risk_level == "LOW"
        )

        .count()
    )


    blocked = (

        db.query(Transaction)

        .filter(
            Transaction.decision == "BLOCK"
        )

        .count()
    )


    review = (

        db.query(Transaction)

        .filter(
            Transaction.decision == "REVIEW"
        )

        .count()
    )


    approved = (

        db.query(Transaction)

        .filter(
            Transaction.decision == "APPROVE"
        )

        .count()
    )


    transactions = (

        db.query(Transaction)
        .all()
    )


    total_amount = sum(

        (
            transaction.amount
            for transaction in transactions
        ),

        Decimal("0")
    )


    return {

        "total_transactions":
            total_transactions,

        "total_alerts":
            total_alerts,

        "high_risk":
            high_risk,

        "medium_risk":
            medium_risk,

        "low_risk":
            low_risk,

        "blocked":
            blocked,

        "review":
            review,

        "approved":
            approved,

        "total_amount":
            total_amount
    }
