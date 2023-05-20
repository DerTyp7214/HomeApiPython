import time
import jwt
import bcrypt
from typing import Dict

from .consts import JWT_SECRET, JWT_ALGORITHM

TOKEN_VERSION = "1.0.0"


def token_response(token):
    return {
        "access_token": token,
        "token_type": "bearer",
    }


def signJWT(email: str) -> Dict[str, str]:
    payload = {
        "email": email,
        "expires": time.time() + (60 * 60 * 24 * 7),
        "version": TOKEN_VERSION,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token_response(token)


def decodeJWT(token: str) -> dict | None:
    try:
        decoded_token = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token if decoded_token["expires"] >= time.time() else None
    except:
        return None


def check_for_latest_token_version(token: str) -> bool:
    try:
        decoded_token = decodeJWT(token)
        if decoded_token is None:
            return False
        return decoded_token["version"] == TOKEN_VERSION
    except:
        return False


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())
