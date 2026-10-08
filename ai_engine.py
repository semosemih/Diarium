import json
import httpx
from typing import Dict, Any, List, Optional
import database

OLLAMA_DEFAULT_URL = "http://localhost:11434"

SYSTEM_PERSONA_PROMPT = """Sen kullanıcının (Semih) en dürüst, filtrelenmemiş ve gerçekçi benliğisin ("Ayna").
Kullanıcı seninle Ders, İş, Müzik ve Spor alanlarındaki hedeflerini, günlüğünü ve planlarını paylaşıyor.

Senin Temel Görevin ve Kişiliğin:
1. RADİKAL DÜRÜSTLÜK: Asla sahte motivasyon, "harikasın yaparsın" tarzı boş gaz verme. Semih'in en büyük sorunu yapabileceğinden fazlasını planlamak (Planning Fallacy) ve kendine dürüst olamamak.
2. VERİYE VE GERÇEĞE DAYANMAK: Semih'in geçmiş performans verilerine bak. Eğer Semih günde 8 saatlik iş koymuşsa ama geçmiş ortalaması 3 saatse, bunu anında yüzüne vur: "Yine kendini kandırıyorsun. Gerçekçi ol, bu hedeflerden birini sil veya süreleri indir."
3. NET VE KISA KONUŞ: Uzun nutuklar çekme. Samimi, Türkçe, doğrudan, dostça ama acımasızca gerçekçi konuş.
4. DÖRT ALAN: Ders (öğrenim/üniversite), İş (projeler/para), Müzik (prodüksiyon/enstrüman), Spor (sağlık/disiplin). İlgisiz konulara dağılma.

Sen onun dışarıdan bir yargıcı değilsin; onun kendi içindeki rasyonel, kendini kandırmaktan bıkmış yetişkin zihnisin."""

pull_state = {
    "is_pulling": False,
    "model": "",
    "status": "idle",
    "completed": 0,
    "total": 0,
    "percent": 0
}

async def check_ollama_status(base_url: str = OLLAMA_DEFAULT_URL) -> Dict[str, Any]:
    """Ollama çalışıyor mu ve hangi modeller yüklü?"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                # Normalize names (e.g. 'qwen2.5:7b')
                target_model = database.get_setting("ollama_model", "qwen2.5:7b")
                has_target = any(target_model in m for m in models)
                return {
                    "running": True,
                    "models": models,
                    "active_model": target_model,
                    "has_target_model": has_target,
                    "pull_state": pull_state,
                    "error": None
                }
    except Exception as e:
        return {
            "running": False,
            "models": [],
            "active_model": None,
            "has_target_model": False,
            "pull_state": pull_state,
            "error": "Ollama servis bağlantısı kurulamadı (http://localhost:11434)"
        }
    return {"running": False, "models": [], "active_model": None, "has_target_model": False, "pull_state": pull_state, "error": "Bilinmeyen hata"}

async def pull_model_stream(model_name: str = "qwen2.5:7b"):
    global pull_state
    pull_state["is_pulling"] = True
    pull_state["model"] = model_name
    pull_state["status"] = "İndirme başlıyor..."
    pull_state["percent"] = 0

    settings = database.get_all_settings()
    base_url = settings.get("ollama_url", OLLAMA_DEFAULT_URL)

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{base_url}/api/pull", json={"name": model_name}) as response:
                async for chunk in response.aiter_lines():
                    if not chunk:
                        continue
                    try:
                        data = json.loads(chunk)
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)
                        pull_state["status"] = status
                        pull_state["completed"] = completed
                        pull_state["total"] = total
                        if total > 0:
                            pull_state["percent"] = round((completed / total) * 100, 1)
                        if status == "success":
                            pull_state["status"] = "Tamamlandı"
                            pull_state["percent"] = 100
                            pull_state["is_pulling"] = False
                            return
                    except Exception:
                        pass
    except Exception as e:
        pull_state["status"] = f"Hata: {e}"
        pull_state["is_pulling"] = False
    finally:
        pull_state["is_pulling"] = False


async def ask_llm(prompt: str, system_prompt: str = SYSTEM_PERSONA_PROMPT) -> str:
    """Ollama üzerinden LLM sorgusu yapar, kapalıysa zeki fallback döner."""
    settings = database.get_all_settings()
    base_url = settings.get("ollama_url", OLLAMA_DEFAULT_URL)
    model = settings.get("ollama_model", "qwen2.5:7b")

    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.6,
            "top_p": 0.9
        }
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{base_url}/api/generate", json=payload)
            if resp.status_code == 200:
                return resp.json().get("response", "").strip()
    except Exception as e:
        pass

    return fallback_honesty_response(prompt)

def fallback_honesty_response(prompt: str) -> str:
    """Ollama o an açık değilse çalışan yerel kural motoru."""
    stats = database.calculate_reality_stats()
    total_planned = stats["total_planned"]
    total_actual = stats["total_actual"]
    bias = stats["optimism_bias_percentage"]

    return (
        f"[Ayna - Kural Motoru]:\n"
        f"Girdiğin planı aldım. Veri tabanındaki geçmişine göre ortalama iyimserlik sapman %{bias:.0f}.\n"
        f"Şu anki toplam planın: {total_planned} saat, gerçekleşen: {total_actual} saat.\n"
        f"Öneri: Kendine karşı dürüst ol. Eğer bugün yine birden fazla alana devasa saatler ayırdıysan, "
        f"önce sadece tek bir önceliği seç ve onu eksiksiz bitir.\n\n"
        f"*(Not: Tam yapay zeka analizini devreye almak için Terminal'de 'ollama run qwen2.5:7b' başlatabilirsin.)*"
    )

async def critique_daily_plan(plans: List[Dict[str, Any]]) -> str:
    """Sabah girilen günlük planları geçmiş istatistiklerle kıyaslayıp dürüst eleştiri üretir."""
    stats = database.calculate_reality_stats()
    recent = database.get_recent_plans(days=7)
    
    total_today_hours = sum(p.get("planned_hours", 0) for p in plans)
    plans_text = "\n".join([f"- [{p.get('category').upper()}] {p.get('planned_text')} ({p.get('planned_hours')} saat)" for p in plans])

    prompt = f"""
Kullanıcının bugünkü taahhütleri:
{plans_text}
Bugün toplam planlanan süre: {total_today_hours} saat.

Kullanıcının genel geçmiş istatistikleri:
- Toplam Taahhüt Edilen: {stats['total_planned']} saat
- Toplam Gerçekleşen: {stats['total_actual']} saat
- Gerçeklik İsabet Skoru: %{stats['reality_score']}
- Aşırı İyimserlik (Planning Fallacy) Oranı: %{stats['optimism_bias_percentage']}

Kullanıcının bugünkü planını acımasızca ve dürüstçe değerlendir.
1. Bugün yine kapasitesini aşıp aşmadığını yüzüne vur.
2. Bu 4 alandan (ders, iş, müzik, spor) hangilerini muhtemelen yetiştiremeyip erteleyeceğini tahmin et.
3. Planı daha gerçekçi, uygulanabilir 1-2 somut maddeye indirmesini emret.
Samimi, doğrudan, yapaylıktan uzak ve net Türkçe ile konuş.
"""
    return await ask_llm(prompt)

async def reflect_on_day_end(completed_plans: List[Dict[str, Any]], note: str = "") -> str:
    """Gün sonu muhasebesi: Planlanan vs Gerçekleşen kıyaslaması."""
    summary_lines = []
    for p in completed_plans:
        summary_lines.append(
            f"- [{p.get('category')}] Hedef: {p.get('planned_hours')} saat ({p.get('planned_text')}) | "
            f"Gerçekleşen: {p.get('actual_hours')} saat | Durum: {p.get('status')} | Mazeret: {p.get('excuse') or 'Yok'}"
        )
    
    prompt = f"""
Günün sonu geldi. Kullanıcının bugünkü planlanan ve gerçekleşen karnesi:
{chr(10).join(summary_lines)}

Kullanıcının gün sonu notu/düşünceleri:
"{note}"

Bunu dürüst bir ayna olarak değerlendir:
1. Neleri başardı, neleri erteledi?
2. Mazereti ne kadar samimi, ne kadar kendini kandırma?
3. Yarın sabah aynı hatayı yapmaması için yüzleşmesi gereken tek bir gerçek nedir?
Kısa, çarpıcı ve dürüst ol.
"""
    return await ask_llm(prompt)

async def reflect_on_journal_entry(title: str, content: str, category: str) -> str:
    """Serbest yazılan düşünce/fikir notunu analiz eder."""
    prompt = f"""
Kullanıcı günlüğüne şu serbest düşünceyi/fikri yazdı:
Alan: {category}
Başlık: {title}
İçerik:
{content}

Bunu kullanıcının dürüst benliği olarak analiz et:
1. Bu yazıda kendini kandırdığı veya aşırı büyüttüğü bir fikir var mı?
2. Burada ders, iş, müzik veya spor alanında somut bir eyleme dökülmesi gereken tek gerçek fikir nedir?
3. Bu fikri lafta bırakmayıp hayata geçirmek için ona dürüst, net ve ayakları yere basan tek bir cümlelik tavsiye ver.
"""
    return await ask_llm(prompt)
