import math

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, date
import json

from models import (ShiftRequest, ShiftResult, WorkerResult,
                    WorkerRecord, WorkerRecordUpdate)
from database import (init_db, save_shift, get_all_shifts, get_shift_by_id,
                      delete_shift, get_all_workers, add_worker,
                      update_worker, delete_worker, get_worker_data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Bartender Tip Splitter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def hours_between(start: str, end: str) -> float:
    s = datetime.strptime(start, "%H:%M")
    e = datetime.strptime(end, "%H:%M")
    diff = (e - s).total_seconds()
    if diff < 0:
        diff += 86400
    return round(diff / 3600, 4)


# ── Workers ───────────────────────────────────────────────────────────────────

@app.get("/workers", response_model=list[WorkerRecord])
def list_workers():
    return [WorkerRecord(**w) for w in get_all_workers()]


@app.post("/workers", response_model=WorkerRecord)
def create_worker(worker: WorkerRecordUpdate):
    worker_id = add_worker(worker.name, worker.supplement, worker.min_hourly)
    return WorkerRecord(id=worker_id, name=worker.name,
                        supplement=worker.supplement, min_hourly=worker.min_hourly)


@app.put("/workers/{worker_id}", response_model=WorkerRecord)
def edit_worker(worker_id: int, worker: WorkerRecordUpdate):
    if not update_worker(worker_id, worker.name, worker.supplement, worker.min_hourly):
        raise HTTPException(status_code=404, detail="עובד לא נמצא")
    return WorkerRecord(id=worker_id, name=worker.name,
                        supplement=worker.supplement, min_hourly=worker.min_hourly)


@app.delete("/workers/{worker_id}")
def remove_worker(worker_id: int):
    if not delete_worker(worker_id):
        raise HTTPException(status_code=404, detail="עובד לא נמצא")
    return {"detail": "עובד נמחק"}


# ── Shifts ────────────────────────────────────────────────────────────────────

@app.post("/calculate", response_model=ShiftResult)
def calculate_shift(req: ShiftRequest):
    if req.total_amount <= 0:
        raise HTTPException(status_code=400, detail="סכום חייב להיות חיובי")
    if not req.workers:
        raise HTTPException(status_code=400, detail="נדרש לפחות עובד אחד")

    worker_results = []
    for w in req.workers:
        hours = hours_between(w.start_time, w.end_time)
        data = get_worker_data(w.name)
        base_supplement = data["supplement"]
        min_hourly = data["min_hourly"]

        worker_results.append({
            "name": w.name,
            "start_time": w.start_time,
            "end_time": w.end_time,
            "hours_worked": hours,
            "tip_amount": 0.0,
            "tip_per_hour": 0.0,
            "base_supplement": base_supplement,
            "min_hourly": min_hourly,
            "hourly_gap": 0.0,
            "supplement": 0.0,
            "total": 0.0,
        })

    total_hours = sum(r["hours_worked"] for r in worker_results)
    if total_hours == 0:
        raise HTTPException(status_code=400, detail="סך השעות לא יכול להיות אפס")

    hourly_rate = req.total_amount / total_hours

    for r in worker_results:
        tip = r["hours_worked"] * hourly_rate
        tip_per_hour = hourly_rate
        hourly_gap = max(0, r["min_hourly"] - math.floor(tip_per_hour))
        final_supplement = math.ceil(r["base_supplement"] + hourly_gap * r["hours_worked"])

        r["tip_amount"] = tip
        r["tip_per_hour"] = tip_per_hour
        r["hourly_gap"] = hourly_gap
        r["supplement"] = final_supplement
        r["total"] = tip + final_supplement


    today = date.today().isoformat()
    shift_id = save_shift(
        date=today,
        total_amount=req.total_amount,
        total_hours=total_hours,
        hourly_rate=hourly_rate,
        workers=worker_results,
    )

    return ShiftResult(
        id=shift_id,
        date=today,
        total_amount=req.total_amount,
        total_hours=total_hours,
        hourly_rate=hourly_rate,
        workers=[WorkerResult(**r) for r in worker_results],
    )


@app.get("/shifts", response_model=list[ShiftResult])
def list_shifts():
    rows = get_all_shifts()
    results = []
    for row in rows:
        workers = [WorkerResult(**w) for w in json.loads(row["workers_json"])]
        results.append(ShiftResult(
            id=row["id"],
            date=row["date"],
            total_amount=row["total_amount"],
            total_hours=row["total_hours"],
            hourly_rate=row["hourly_rate"],
            workers=workers,
        ))
    return results


@app.get("/shifts/{shift_id}", response_model=ShiftResult)
def get_shift(shift_id: int):
    row = get_shift_by_id(shift_id)
    if not row:
        raise HTTPException(status_code=404, detail="משמרת לא נמצאה")
    workers = [WorkerResult(**w) for w in json.loads(row["workers_json"])]
    return ShiftResult(
        id=row["id"],
        date=row["date"],
        total_amount=row["total_amount"],
        total_hours=row["total_hours"],
        hourly_rate=row["hourly_rate"],
        workers=workers,
    )


@app.delete("/shifts/{shift_id}")
def remove_shift(shift_id: int):
    if not delete_shift(shift_id):
        raise HTTPException(status_code=404, detail="משמרת לא נמצאה")
    return {"detail": "משמרת נמחקה"}


@app.get("/health")
def health():
    return {"status": "ok"}
