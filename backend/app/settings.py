"""Runtime-configurable alert thresholds (in-memory)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Settings(BaseModel):
    cpu_threshold: float = Field(90.0, ge=1, le=100)
    ram_threshold: float = Field(90.0, ge=1, le=100)
    disk_threshold: float = Field(95.0, ge=1, le=100)

    def thresholds(self) -> dict[str, float]:
        return {"cpu": self.cpu_threshold, "ram": self.ram_threshold, "disk": self.disk_threshold}


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
