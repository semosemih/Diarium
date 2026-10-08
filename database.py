import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional

DB_FILE = "ayna.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Günlük Taahhütler ve Gerçekleşenler (Commitments & Reality)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        category TEXT NOT NULL, -- 'ders', 'is', 'muzik', 'spor', 'genel'
        planned_text TEXT NOT NULL,
        planned_hours REAL DEFAULT 0.0,
        actual_hours REAL DEFAULT 0.0,
        status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'partial', 'skipped'
        excuse TEXT,
        ai_critique TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Serbest Düşünce ve Not Günlüğü (Free Journal & Ideas)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        title TEXT,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'genel', -- 'ders', 'is', 'muzik', 'spor', 'genel'
        ai_reflection TEXT,
        tags TEXT, -- JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Benlik Profili ve Öğrenilen Gerçekler (User Reality Profile / Insights)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        category TEXT,
        insight_text TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Ayarlar (Ollama model, url, persona vb.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Varsayılan ayarlar
    default_settings = {
        "ollama_url": "http://localhost:11434",
        "ollama_model": "qwen2.5:7b",
        "honesty_level": "brutal", # 'brutal', 'balanced', 'gentle'
        "user_name": "Semih"
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

# --- Daily Plans CRUD & Stats ---

def add_plan(plan_date: str, category: str, planned_text: str, planned_hours: float, ai_critique: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_plans (date, category, planned_text, planned_hours, ai_critique, status)
    VALUES (?, ?, ?, ?, ?, 'pending')
    """, (plan_date, category, planned_text, planned_hours, ai_critique))
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()
    try:
        sync_to_google_drive()
    except Exception:
        pass
    return plan_id

def update_plan_actual(plan_id: int, actual_hours: float, status: str, excuse: str = ""):
    # Ertelendi / Yapılmadı veya Bekliyor durumunda gerçekleşen süre kesinlikle 0 olmalıdır.
    if status in ("skipped", "pending"):
        actual_hours = 0.0
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE daily_plans 
    SET actual_hours = ?, status = ?, excuse = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (actual_hours, status, excuse, plan_id))
    conn.commit()
    conn.close()
    try:
        sync_to_google_drive()
    except Exception:
        pass

def get_plans_by_date(target_date: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_plans WHERE date = ? ORDER BY id ASC", (target_date,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_recent_plans(days: int = 14) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM daily_plans 
    WHERE date >= date('now', '-' || ? || ' days')
    ORDER BY date DESC, id DESC
    """, (days,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def calculate_reality_stats():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Toplam taahhüt vs gerçekleşen (Sadece completed ve partial fiili süreye sayılır)
    cursor.execute("""
    SELECT 
        category,
        COUNT(*) as total_items,
        SUM(planned_hours) as total_planned,
        SUM(CASE WHEN status IN ('completed', 'partial') THEN actual_hours ELSE 0.0 END) as total_actual,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
        SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_count
    FROM daily_plans
    GROUP BY category
    """)
    category_stats = {}
    for row in cursor.fetchall():
        planned = row["total_planned"] or 0.0
        actual = row["total_actual"] or 0.0
        ratio = (actual / planned * 100.0) if planned > 0 else 0.0
        category_stats[row["category"]] = {
            "total_items": row["total_items"],
            "total_planned": round(planned, 1),
            "total_actual": round(actual, 1),
            "accuracy_percentage": round(min(ratio, 100.0), 1),
            "completed_count": row["completed_count"],
            "skipped_count": row["skipped_count"]
        }

    # Genel toplam
    cursor.execute("""
    SELECT 
        SUM(planned_hours) as total_planned,
        SUM(CASE WHEN status IN ('completed', 'partial') THEN actual_hours ELSE 0.0 END) as total_actual,
        COUNT(*) as total_plans
    FROM daily_plans
    """)
    totals = cursor.fetchone()
    total_planned = totals["total_planned"] or 0.0
    total_actual = totals["total_actual"] or 0.0
    overall_ratio = (total_actual / total_planned * 100.0) if total_planned > 0 else 100.0

    conn.close()
    return {
        "categories": category_stats,
        "total_planned": round(total_planned, 1),
        "total_actual": round(total_actual, 1),
        "reality_score": round(min(overall_ratio, 100.0), 1),
        "optimism_bias_percentage": round(max(0.0, ((total_planned - total_actual) / total_planned * 100.0)), 1) if total_planned > 0 else 0.0
    }

# --- Journal CRUD ---

def add_journal_entry(entry_date: str, title: str, content: str, category: str = "genel", ai_reflection: str = "", tags: List[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO journal_entries (date, title, content, category, ai_reflection, tags)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (entry_date, title, content, category, ai_reflection, json.dumps(tags or [])))
    conn.commit()
    entry_id = cursor.lastrowid
    conn.close()
    try:
        sync_to_google_drive()
    except Exception:
        pass
    return entry_id

def get_journal_entries(limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if category and category != "all":
        cursor.execute("SELECT * FROM journal_entries WHERE category = ? ORDER BY date DESC, id DESC LIMIT ?", (category, limit))
    else:
        cursor.execute("SELECT * FROM journal_entries ORDER BY date DESC, id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# --- Settings ---

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {r["key"]: r["value"] for r in cursor.fetchall()}
    conn.close()
    return settings

# --- Google Drive Auto-Sync & Backup ---

GOOGLE_DRIVE_DIR = "/Users/semihsengul/Library/CloudStorage/GoogleDrive-semihyahama@gmail.com/My Drive/notebook pipeline"

def sync_to_google_drive() -> Dict[str, Any]:
    """Tüm veri tabanını, markdown günlükleri ve taahhütleri Google Drive'a senkronize eder."""
    import os
    import shutil
    
    try:
        os.makedirs(GOOGLE_DRIVE_DIR, exist_ok=True)
        
        # 1. Ham SQLite dosyasını yedekle
        if os.path.exists(DB_FILE):
            shutil.copy2(DB_FILE, os.path.join(GOOGLE_DRIVE_DIR, "ayna.db"))
            
        # 2. Markdown Günlük Dosyası Oluştur (gunluk_notlar.md)
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM journal_entries ORDER BY date DESC, id DESC")
        journal_rows = [dict(r) for r in cursor.fetchall()]
        
        md_journal = "# 📓 AYNA — Düşünce ve Fikir Günlüğü\n\n"
        md_journal += f"> Son Senkronizasyon: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
        
        if not journal_rows:
            md_journal += "*Henüz bir günlük kaydı eklenmedi.*\n"
        else:
            for item in journal_rows:
                cat_emoji = {"ders": "📚", "is": "💼", "muzik": "🎵", "spor": "🏃"}.get(item["category"], "💭")
                md_journal += f"## {cat_emoji} {item['title']}\n"
                md_journal += f"**Tarih:** {item['date']} | **Kategori:** `{item['category'].upper()}`\n\n"
                md_journal += f"{item['content']}\n\n"
                if item.get("ai_reflection"):
                    md_journal += f"> 🪞 **Ayna Analizi:**\n> {item['ai_reflection']}\n\n"
                md_journal += "---\n\n"
                
        with open(os.path.join(GOOGLE_DRIVE_DIR, "gunluk_notlar.md"), "w", encoding="utf-8") as f:
            f.write(md_journal)
            
        # 3. Markdown Plan ve Taahhüt Dosyası (taahhutler_ve_planlar.md)
        cursor.execute("SELECT * FROM daily_plans ORDER BY date DESC, id ASC")
        plan_rows = [dict(r) for r in cursor.fetchall()]
        stats = calculate_reality_stats()
        
        md_plans = "# 🎯 AYNA — Taahhütler ve Gerçekleşenler (Reality Audit)\n\n"
        md_plans += f"> **Gerçeklik Doğruluk Skoru:** %{stats['reality_score']} | "
        md_plans += f"**Toplam Hedef:** {stats['total_planned']} sa | "
        md_plans += f"**Toplam Fiili:** {stats['total_actual']} sa\n\n---\n\n"
        
        # Tarihe göre grupla
        plans_by_date = {}
        for p in plan_rows:
            d = p["date"]
            if d not in plans_by_date:
                plans_by_date[d] = []
            plans_by_date[d].append(p)
            
        for d, items in plans_by_date.items():
            md_plans += f"### 📅 {d}\n\n"
            md_plans += "| Kategori | Hedef / Taahhüt | Plan (sa) | Fiili (sa) | Durum | Mazeret / Not |\n"
            md_plans += "| :--- | :--- | :---: | :---: | :---: | :--- |\n"
            for p in items:
                status_icon = {"completed": "✅ Tamamlandı", "partial": "⏳ Kısmen", "skipped": "❌ Ertelendi", "pending": "🕒 Bekliyor"}.get(p["status"], p["status"])
                actual_val = p['actual_hours'] if p['status'] in ('completed', 'partial') else 0.0
                md_plans += f"| `{p['category']}` | {p['planned_text']} | {p['planned_hours']} | {actual_val} | {status_icon} | {p['excuse'] or '-'} |\n"
            md_plans += "\n"
            
        with open(os.path.join(GOOGLE_DRIVE_DIR, "taahhutler_ve_planlar.md"), "w", encoding="utf-8") as f:
            f.write(md_plans)
            
        # 4. JSON Tam Yedek
        full_export = {
            "backup_date": datetime.now().isoformat(),
            "stats": stats,
            "plans": plan_rows,
            "journal": journal_rows
        }
        with open(os.path.join(GOOGLE_DRIVE_DIR, "ayna_backup.json"), "w", encoding="utf-8") as f:
            json.dump(full_export, f, ensure_ascii=False, indent=2)
            
        conn.close()
        return {"success": True, "path": GOOGLE_DRIVE_DIR}
    except Exception as e:
        print(f"[Ayna Sync] Google Drive senkronizasyon uyarısı: {e}")
        return {"success": False, "error": str(e)}

