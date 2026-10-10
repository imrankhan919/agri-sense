import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from app.database import get_session
from app.models import User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")



def get_current_user(
 token: str = Depends(oauth2_scheme),
 session: Session = Depends(get_session),
) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(401, "Token galat ya expire ho gaya", headers={"WWW-Authenticate": "Bearer"})
    user = session.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "User nahi mila")
    return user


def require_role(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"This endpoint is only for {', '.join(roles)}")
        return user
    return checker