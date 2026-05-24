from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Task(TimestampMixin, Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topic.id"), index=True, nullable=False
    )
    task_type: Mapped[str] = mapped_column(index=True, nullable=False)
    difficulty: Mapped[int] = mapped_column(index=True, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(nullable=False)
    options: Mapped[list[str] | None] = mapped_column(JSON)
    starter_code: Mapped[str | None] = mapped_column(Text)
    test_cases: Mapped[dict | None] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source: Mapped[str] = mapped_column(default="seed", nullable=False)
    topic = relationship("Topic", back_populates="tasks")
