# 🪞 AYNA — Radikal Dürüstlük & Kişisel Gerçeklik Sistemi

> *"Kendini kandırmayı bırak, gerçeği inşa et."*

Ayna; **Ders, İş, Müzik ve Spor** alanlarında aşırı iyimser hedefler koyup (Planning Fallacy) kendini takip etmekte zorlanan zihinler için tasarlanmış, **%100 yerel ve gizli** bir kişisel ayna uygulamasıdır.

---

## 🚀 Nasıl Başlatılır?

Uygulamayı 3 farklı şekilde tek tıkla çalıştırabilirsin:

1. **Spotlight veya Raycast Üzerinden (En Kolay Yol):**
   - `Cmd + Space` bas.
   - `Ayna` yaz ve `Enter`'a bas.
2. **Masaüstünden:**
   - Masaüstündeki **`Ayna.app`** simgesine çift tıkla.
3. **Terminalden:**
   ```bash
   cd "/Users/semihsengul/Desktop/notebook pipeline"
   ./run.sh
   ```

---

## 🧠 Yerel Yapay Zeka (Ollama) Entegrasyonu

Ayna, Mac'inin donanımını (Metal & Neural Engine) kullanarak yerelde **Qwen 2.5 7B** (veya tercihen Llama 3.1 8B) çalıştırır.

Eğer henüz Mac'inde Ollama kurulu değilse:
```bash
# 1. Ollama'yı yükle
brew install ollama

# 2. Modeli başlat (Arka planda sessizce hazır durur)
ollama run qwen2.5:7b
```

> **Not:** Ollama henüz açık olmasa bile Ayna asla çökmez; dahili **Kural ve İstatistik Motoru** ile taahhütlerini ve geçmiş sapmalarını yine de hesaplar.

---

## 🎯 Temel Özellikler

- **🌅 Günün Taahhütleri (Morning Commitments):** Sabah planlarını gir.
- **⚡ Ayna Kontrolü (Mirror Check):** Yapay zeka, geçmiş tamamlama oranlarına bakarak aşırı iyimser planları ("Bugün 8 saat çalışacağım" gibi) yüzüne vurur ve hedefleri küçültmeni emreder.
- **🌙 Gün Sonu Muhasebesi (Evening Reality Check):** Gerçekte ne kadar süre harcadığını ve mazeretlerini kaydet. Mazeretlerin sıklığı hafızada tutulur.
- **📓 Fikir & Düşünce Günlüğü:** Serbest müzik fikirlerini, stratejilerini yaz; Ayna bunları somut eylemlere dönüştürsün.
- **📊 Gerçeklik Analitiği:** 4 alandaki (Ders, İş, Müzik, Spor) taahhüt vs gerçekleşen doğruluk oranlarını grafiklerle incele.
- **🔒 %100 Gizlilik:** Tüm veriler yerel `ayna.db` (SQLite) dosyasında tutulur, hiçbir veri dışarıya gönderilmez.
