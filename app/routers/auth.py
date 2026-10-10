from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register" , response_model=UserRead , status_code=201)
def register(body : UserCreate , session:Session = Depends(get_session)) : 
    if body.role not in ("farmer" , "buyer") :
        raise HTTPException(400 , "Only farmer and buyer roles allowed")
    if session.exec(select(User).where(User.email == body.email)).first() :
        raise HTTPException(409 , "User Already Exist")
    user= User(name = body.name , email = body.email , role = body.role , state = body.state , hashed_password = hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form.username)).first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invlaid Credentials")
    return Token(access_token=create_access_token(user.id, user.role))

@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user