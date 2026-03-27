"""Community routes for Rosh Naki."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CommunityComment, CommunityPost, User

router = APIRouter(prefix="/api/community", tags=["community"])


class PostRequest(BaseModel):
    content: str
    post_type: str = "share"
    is_anonymous: bool = False


class CommentRequest(BaseModel):
    content: str
    is_anonymous: bool = False


@router.get("/feed")
def get_feed(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    posts = db.query(CommunityPost).order_by(
        CommunityPost.created_at.desc()
    ).offset(offset).limit(limit).all()

    result = []
    for post in posts:
        user = db.query(User).filter(User.id == post.user_id).first()
        display_name = "אנונימי/ת" if post.is_anonymous else (user.display_name if user else "משתמש/ת")

        # Calculate sober days for the post author
        sober_days = 0
        if user and user.sobriety_start_date:
            sober_days = (datetime.utcnow() - user.sobriety_start_date).days

        comments = db.query(CommunityComment).filter(
            CommunityComment.post_id == post.id
        ).order_by(CommunityComment.created_at.asc()).all()

        comment_list = []
        for c in comments:
            c_user = db.query(User).filter(User.id == c.user_id).first()
            c_name = "אנונימי/ת" if c.is_anonymous else (c_user.display_name if c_user else "משתמש/ת")
            comment_list.append({
                "id": c.id,
                "content": c.content,
                "display_name": c_name,
                "created_at": c.created_at.isoformat(),
            })

        result.append({
            "id": post.id,
            "content": post.content,
            "post_type": post.post_type,
            "display_name": display_name,
            "sober_days": sober_days,
            "likes_count": post.likes_count,
            "comments": comment_list,
            "comments_count": len(comment_list),
            "created_at": post.created_at.isoformat(),
        })

    return {"posts": result, "page": page}


@router.post("/post/{user_id}")
def create_post(user_id: int, req: PostRequest, db: Session = Depends(get_db)):
    post = CommunityPost(
        user_id=user_id,
        content=req.content,
        post_type=req.post_type,
        is_anonymous=req.is_anonymous,
    )
    db.add(post)
    db.commit()
    return {"message": "הפוסט פורסם! 📣", "id": post.id}


@router.post("/comment/{post_id}/{user_id}")
def create_comment(post_id: int, user_id: int, req: CommentRequest, db: Session = Depends(get_db)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="פוסט לא נמצא")

    comment = CommunityComment(
        post_id=post_id,
        user_id=user_id,
        content=req.content,
        is_anonymous=req.is_anonymous,
    )
    db.add(comment)
    db.commit()
    return {"message": "התגובה נוספה! 💬", "id": comment.id}


@router.post("/like/{post_id}")
def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="פוסט לא נמצא")

    post.likes_count += 1
    db.commit()
    return {"likes_count": post.likes_count}


# Hebrew motivational quotes for cannabis sobriety
MOTIVATIONAL_QUOTES = [
    {"text": "החופש האמיתי מתחיל כשאתה מפסיק לברוח מעצמך", "author": "ניב איפרגן", "category": "freedom"},
    {"text": "כל יום נקי הוא ניצחון. כל ניצחון בונה את האדם החדש שאתה", "author": "ראש נקי", "category": "strength"},
    {"text": "אתה לא מוותר על משהו. אתה מקבל בחזרה את החיים שלך", "author": "ראש נקי", "category": "freedom"},
    {"text": "הקנאביס לא פתר שום בעיה. הוא רק דחה אותן", "author": "ראש נקי", "category": "truth"},
    {"text": "ראש נקי = חיים מלאים. בלי פילטרים, בלי ערפל", "author": "ניב איפרגן", "category": "clarity"},
    {"text": "הכוח לשנות נמצא בתוכך. תמיד היה שם", "author": "ראש נקי", "category": "strength"},
    {"text": "לא נולדנו עם ג'וינט ביד. אפשר לחיות בלעדיו", "author": "ראש נקי", "category": "truth"},
    {"text": "כל פעם שאתה אומר 'לא' לדחף, אתה אומר 'כן' לעצמך", "author": "ראש נקי", "category": "strength"},
    {"text": "היום הכי קשה הוא היום שבו אתה הכי גדל", "author": "ראש נקי", "category": "growth"},
    {"text": "אתה לא לבד במסע הזה. כולנו פה בשבילך", "author": "קהילת ראש נקי", "category": "community"},
    {"text": "השינוי לא קורה ביום אחד, אבל יום אחד הוא כל מה שצריך כדי להתחיל", "author": "ראש נקי", "category": "hope"},
    {"text": "מי שיש לו 'למה' חזק מספיק, יכול לסבול כמעט כל 'איך'", "author": "ויקטור פרנקל", "category": "strength"},
    {"text": "הבחירה שלך היום קובעת את המציאות שלך מחר", "author": "ראש נקי", "category": "growth"},
    {"text": "אתה חזק יותר מכל דחף. תזכור את זה", "author": "ניב איפרגן", "category": "strength"},
    {"text": "הערפל מתפזר. הראש מתבהר. החיים חוזרים", "author": "ראש נקי", "category": "clarity"},
    {"text": "כל גיבור היה פעם אדם רגיל שהחליט לא לוותר", "author": "ראש נקי", "category": "hope"},
    {"text": "ההתמכרות משקרת לך שאתה צריך אותה. האמת היא שהיא צריכה אותך", "author": "ראש נקי", "category": "truth"},
    {"text": "תן לעצמך את ההזדמנות לגלות מי אתה באמת בלי העשן", "author": "ניב איפרגן", "category": "freedom"},
    {"text": "הצעד הראשון הוא תמיד הכי קשה, אבל בלעדיו אין מסע", "author": "ראש נקי", "category": "hope"},
    {"text": "אתה לא נכשלת. אתה לומד. כל ניסיון מקרב אותך לחופש", "author": "ראש נקי", "category": "growth"},
]


@router.get("/quote")
def get_daily_quote():
    import random
    quote = random.choice(MOTIVATIONAL_QUOTES)
    return quote


@router.get("/quotes")
def get_all_quotes(category: str | None = None):
    if category:
        filtered = [q for q in MOTIVATIONAL_QUOTES if q["category"] == category]
        return {"quotes": filtered}
    return {"quotes": MOTIVATIONAL_QUOTES}
