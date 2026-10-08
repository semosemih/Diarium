from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import database
import ai_engine

app = FastAPI(title="Ayna - Dürüst Kişisel Gerçeklik & Not Sistemi")

# Initialize database tables
database.init_db()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def get_index():
    return FileResponse("static/index.html")

# --- Pydantic Models ---

class PlanCreate(BaseModel):
    category: str # 'ders', 'is', 'muzik', 'spor', 'genel'
    planned_text: str
    planned_hours: float
    date_str: Optional[str] = None

class PlanBatchCreate(BaseModel):
    plans: List[PlanCreate]
    date_str: Optional[str] = None

class PlanUpdate(BaseModel):
    actual_hours: float
    status: str # 'completed', 'partial', 'skipped'
    excuse: Optional[str] = ""

class DayEndReview(BaseModel):
    date_str: Optional[str] = None
    note: Optional[str] = ""

class JournalCreate(BaseModel):
    title: str
    content: str
    category: str = "genel"
    tags: Optional[List[str]] = []

class SettingsUpdate(BaseModel):
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    honesty_level: Optional[str] = None
    user_name: Optional[str] = None

# --- Endpoints ---

@app.get("/api/status")
async def get_status():
    ollama_info = await ai_engine.check_ollama_status()
    current_settings = database.get_all_settings()
    return {
        "today": str(date.today()),
        "ollama": ollama_info,
        "settings": current_settings
    }

@app.post("/api/ollama/pull")
async def pull_model_endpoint():
    import asyncio
    settings = database.get_all_settings()
    model = settings.get("ollama_model", "qwen2.5:7b")
    if not ai_engine.pull_state.get("is_pulling"):
        asyncio.create_task(ai_engine.pull_model_stream(model))
    return {"success": True, "status": ai_engine.pull_state}

@app.get("/api/ollama/pull-status")
def pull_model_status():
    return ai_engine.pull_state

@app.get("/api/stats")
def get_stats():
    return database.calculate_reality_stats()

@app.get("/api/plans")
def get_plans(target_date: Optional[str] = None):
    d = target_date or str(date.today())
    plans = database.get_plans_by_date(d)
    return {"date": d, "plans": plans}

@app.post("/api/plans")
def create_plan(plan: PlanCreate):
    d = plan.date_str or str(date.today())
    plan_id = database.add_plan(
        plan_date=d,
        category=plan.category,
        planned_text=plan.planned_text,
        planned_hours=plan.planned_hours
    )
    return {"success": True, "id": plan_id}

@app.post("/api/plans/batch")
def create_batch_plans(batch: PlanBatchCreate):
    d = batch.date_str or str(date.today())
    created_ids = []
    for p in batch.plans:
        pid = database.add_plan(
            plan_date=d,
            category=p.category,
            planned_text=p.planned_text,
            planned_hours=p.planned_hours
        )
        created_ids.append(pid)
    return {"success": True, "ids": created_ids}

@app.post("/api/plans/critique")
async def critique_plans(target_date: Optional[str] = None):
    d = target_date or str(date.today())
    plans = database.get_plans_by_date(d)
    if not plans:
        return {"critique": "Henüz bugüne ait bir plan girmedin. Önce taahhütlerini yaz, sonra yüzleşelim."}
    critique = await ai_engine.critique_daily_plan(plans)
    return {"critique": critique}

@app.put("/api/plans/{plan_id}")
def update_plan(plan_id: int, update: PlanUpdate):
    database.update_plan_actual(
        plan_id=plan_id,
        actual_hours=update.actual_hours,
        status=update.status,
        excuse=update.excuse or ""
    )
    return {"success": True}

@app.post("/api/plans/day-end")
async def day_end_review(review: DayEndReview):
    d = review.date_str or str(date.today())
    plans = database.get_plans_by_date(d)
    reflection = await ai_engine.reflect_on_day_end(plans, review.note or "")
    return {"reflection": reflection}

@app.get("/api/journal")
def get_journal(category: Optional[str] = None):
    entries = database.get_journal_entries(limit=50, category=category)
    return {"entries": entries}

@app.post("/api/journal")
async def create_journal(entry: JournalCreate):
    today_str = str(date.today())
    # Generate reflection
    reflection = await ai_engine.reflect_on_journal_entry(
        title=entry.title,
        content=entry.content,
        category=entry.category
    )
    entry_id = database.add_journal_entry(
        entry_date=today_str,
        title=entry.title,
        content=entry.content,
        category=entry.category,
        ai_reflection=reflection,
        tags=entry.tags or []
    )
    return {
        "success": True,
        "id": entry_id,
        "reflection": reflection
    }

@app.post("/api/settings")
def update_settings(settings: SettingsUpdate):
    if settings.ollama_url is not None:
        database.set_setting("ollama_url", settings.ollama_url)
    if settings.ollama_model is not None:
        database.set_setting("ollama_model", settings.ollama_model)
    if settings.honesty_level is not None:
        database.set_setting("honesty_level", settings.honesty_level)
    if settings.user_name is not None:
        database.set_setting("user_name", settings.user_name)
    return {"success": True, "settings": database.get_all_settings()}
