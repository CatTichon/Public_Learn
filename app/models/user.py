from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UpdatedAtMixin


class UserProfile(UpdatedAtMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    level: Mapped[int] = mapped_column(default=1, nullable=False)
    xp: Mapped[int] = mapped_column(default=0, nullable=False)
    current_streak: Mapped[int] = mapped_column(default=0, nullable=False)
    max_streak: Mapped[int] = mapped_column(default=0, nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topic.id"))
    selected_topic = relationship("Topic")
    mastery_profiles = relationship("MasteryProfile", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user")
    quests = relationship("UserQuest", back_populates="user")
