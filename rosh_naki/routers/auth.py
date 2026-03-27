"""Authentication routes for Rosh Naki."""

import hashlib
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Milestone, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Default milestones for cannabis sobriety (in Hebrew)
DEFAULT_MILESTONES = [
    (1, "יום ראשון נקי 🌱", "הצעד הראשון הוא הכי חשוב"),
    (3, "3 ימים חזקים 💪", "הגוף מתחיל להתנקות"),
    (7, "שבוע שלם! 🌟", "שבוע של חופש אמיתי"),
    (14, "שבועיים של כוח ✨", "ההרגלים מתחילים להשתנות"),
    (21, "21 יום - הרגל חדש 🔥", "מחקרים מראים ש-21 יום יוצרים הרגל"),
    (30, "חודש נקי! 🏆", "חודש שלם של ראש נקי"),
    (60, "חודשיים! 🎯", "הקנאביס כבר לא בדם"),
    (90, "3 חודשים! 🌈", "רבעון של חירות"),
    (180, "חצי שנה! 🎊", "חצי שנה של חיים חדשים"),
    (365, "שנה שלמה! 👑", "שנה של חופש מוחלט"),
    (730, "שנתיים! 🌍", "אלוף/ה אמיתי/ת"),
]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(stored: str, provided: str) -> bool:
    salt, hashed = stored.split(":")
    return hashlib.sha256((salt + provided).encode()).hexdigest() == hashed


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str | None = None
    motivation: str | None = None
    sobriety_date: str | None = None
    daily_cost: float = 50.0
    daily_hours: float = 2.0


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username == req.username) | (User.email == req.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="שם משתמש או אימייל כבר קיימים")

    sobriety_date = None
    if req.sobriety_date:
        sobriety_date = datetime.fromisoformat(req.sobriety_date)

    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        display_name=req.display_name or req.username,
        motivation=req.motivation,
        sobriety_start_date=sobriety_date,
        daily_cost_saved=req.daily_cost,
        daily_hours_saved=req.daily_hours,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default milestones
    for days, name, note in DEFAULT_MILESTONES:
        milestone = Milestone(
            user_id=user.id,
            name=name,
            days_required=days,
            celebration_note=note,
        )
        db.add(milestone)
    db.commit()

    return JSONResponse(
        content={"message": "ברוכים הבאים לראש נקי! 🧠", "user_id": user.id},
        headers={"X-User-Id": str(user.id)},
    )


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(user.hashed_password, req.password):
        raise HTTPException(status_code=401, detail="שם משתמש או סיסמה שגויים")

    return {
        "message": "!התחברת בהצלחה",
        "user_id": user.id,
        "display_name": user.display_name,
    }


@router.get("/me/{user_id}")
def get_me(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "sobriety_start_date": user.sobriety_start_date.isoformat() if user.sobriety_start_date else None,
        "daily_cost_saved": user.daily_cost_saved,
        "daily_hours_saved": user.daily_hours_saved,
        "motivation": user.motivation,
        "created_at": user.created_at.isoformat(),
    }


@router.put("/me/{user_id}")
def update_me(user_id: int, req: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    if req.display_name:
        user.display_name = req.display_name
    if req.motivation:
        user.motivation = req.motivation
    if req.sobriety_date:
        user.sobriety_start_date = datetime.fromisoformat(req.sobriety_date)
    user.daily_cost_saved = req.daily_cost
    user.daily_hours_saved = req.daily_hours

    db.commit()
    return {"message": "הפרופיל עודכן בהצלחה"}
