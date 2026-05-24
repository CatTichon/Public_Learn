from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UpdatedAtMixin


class MasteryProfile(UpdatedAtMixin, Base):
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_mastery_user_topic"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id"), index=True, nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topic.id"), index=True, nullable=False
    )
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_difficulty: Mapped[int] = mapped_column(default=1, nullable=False)
    attempts_count: Mapped[int] = mapped_column(default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    average_answer_time: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    last_answer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user = relationship("UserProfile", back_populates="mastery_profiles")
    topic = relationship("Topic")
