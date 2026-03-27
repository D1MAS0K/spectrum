"""Sobriety tracking routes for Rosh Naki."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Milestone, User

router = APIRouter(prefix="/api/tracker", tags=["tracker"])


@router.get("/stats/{user_id}")
def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    if not user.sobriety_start_date:
        return {
            "sober_days": 0,
            "sober_hours": 0,
            "sober_minutes": 0,
            "money_saved": 0,
            "hours_saved": 0,
            "sobriety_start_date": None,
            "motivation": user.motivation,
        }

    now = datetime.utcnow()
    delta = now - user.sobriety_start_date
    total_seconds = int(delta.total_seconds())
    days = delta.days
    hours = total_seconds // 3600
    minutes = total_seconds // 60

    money_saved = round(days * user.daily_cost_saved, 2)
    hours_saved = round(days * user.daily_hours_saved, 1)

    # Check and update milestones
    milestones = db.query(Milestone).filter(
        Milestone.user_id == user_id,
        Milestone.achieved == False,
    ).all()

    newly_achieved = []
    for m in milestones:
        if days >= m.days_required:
            m.achieved = True
            m.achieved_at = now
            newly_achieved.append({"name": m.name, "days": m.days_required})

    if newly_achieved:
        db.commit()

    return {
        "sober_days": days,
        "sober_hours": hours,
        "sober_minutes": minutes,
        "sober_seconds": total_seconds,
        "money_saved": money_saved,
        "hours_saved": hours_saved,
        "sobriety_start_date": user.sobriety_start_date.isoformat(),
        "motivation": user.motivation,
        "newly_achieved_milestones": newly_achieved,
    }


@router.get("/milestones/{user_id}")
def get_milestones(user_id: int, db: Session = Depends(get_db)):
    milestones = db.query(Milestone).filter(
        Milestone.user_id == user_id
    ).order_by(Milestone.days_required).all()

    user = db.query(User).filter(User.id == user_id).first()
    current_days = 0
    if user and user.sobriety_start_date:
        current_days = (datetime.utcnow() - user.sobriety_start_date).days

    result = []
    for m in milestones:
        progress = min(100, round((current_days / m.days_required) * 100, 1)) if m.days_required > 0 else 100
        result.append({
            "id": m.id,
            "name": m.name,
            "days_required": m.days_required,
            "achieved": m.achieved,
            "achieved_at": m.achieved_at.isoformat() if m.achieved_at else None,
            "celebration_note": m.celebration_note,
            "progress": progress,
        })

    return {"milestones": result, "current_days": current_days}


class ResetRequest(BaseModel):
    new_date: str | None = None


@router.post("/reset/{user_id}")
def reset_sobriety(user_id: int, req: ResetRequest, db: Session = Depends(get_db)):
    """Reset sobriety date (relapse handling - non-judgmental)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="משתמש לא נמצא")

    if req.new_date:
        user.sobriety_start_date = datetime.fromisoformat(req.new_date)
    else:
        user.sobriety_start_date = datetime.utcnow()

    # Reset milestones
    milestones = db.query(Milestone).filter(Milestone.user_id == user_id).all()
    for m in milestones:
        m.achieved = False
        m.achieved_at = None

    db.commit()
    return {
        "message": "הכי חשוב שחזרת. כל יום הוא התחלה חדשה. 💜",
        "new_start_date": user.sobriety_start_date.isoformat(),
    }


# Cannabis withdrawal timeline data
WITHDRAWAL_TIMELINE = [
    {
        "day_range": "ימים 1-3",
        "title": "ההתחלה 🌱",
        "description": "הגוף מתחיל לזהות שאין קנאביס. עשויה להיות עצבנות, קושי בשינה, ירידה בתיאבון.",
        "symptoms": ["עצבנות", "נדודי שינה", "ירידה בתיאבון", "הזעה"],
        "tips": ["שתו הרבה מים", "עשו פעילות גופנית קלה", "הימנעו מקפאין בערב"],
        "severity": 3,
    },
    {
        "day_range": "ימים 4-7",
        "title": "השיא של הגמילה 🔥",
        "description": "התקופה הכי קשה. הדחפים חזקים אבל כל שעה שעוברת מקרבת אתכם לחופש.",
        "symptoms": ["דחפים חזקים", "שינויים במצב הרוח", "חלומות חיים", "כאבי ראש"],
        "tips": ["דברו עם מישהו", "צאו להליכה", "כתבו ביומן", "נשמו עמוק"],
        "severity": 5,
    },
    {
        "day_range": "ימים 8-14",
        "title": "הגוף מתחיל להתאושש 💪",
        "description": "הדחפים הפיזיים מתמתנים. השינה מתחילה להשתפר. החלומות חוזרים.",
        "symptoms": ["חלומות חיים מאוד", "שיפור בתיאבון", "עייפות", "מצב רוח משתנה"],
        "tips": ["שמרו על שגרת שינה", "תזונה מאוזנת", "ספורט קבוע"],
        "severity": 3,
    },
    {
        "day_range": "ימים 15-30",
        "title": "בדרך לחופש 🌟",
        "description": "הריכוז משתפר. אנרגיה חוזרת. הזיכרון מתחדד. הגוף מתנקה.",
        "symptoms": ["שיפור בריכוז", "אנרגיה חוזרת", "מצב רוח יציב יותר"],
        "tips": ["התחילו תחביב חדש", "חזקו קשרים חברתיים", "חגגו את ההישגים"],
        "severity": 2,
    },
    {
        "day_range": "ימים 30-60",
        "title": "התנקות מלאה 🧠",
        "description": "ה-THC יוצא מרקמת השומן. המוח מתאושש. הבהירות המנטלית חוזרת.",
        "symptoms": ["בהירות מנטלית", "שינה טובה יותר", "מוטיבציה גוברת"],
        "tips": ["הציבו יעדים חדשים", "עזרו לאחרים בקהילה", "תעדו את השינוי"],
        "severity": 1,
    },
    {
        "day_range": "60+ ימים",
        "title": "ראש נקי! ✨",
        "description": "הגוף נקי לחלוטין. ההרגלים החדשים מושרשים. אתם חופשיים.",
        "symptoms": ["ביטחון עצמי", "שקט נפשי", "חשיבה צלולה", "שמחת חיים"],
        "tips": ["המשיכו בשגרה הבריאה", "היו מודל לחיקוי", "זכרו מאיפה התחלתם"],
        "severity": 0,
    },
]


@router.get("/withdrawal-timeline")
def get_withdrawal_timeline():
    return {"timeline": WITHDRAWAL_TIMELINE}
