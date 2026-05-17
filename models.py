from pydantic import BaseModel
from typing import List, Optional


# ── Pink table (permanent workers) ───────────────────────────────────────────

class WorkerRecord(BaseModel):
    id: Optional[int] = None
    name: str
    supplement: float          # השלמה — fixed bonus per shift
    min_hourly: float          # שכר מינימום — minimum hourly rate


class WorkerRecordUpdate(BaseModel):
    name: str
    supplement: float
    min_hourly: float


# ── Shift input ───────────────────────────────────────────────────────────────

class Worker(BaseModel):
    name: str
    start_time: str            # "HH:MM"
    end_time: str              # "HH:MM"


class ShiftRequest(BaseModel):
    total_amount: float
    workers: List[Worker]


# ── Shift results ─────────────────────────────────────────────────────────────

class WorkerResult(BaseModel):
    name: str
    start_time: str
    end_time: str
    hours_worked: float
    tip_amount: float          # כסף מהטיפים
    tip_per_hour: float        # טיפ לשעה של העובד
    base_supplement: float     # השלמה בסיסית
    min_hourly: float          # שכר מינימום
    hourly_gap: float          # פער שעתי (מינימום - טיפ לשעה, אם חיובי)
    supplement: float          # השלמה סופית (בסיסית + פיצוי מינימום)
    total: float               # סה"כ


class ShiftResult(BaseModel):
    id: Optional[int] = None
    date: str
    total_amount: float
    total_hours: float
    hourly_rate: float         # טיפ לשעה כללי
    workers: List[WorkerResult]
