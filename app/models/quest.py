from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, UpdatedAtMixin


class Quest(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    quest_type: Mapped[str] = mapped_column(index=True, nullable=False)
    target_value: Mapped[int] = mapped_column(nullable=False)
    xp_reward: Mapped[int] = mapped_column(default=0, nullable=False)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topic.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    topic = relationship("Topic")


class UserQuest(UpdatedAtMixin, Base):
    __table_args__ = (UniqueConstraint("user_id", "quest_id", name="uq_user_quest"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id"), index=True, nullable=False
    )
    quest_id: Mapped[int] = mapped_column(
        ForeignKey("quest.id"), index=True, nullable=False
    )
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user = relationship("UserProfile", back_populates="quests")
    quest = relationship("Quest")
