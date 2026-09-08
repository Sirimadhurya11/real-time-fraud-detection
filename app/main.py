from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from jose import JWTError, jwt

from app.database import SessionLocal, engine, Base
from app.models import User, Transaction, ReconciliationResult
from app.schemas import TransactionCreate, LoginRequest
from app.auth import hash_password, verify_password
from app.reconciliation import ( # type: ignore
    reconcile_transactions,
    check_transaction_presence
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Financial Reconciliation System",
    description="Backend system for reconciling financial transactions",
    version="1.0.0"
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# JWT CONFIGURATION
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "financial-reconciliation-secret-key-change-this"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(username: str):

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# VERIFY TOKEN
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:

            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        return username

    except JWTError:

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token"
        )


# =========================================================
# CREATE DEFAULT ADMIN USER
# =========================================================

def create_default_admin():

    db = SessionLocal()

    try:

        existing_user = (
            db.query(User)
            .filter(
                User.username == "admin"
            )
            .first()
        )

        if not existing_user:

            password_hash = hash_password("admin123")

            admin_user = User(
                username="admin",
                password_hash=password_hash
            )

            db.add(admin_user)

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
            "Financial Reconciliation System API is running"
    }


# =========================================================
# LOGIN PAGE
# =========================================================

@app.get("/login-page")
def login_page():

    login_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
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
# LOGIN API
# =========================================================

@app.post("/login")
def login(login_data: LoginRequest):

    db = SessionLocal()

    try:

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

        # FIXED:
        # Use bcrypt verification from app.auth
        # instead of the old broken get_context.verify()

        password_valid = verify_password(
            login_data.password,
            user.password_hash
        )

        if not password_valid:

            raise HTTPException(
                status_code=401,
                detail="Invalid username or password"
            )

        access_token = create_access_token(
            user.username
        )

        return {

            "message":
                "Login successful",

            "username":
                user.username,

            "authenticated":
                True,

            "access_token":
                access_token,

            "token_type":
                "bearer"
        }

    finally:

        db.close()


# =========================================================
# DASHBOARD PAGE
# =========================================================

@app.get("/dashboard-page")
def dashboard_page():

    dashboard_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
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
def health_check():

    db = SessionLocal()

    try:

        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception:

        raise HTTPException(
            status_code=503,
            detail="Database connection failed"
        )

    finally:

        db.close()


# =========================================================
# CREATE TRANSACTION
# =========================================================

@app.post("/transactions")
def create_transaction(
    transaction: TransactionCreate,
    current_user: str = Depends(get_current_user)
):

    db = SessionLocal()

    try:

        existing_transaction = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == transaction.transaction_id,

                Transaction.source
                == transaction.source
            )
            .first()
        )

        if existing_transaction:

            raise HTTPException(
                status_code=409,
                detail=(
                    "Transaction with this ID and "
                    "source already exists"
                )
            )

        new_transaction = Transaction(

            transaction_id=transaction.transaction_id,

            amount=transaction.amount,

            currency=transaction.currency,

            source=transaction.source,

            status=transaction.status,

            transaction_time=transaction.transaction_time
        )

        db.add(new_transaction)

        db.commit()

        db.refresh(new_transaction)

        return {

            "message":
                "Transaction created successfully",

            "transaction_id":
                new_transaction.transaction_id
        }

    finally:

        db.close()


# =========================================================
# GET ALL TRANSACTIONS
# =========================================================

@app.get("/transactions")
def get_transactions(

    page: int = 1,

    page_size: int = 10,

    sort: str = "newest",

    current_user: str = Depends(get_current_user)

):

    if page < 1:

        raise HTTPException(
            status_code=400,
            detail="Page must be greater than or equal to 1"
        )

    if page_size < 1 or page_size > 100:

        raise HTTPException(
            status_code=400,
            detail="Page size must be between 1 and 100"
        )

    if sort not in ["newest", "oldest"]:

        raise HTTPException(
            status_code=400,
            detail="Sort must be either 'newest' or 'oldest'"
        )

    db = SessionLocal()

    try:

        total = (
            db.query(Transaction)
            .count()
        )

        query = db.query(Transaction)

        if sort == "newest":

            query = query.order_by(
                Transaction.transaction_time.desc()
            )

        else:

            query = query.order_by(
                Transaction.transaction_time.asc()
            )

        offset = (page - 1) * page_size

        transactions = (
            query
            .offset(offset)
            .limit(page_size)
            .all()
        )

        total_pages = (
            (total + page_size - 1) // page_size
            if total > 0
            else 0
        )

        return {

            "page": page,

            "page_size": page_size,

            "sort": sort,

            "total_transactions": total,

            "total_pages": total_pages,

            "has_next_page":
                page < total_pages,

            "has_previous_page":
                page > 1,

            "transactions": transactions
        }

    finally:

        db.close()


# =========================================================
# SEARCH / FILTER TRANSACTIONS
# =========================================================

@app.get("/transactions/search")
def search_transactions(

    source: Optional[str] = None,

    status: Optional[str] = None,

    page: int = 1,

    page_size: int = 10,

    sort: str = "newest",

    current_user: str = Depends(get_current_user)

):

    if page < 1:

        raise HTTPException(
            status_code=400,
            detail="Page must be greater than or equal to 1"
        )

    if page_size < 1 or page_size > 100:

        raise HTTPException(
            status_code=400,
            detail="Page size must be between 1 and 100"
        )

    if sort not in ["newest", "oldest"]:

        raise HTTPException(
            status_code=400,
            detail="Sort must be either 'newest' or 'oldest'"
        )

    db = SessionLocal()

    try:

        query = db.query(Transaction)

        if source:

            query = query.filter(
                Transaction.source == source
            )

        if status:

            query = query.filter(
                Transaction.status == status
            )

        total = query.count()

        if sort == "newest":

            query = query.order_by(
                Transaction.transaction_time.desc()
            )

        else:

            query = query.order_by(
                Transaction.transaction_time.asc()
            )

        offset = (page - 1) * page_size

        transactions = (
            query
            .offset(offset)
            .limit(page_size)
            .all()
        )

        total_pages = (
            (total + page_size - 1) // page_size
            if total > 0
            else 0
        )

        return {

            "page": page,

            "page_size": page_size,

            "sort": sort,

            "total_transactions": total,

            "total_pages": total_pages,

            "has_next_page":
                page < total_pages,

            "has_previous_page":
                page > 1,

            "transactions": transactions
        }

    finally:

        db.close()


# =========================================================
# GET SINGLE TRANSACTION
# =========================================================

@app.get("/transactions/{transaction_id}")
def get_transaction(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

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

        return {

            "transaction_id":
                transaction.transaction_id,

            "amount":
                transaction.amount,

            "currency":
                transaction.currency,

            "source":
                transaction.source,

            "status":
                transaction.status,

            "transaction_time":
                transaction.transaction_time
        }

    finally:

        db.close()


# =========================================================
# UPDATE TRANSACTION
# =========================================================

@app.put("/transactions/{transaction_id}")
def update_transaction(

    transaction_id: str,

    transaction: TransactionCreate,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        existing_transaction = (
            db.query(Transaction)
            .filter(

                Transaction.transaction_id
                == transaction_id,

                Transaction.source
                == transaction.source

            )
            .first()
        )

        if not existing_transaction:

            raise HTTPException(
                status_code=404,
                detail="Transaction not found"
            )

        existing_transaction.amount = (
            transaction.amount
        )

        existing_transaction.currency = (
            transaction.currency
        )

        existing_transaction.status = (
            transaction.status
        )

        existing_transaction.transaction_time = (
            transaction.transaction_time
        )

        db.commit()

        db.refresh(existing_transaction)

        return {

            "message":
                "Transaction updated successfully",

            "transaction_id":
                existing_transaction.transaction_id,

            "source":
                existing_transaction.source,

            "amount":
                existing_transaction.amount,

            "currency":
                existing_transaction.currency,

            "status":
                existing_transaction.status,

            "transaction_time":
                existing_transaction.transaction_time
        }

    finally:

        db.close()


# =========================================================
# DELETE TRANSACTION
# =========================================================

@app.delete("/transactions/{transaction_id}")
def delete_transaction(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

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

        db.delete(transaction)

        db.commit()

        return {

            "message":
                "Transaction deleted successfully"
        }

    finally:

        db.close()


# =========================================================
# RECONCILE - GET
# =========================================================

@app.get("/reconcile/{transaction_id}")
def reconcile_transaction(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == transaction_id
            )
            .all()
        )

        bank_transaction = next(

            (
                t for t in transactions
                if t.source == "bank"
            ),

            None
        )

        payment_transaction = next(

            (
                t for t in transactions
                if t.source == "payment_system"
            ),

            None
        )

        if (
            not bank_transaction
            or not payment_transaction
        ):

            return {

                "transaction_id":
                    transaction_id,

                "status":
                    "PENDING",

                "message":
                    (
                        "Both bank and payment-system "
                        "transactions are required"
                    )
            }

        result = reconcile_transactions(
            bank_transaction,
            payment_transaction
        )

        reconciliation_record = ReconciliationResult(

            transaction_id=
                result["transaction_id"],

            status=
                result["status"],

            differences=(

                ",".join(
                    result["differences"]
                )

                if result["differences"]
                else None
            )
        )

        db.add(reconciliation_record)

        db.commit()

        return result

    finally:

        db.close()


# =========================================================
# RECONCILE - POST
# =========================================================

@app.post("/reconcile/{transaction_id}")
def run_reconciliation(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == transaction_id
            )
            .all()
        )

        bank_transaction = next(

            (
                t for t in transactions
                if t.source == "bank"
            ),

            None
        )

        payment_transaction = next(

            (
                t for t in transactions
                if t.source == "payment_system"
            ),

            None
        )

        if (
            not bank_transaction
            or not payment_transaction
        ):

            return {

                "transaction_id":
                    transaction_id,

                "status":
                    "PENDING",

                "message":
                    (
                        "Both bank and payment-system "
                        "transactions are required"
                    )
            }

        result = reconcile_transactions(

            bank_transaction,

            payment_transaction
        )

        reconciliation_record = ReconciliationResult(

            transaction_id=
                result["transaction_id"],

            status=
                result["status"],

            differences=(

                ",".join(
                    result["differences"]
                )

                if result["differences"]
                else None
            )
        )

        db.add(reconciliation_record)

        db.commit()

        return {

            "message":
                "Reconciliation completed",

            **result
        }

    finally:

        db.close()


# =========================================================
# CHECK PRESENCE
# =========================================================

@app.get("/check-presence/{transaction_id}")
def check_presence(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id
                == transaction_id
            )
            .all()
        )

        result = check_transaction_presence(
            transactions
        )

        return {

            "transaction_id":
                transaction_id,

            **result
        }

    finally:

        db.close()


# =========================================================
# ALL RECONCILIATION RESULTS
# =========================================================

@app.get("/reconciliation-results")
def get_reconciliation_results(

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        results = (
            db.query(ReconciliationResult)
            .order_by(
                ReconciliationResult.created_at.desc()
            )
            .all()
        )

        return results

    finally:

        db.close()


# =========================================================
# RECONCILIATION HISTORY
# =========================================================

@app.get("/reconciliation-results/{transaction_id}")
def get_reconciliation_history(

    transaction_id: str,

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        results = (
            db.query(ReconciliationResult)
            .filter(
                ReconciliationResult.transaction_id
                == transaction_id
            )
            .order_by(
                ReconciliationResult.created_at.desc()
            )
            .all()
        )

        if not results:

            raise HTTPException(
                status_code=404,
                detail="No reconciliation history found"
            )

        return results

    finally:

        db.close()


# =========================================================
# RECONCILIATION SUMMARY
# =========================================================

@app.get("/reconciliation-summary")
def get_reconciliation_summary(

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        results = (
            db.query(
                ReconciliationResult
            )
            .all()
        )

        total = len(results)

        matched = sum(
            1
            for result in results
            if result.status == "MATCHED"
        )

        mismatched = sum(
            1
            for result in results
            if result.status == "MISMATCH"
        )

        pending = sum(
            1
            for result in results
            if result.status == "PENDING"
        )

        return {

            "total_reconciliations":
                total,

            "matched":
                matched,

            "mismatched":
                mismatched,

            "pending":
                pending
        }

    finally:

        db.close()


# =========================================================
# DASHBOARD API
# =========================================================

@app.get("/dashboard")
def dashboard(

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        total_transactions = (
            db.query(Transaction)
            .count()
        )

        total_reconciliations = (
            db.query(
                ReconciliationResult
            )
            .count()
        )

        matched = (
            db.query(
                ReconciliationResult
            )
            .filter(
                ReconciliationResult.status
                == "MATCHED"
            )
            .count()
        )

        mismatched = (
            db.query(
                ReconciliationResult
            )
            .filter(
                ReconciliationResult.status
                == "MISMATCH"
            )
            .count()
        )

        pending = (
            db.query(
                ReconciliationResult
            )
            .filter(
                ReconciliationResult.status
                == "PENDING"
            )
            .count()
        )

        return {

            "total_transactions":
                total_transactions,

            "total_reconciliations":
                total_reconciliations,

            "matched":
                matched,

            "mismatched":
                mismatched,

            "pending":
                pending
        }

    finally:

        db.close()


# =========================================================
# TRANSACTION STATISTICS
# =========================================================

@app.get("/transaction-statistics")
def transaction_statistics(

    current_user: str = Depends(get_current_user)

):

    db = SessionLocal()

    try:

        transactions = (
            db.query(Transaction)
            .all()
        )

        total = len(transactions)

        bank_count = sum(
            1
            for transaction in transactions
            if transaction.source == "bank"
        )

        payment_system_count = sum(
            1
            for transaction in transactions
            if transaction.source == "payment_system"
        )

        completed_count = sum(
            1
            for transaction in transactions
            if transaction.status == "completed"
        )

        pending_count = sum(
            1
            for transaction in transactions
            if transaction.status == "pending"
        )

        failed_count = sum(
            1
            for transaction in transactions
            if transaction.status == "failed"
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
                total,

            "bank_transactions":
                bank_count,

            "payment_system_transactions":
                payment_system_count,

            "completed_transactions":
                completed_count,

            "pending_transactions":
                pending_count,

            "failed_transactions":
                failed_count,

            "total_amount":
                total_amount
        }

    finally:

        db.close()

