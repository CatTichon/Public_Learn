from sqlalchemy import JSON, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class TaskLog(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_profile.id"), index=True, nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id"), index=True, nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topic.id"), index=True, nullable=False
    )
    task_type: Mapped[str] = mapped_column(nullable=False)
    difficulty: Mapped[int] = mapped_column(nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    answer_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)


class TechnicalLog(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
