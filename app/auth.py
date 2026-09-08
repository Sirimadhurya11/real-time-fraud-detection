import os
from datetime import datetime, timedelta

import bcrypt
from jose import jwt, JWTError

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)


# =========================================================
# JWT CONFIGURATION
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "fraud-detection-secret-key-change-this"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# HTTP BEARER AUTHENTICATION
# =========================================================

security = HTTPBearer(
    auto_error=True
)


# =========================================================
# PASSWORD HASH
# =========================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    bcrypt supports a maximum of 72 bytes.
    Passwords longer than 72 bytes are truncated.
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

def create_access_token(
    username: str
) -> str:
    """
    Create a JWT access token for the logged-in user.
    """

    expire = (
        datetime.utcnow()
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": username,
        "exp": expire
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    )
) -> str:
    """
    Extract and validate the JWT token from:

    Authorization: Bearer <token>

    Returns the username stored in the token.
    """

    if not credentials:

        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    token = credentials.credentials

    if not token:

        raise HTTPException(
            status_code=401,
            detail="Authentication token missing"
        )

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

    except Exception as e:

        print(
            f"Authentication error: {e}"
        )

        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )

