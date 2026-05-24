from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class GamificationLog(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(index=True, nullable=False)
    xp_delta: Mapped[int] = mapped_column(default=0, nullable=False)
    old_level: Mapped[int] = mapped_column(default=1, nullable=False)
    new_level: Mapped[int] = mapped_column(default=1, nullable=False)
    reason: Mapped[str] = mapped_column(default="", nullable=False)


class Achievement(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    condition_type: Mapped[str] = mapped_column(nullable=False)
    condition_value: Mapped[int] = mapped_column(nullable=False)
    xp_reward: Mapped[int] = mapped_column(default=0, nullable=False)


class UserAchievement(Base):
    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id"), index=True, nullable=False
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievement.id"), index=True, nullable=False
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    user = relationship("UserProfile", back_populates="achievements")
    achievement = relationship("Achievement")
