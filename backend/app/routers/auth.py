import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/signup", response_model=schemas.TokenOut)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(payload.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    existing = db.query(models.User).filter_by(email=email).first()
    if existing:
        raise HTTPException(409, "An account with this email already exists.")

    user = models.User(
        email=email,
        hashed_password=hash_password(payload.password),
        name=(payload.name or "").strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "user": user}


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter_by(email=email).first()
    # Deliberately identical error for "no such user" and "wrong password"
    # so login can't be used to enumerate registered email addresses.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password.")

    token = create_access_token(user.id)
    return {"access_token": token, "user": user}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
