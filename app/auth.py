import os
from datetime import datetime, timedelta

import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# =========================================================
# JWT CONFIGURATION
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "fraud-detection-secret-key-change-this"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()


# =========================================================
# PASSWORD HASH
# =========================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    bcrypt supports a maximum of 72 bytes.
    Passwords longer than 72 bytes are safely truncated.
    """

    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


# =========================================================
# VERIFY PASSWORD
# =========================================================

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.
    """

    try:

        password_bytes = plain_password.encode("utf-8")

        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        hashed_bytes = hashed_password.encode("utf-8")

        return bcrypt.checkpw(
            password_bytes,
            hashed_bytes
        )

    except Exception as e:

        print(
            f"Password verification error: {e}"
        )

        return False


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(username: str) -> str:

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
# GET CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials
) -> str:

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
