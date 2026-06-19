"""Database models: Batch and Image."""
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    # created | processing | paused | done | error
    status = Column(String, default="created", nullable=False)
    # JSON blob of the processing configuration (see config.DEFAULT_CONFIG)
    config_json = Column(Text, nullable=False, default="{}")
    # Optional source folder when images are referenced in place (not uploaded)
    source_dir = Column(String, nullable=True)

    images = relationship(
        "Image", back_populates="batch", cascade="all, delete-orphan"
    )

    @property
    def config(self) -> dict:
        return json.loads(self.config_json or "{}")

    @config.setter
    def config(self, value: dict) -> None:
        self.config_json = json.dumps(value)

    def counts(self) -> dict:
        total = len(self.images)
        done = sum(1 for i in self.images if i.status == "done")
        pending = sum(1 for i in self.images if i.status == "pending")
        processing = sum(1 for i in self.images if i.status == "processing")
        error = sum(1 for i in self.images if i.status == "error")
        flagged = sum(1 for i in self.images if i.flagged and i.status == "done")
        approved = sum(1 for i in self.images if i.review_status == "approved")
        reverted = sum(1 for i in self.images if i.review_status == "reverted")
        return {
            "total": total, "done": done, "pending": pending,
            "processing": processing, "error": error, "flagged": flagged,
            "approved": approved, "reverted": reverted,
        }

    def to_dict(self, counts: dict | None = None) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "config": self.config,
            "source_dir": self.source_dir,
            "counts": counts if counts is not None else self.counts(),
        }


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)
    result_path = Column(String, nullable=True)
    # pending | processing | done | error
    status = Column(String, default="pending", nullable=False, index=True)
    flagged = Column(Boolean, default=False, nullable=False)
    flag_reasons = Column(Text, nullable=True)  # JSON list of strings
    # pending | approved | reverted
    review_status = Column(String, default="pending", nullable=False, index=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    batch = relationship("Batch", back_populates="images")

    @property
    def reasons(self) -> list:
        if not self.flag_reasons:
            return []
        try:
            return json.loads(self.flag_reasons)
        except (ValueError, TypeError):
            return [self.flag_reasons]

    @reasons.setter
    def reasons(self, value: list) -> None:
        self.flag_reasons = json.dumps(value or [])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "filename": self.filename,
            "status": self.status,
            "flagged": self.flagged,
            "reasons": self.reasons,
            "review_status": self.review_status,
            "error": self.error,
            "has_result": bool(self.result_path),
        }
