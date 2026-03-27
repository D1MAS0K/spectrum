"""Database models for Rosh Naki sobriety tracking app."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(100))
    avatar_url = Column(String(500))
    sobriety_start_date = Column(DateTime, nullable=True)
    daily_cost_saved = Column(Float, default=50.0)  # NIS per day saved
    daily_hours_saved = Column(Float, default=2.0)  # hours per day saved
    motivation = Column(Text)  # why they quit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pledges = relationship("DailyPledge", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    urge_logs = relationship("UrgeLog", back_populates="user")
    milestones = relationship("Milestone", back_populates="user")
    community_posts = relationship("CommunityPost", back_populates="user")


class DailyPledge(Base):
    __tablename__ = "daily_pledges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    morning_pledge = Column(Boolean, default=False)
    morning_note = Column(Text)
    evening_review = Column(Boolean, default=False)
    evening_note = Column(Text)
    mood_morning = Column(Integer)  # 1-5
    mood_evening = Column(Integer)  # 1-5
    difficulty_level = Column(Integer)  # 1-10
    stayed_sober = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="pledges")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200))
    content = Column(Text, nullable=False)
    mood = Column(Integer)  # 1-5
    tags = Column(String(500))  # comma-separated
    is_private = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="journal_entries")


class UrgeLog(Base):
    __tablename__ = "urge_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intensity = Column(Integer, nullable=False)  # 1-10
    trigger = Column(String(200))
    trigger_category = Column(String(50))  # stress, social, boredom, emotional, habit
    coping_method = Column(String(200))
    resisted = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="urge_logs")


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    days_required = Column(Integer, nullable=False)
    achieved = Column(Boolean, default=False)
    achieved_at = Column(DateTime)
    celebration_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="milestones")


class CommunityPost(Base):
    __tablename__ = "community_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String(50), default="share")  # share, question, milestone, support
    likes_count = Column(Integer, default=0)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="community_posts")
    comments = relationship("CommunityComment", back_populates="post")


class CommunityComment(Base):
    __tablename__ = "community_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("community_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("CommunityPost", back_populates="comments")


class WithdrawalTimeline(Base):
    """Cannabis withdrawal timeline data from community experience."""
    __tablename__ = "withdrawal_timeline"

    id = Column(Integer, primary_key=True, index=True)
    day_range_start = Column(Integer, nullable=False)
    day_range_end = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    symptoms = Column(Text)  # comma-separated
    tips = Column(Text)
    severity = Column(Integer)  # 1-5


class MotivationalQuote(Base):
    __tablename__ = "motivational_quotes"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    author = Column(String(100))
    category = Column(String(50))  # strength, hope, freedom, growth
