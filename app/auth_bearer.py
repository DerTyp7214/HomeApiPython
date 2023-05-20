from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session


from .auth_handler import decodeJWT
from .sql_app.database import SessionLocal
from .sql_app import crud


class JWTBearer(HTTPBearer):
    __db__ = None

    def __init__(self, db: Optional[Session] = None, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)
        self.__db__ = db

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials | None = await super(JWTBearer, self).__call__(request)
        if credentials is not None:
            if not credentials.scheme == "Bearer":
                raise HTTPException(
                    status_code=403, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(
                    status_code=403, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(
                status_code=403, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        isTokenValid: bool = False

        try:
            payload = decodeJWT(jwtoken)
        except:
            payload = None
        if payload:
            email = payload.get("email")
            db = self.__db__ if self.__db__ is not None else SessionLocal()
            if email is not None and crud.get_user_by_email(db, email) is not None:
                isTokenValid = True
            if self.__db__ is None:
                db.close()
        return isTokenValid
