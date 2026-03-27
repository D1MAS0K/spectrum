"""Daily pledge and journal routes for Rosh Naki."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DailyPledge, JournalEntry, UrgeLog, User

router = APIRouter(prefix="/api/pledges", tags=["pledges"])


class PledgeRequest(BaseModel):
    morning_note: str | None = None
    mood: int | None = None


class EveningReviewRequest(BaseModel):
    evening_note: str | None = None
    mood: int | None = None
    difficulty_level: int | None = None
    stayed_sober: bool = True


class JournalRequest(BaseModel):
    title: str | None = None
    content: str
    mood: int | None = None
    tags: str | None = None
    is_private: bool = True


class UrgeRequest(BaseModel):
    intensity: int
    trigger: str | None = None
    trigger_category: str | None = None
    coping_method: str | None = None
    resisted: bool = True
    notes: str | None = None


@router.post("/morning/{user_id}")
def morning_pledge(user_id: int, req: PledgeRequest, db: Session = Depends(get_db)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    existing = db.query(DailyPledge).filter(
        DailyPledge.user_id == user_id,
        DailyPledge.date >= today,
    ).first()

    if existing and existing.morning_pledge:
        return {"message": "כבר נתת התחייבות בוקר היום! 💪", "already_pledged": True}

    if existing:
        existing.morning_pledge = True
        existing.morning_note = req.morning_note
        existing.mood_morning = req.mood
    else:
        pledge = DailyPledge(
            user_id=user_id,
            date=today,
            morning_pledge=True,
            morning_note=req.morning_note,
            mood_morning=req.mood,
        )
        db.add(pledge)

    db.commit()
    return {"message": "התחייבות בוקר נרשמה! היום הולך להיות יום נקי 🌅"}


@router.post("/evening/{user_id}")
def evening_review(user_id: int, req: EveningReviewRequest, db: Session = Depends(get_db)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    pledge = db.query(DailyPledge).filter(
        DailyPledge.user_id == user_id,
        DailyPledge.date >= today,
    ).first()

    if not pledge:
        pledge = DailyPledge(
            user_id=user_id,
            date=today,
        )
        db.add(pledge)

    pledge.evening_review = True
    pledge.evening_note = req.evening_note
    pledge.mood_evening = req.mood
    pledge.difficulty_level = req.difficulty_level
    pledge.stayed_sober = req.stayed_sober

    db.commit()

    if req.stayed_sober:
        return {"message": "עוד יום נקי! אתה גיבור/ה 🌙⭐"}
    else:
        return {"message": "זה בסדר. הכי חשוב שאתה פה. מחר יום חדש 💜"}


@router.get("/history/{user_id}")
def get_pledge_history(user_id: int, days: int = 30, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    pledges = db.query(DailyPledge).filter(
        DailyPledge.user_id == user_id,
        DailyPledge.date >= since,
    ).order_by(DailyPledge.date.desc()).all()

    return {
        "pledges": [
            {
                "date": p.date.isoformat(),
                "morning_pledge": p.morning_pledge,
                "morning_note": p.morning_note,
                "evening_review": p.evening_review,
                "evening_note": p.evening_note,
                "mood_morning": p.mood_morning,
                "mood_evening": p.mood_evening,
                "difficulty_level": p.difficulty_level,
                "stayed_sober": p.stayed_sober,
            }
            for p in pledges
        ],
        "streak": _calculate_streak(pledges),
    }


def _calculate_streak(pledges: list[DailyPledge]) -> int:
    streak = 0
    for p in pledges:
        if p.stayed_sober:
            streak += 1
        else:
            break
    return streak


# --- Journal ---

@router.post("/journal/{user_id}")
def create_journal_entry(user_id: int, req: JournalRequest, db: Session = Depends(get_db)):
    entry = JournalEntry(
        user_id=user_id,
        title=req.title,
        content=req.content,
        mood=req.mood,
        tags=req.tags,
        is_private=req.is_private,
    )
    db.add(entry)
    db.commit()
    return {"message": "הרשומה נשמרה ביומן 📝", "id": entry.id}


@router.get("/journal/{user_id}")
def get_journal(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    entries = db.query(JournalEntry).filter(
        JournalEntry.user_id == user_id,
    ).order_by(JournalEntry.created_at.desc()).limit(limit).all()

    return {
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content,
                "mood": e.mood,
                "tags": e.tags,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ]
    }


# --- Urge Tracking ---

@router.post("/urge/{user_id}")
def log_urge(user_id: int, req: UrgeRequest, db: Session = Depends(get_db)):
    urge = UrgeLog(
        user_id=user_id,
        intensity=req.intensity,
        trigger=req.trigger,
        trigger_category=req.trigger_category,
        coping_method=req.coping_method,
        resisted=req.resisted,
        notes=req.notes,
    )
    db.add(urge)
    db.commit()

    messages = {
        True: "גברת על הדחף! כל פעם שאת/ה מתגבר/ת, את/ה נהיה חזק/ה יותר 💪",
        False: "זה בסדר. מודעות היא הצעד הראשון. את/ה בדרך הנכונה 💜",
    }
    return {"message": messages[req.resisted], "id": urge.id}


@router.get("/urge-stats/{user_id}")
def get_urge_stats(user_id: int, days: int = 30, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    urges = db.query(UrgeLog).filter(
        UrgeLog.user_id == user_id,
        UrgeLog.created_at >= since,
    ).all()

    total = len(urges)
    resisted = sum(1 for u in urges if u.resisted)
    avg_intensity = round(sum(u.intensity for u in urges) / total, 1) if total > 0 else 0

    # Count trigger categories
    triggers = {}
    for u in urges:
        if u.trigger_category:
            triggers[u.trigger_category] = triggers.get(u.trigger_category, 0) + 1

    return {
        "total_urges": total,
        "resisted": resisted,
        "resistance_rate": round(resisted / total * 100, 1) if total > 0 else 100,
        "avg_intensity": avg_intensity,
        "trigger_breakdown": triggers,
    }
