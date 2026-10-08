// Ayna - Frontend Core Controller

let currentTab = 'tab-today';
let todayPlans = [];
let cachedStats = null;

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupDateDisplay();
  checkSystemStatus();
  loadTodayPlans();
  loadStats();
  loadJournalEntries();
  setupForms();
});

// Setup Tab Navigation
function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const pageTitle = document.getElementById('pageTitle');
  const titles = {
    'tab-today': 'Günün Taahhütleri',
    'tab-dayend': 'Gün Sonu Muhasebesi',
    'tab-journal': 'Fikir & Düşünce Günlüğü',
    'tab-stats': 'Gerçeklik Analitiği & Geçmiş',
    'tab-settings': 'Model & Tercihler'
  };

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(i => i.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      item.classList.add('active');
      const tabId = item.getAttribute('data-tab');
      currentTab = tabId;
      document.getElementById(tabId).classList.add('active');

      if (pageTitle && titles[tabId]) {
        pageTitle.innerText = titles[tabId];
      }

      // Refresh data on tab switch
      if (tabId === 'tab-today') loadTodayPlans();
      if (tabId === 'tab-dayend') loadDayEndTable();
      if (tabId === 'tab-stats') loadStats();
      if (tabId === 'tab-journal') loadJournalEntries();
    });
  });
}

// Display Current Turkish Date
function setupDateDisplay() {
  const dateEl = document.getElementById('currentDateFormatted');
  const now = new Date();
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  dateEl.innerText = now.toLocaleDateString('tr-TR', options);
}

// Check Ollama & Server Status
let pullPollingInterval = null;

async function checkSystemStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const dot = document.getElementById('statusDot');
    const title = document.getElementById('statusTitle');
    const model = document.getElementById('statusModel');
    const dlWrap = document.getElementById('modelDownloadWrap');
    const btnDl = document.getElementById('btnDownloadModel');
    const barBg = document.getElementById('downloadProgressBarBg');
    const barFill = document.getElementById('downloadProgressBarFill');
    const progressTxt = document.getElementById('downloadProgressText');

    if (data.ollama && data.ollama.running) {
      if (data.ollama.has_target_model) {
        dot.className = 'status-indicator-dot online';
        title.innerText = 'Lokal LLM Bağlı';
        model.innerText = data.settings.ollama_model || data.ollama.active_model;
        if (dlWrap) dlWrap.style.display = 'none';
        if (pullPollingInterval) { clearInterval(pullPollingInterval); pullPollingInterval = null; }
      } else {
        // Ollama is running but target model not downloaded yet!
        dot.className = 'status-indicator-dot';
        dot.style.background = '#38bdf8';
        title.innerText = 'Model Kurulumu Gerekli';
        model.innerText = 'qwen2.5:7b hazır değil';
        if (dlWrap) dlWrap.style.display = 'block';

        // Check if currently pulling
        if (data.ollama.pull_state && data.ollama.pull_state.is_pulling) {
          btnDl.disabled = true;
          btnDl.innerText = 'İndiriliyor...';
          barBg.style.display = 'block';
          progressTxt.style.display = 'block';
          barFill.style.width = `${data.ollama.pull_state.percent}%`;
          progressTxt.innerText = `%${data.ollama.pull_state.percent} (${data.ollama.pull_state.status})`;
          startPullPolling();
        }
      }
    } else {
      dot.className = 'status-indicator-dot offline';
      title.innerText = 'Ollama Bekleniyor';
      model.innerText = 'Dahili Kural Motoru';
      if (dlWrap) dlWrap.style.display = 'none';
    }

    // Populate settings inputs
    if (data.settings) {
      if (document.getElementById('settingOllamaUrl')) document.getElementById('settingOllamaUrl').value = data.settings.ollama_url || 'http://localhost:11434';
      if (document.getElementById('settingOllamaModel')) document.getElementById('settingOllamaModel').value = data.settings.ollama_model || 'qwen2.5:7b';
      if (document.getElementById('settingUserName')) document.getElementById('settingUserName').value = data.settings.user_name || 'Semih';
      if (document.getElementById('settingHonestyLevel')) document.getElementById('settingHonestyLevel').value = data.settings.honesty_level || 'brutal';
    }
  } catch (err) {
    console.warn('Status check failed:', err);
  }
}

function startPullPolling() {
  if (pullPollingInterval) return;
  pullPollingInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/ollama/pull-status');
      const state = await res.json();
      const barFill = document.getElementById('downloadProgressBarFill');
      const progressTxt = document.getElementById('downloadProgressText');
      const btnDl = document.getElementById('btnDownloadModel');

      if (state.is_pulling) {
        barFill.style.width = `${state.percent}%`;
        progressTxt.innerText = `%${state.percent} (${state.status})`;
      } else {
        clearInterval(pullPollingInterval);
        pullPollingInterval = null;
        checkSystemStatus();
      }
    } catch (e) {
      clearInterval(pullPollingInterval);
      pullPollingInterval = null;
    }
  }, 2000);
}


// Load Today's Plans
async function loadTodayPlans() {
  try {
    const res = await fetch('/api/plans');
    const data = await res.json();
    todayPlans = data.plans || [];
    renderTodayPlans();
  } catch (err) {
    console.error('Error loading plans:', err);
  }
}

function renderTodayPlans() {
  const listEl = document.getElementById('todayPlanList');
  const totalBadge = document.getElementById('todayTotalPlanned');

  if (!todayPlans.length) {
    listEl.innerHTML = '<div class="empty-placeholder">Henüz bugüne bir taahhüt girmedin. Yukarıdan ilk planını ekle.</div>';
    totalBadge.innerText = 'Toplam: 0 saat';
    return;
  }

  let totalHours = 0;
  listEl.innerHTML = todayPlans.map(plan => {
    totalHours += plan.planned_hours;
    return `
      <div class="plan-item" data-id="${plan.id}">
        <div class="plan-item-left">
          <span class="plan-cat-tag cat-tag-${plan.category}">${plan.category}</span>
          <span class="plan-text">${escapeHtml(plan.planned_text)}</span>
        </div>
        <div class="plan-item-right">
          <span class="plan-hour-pill">${plan.planned_hours} saat</span>
        </div>
      </div>
    `;
  }).join('');

  totalBadge.innerText = `Toplam: ${totalHours.toFixed(1)} saat`;
}

// Setup Forms and Buttons
function setupForms() {
  // Add Plan Form
  const planForm = document.getElementById('addPlanForm');
  planForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const category = document.querySelector('input[name="planCategory"]:checked').value;
    const text = document.getElementById('planTextInput').value.trim();
    const hours = parseFloat(document.getElementById('planHoursInput').value) || 1.0;

    if (!text) return;

    try {
      const res = await fetch('/api/plans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, planned_text: text, planned_hours: hours })
      });
      if (res.ok) {
        document.getElementById('planTextInput').value = '';
        await loadTodayPlans();
        loadStats();
      }
    } catch (err) {
      alert('Plan eklenirken hata oluştu.');
    }
  });

  // Mirror Check Button
  const btnTrigger = document.getElementById('btnTriggerMirror');
  btnTrigger.addEventListener('click', triggerMirrorCritique);

  // One-click Model Download Button
  const btnDl = document.getElementById('btnDownloadModel');
  if (btnDl) {
    btnDl.addEventListener('click', async () => {
      btnDl.disabled = true;
      btnDl.innerText = 'İndirme Başlatılıyor...';
      document.getElementById('downloadProgressBarBg').style.display = 'block';
      document.getElementById('downloadProgressText').style.display = 'block';
      try {
        await fetch('/api/ollama/pull', { method: 'POST' });
        startPullPolling();
      } catch (err) {
        alert('İndirme başlatılamadı: ' + err);
        btnDl.disabled = false;
        btnDl.innerText = '⬇️ Modeli İndir (Tek Tıkla)';
      }
    });
  }

  // Day End Review Submission
  const btnDayEnd = document.getElementById('btnSubmitDayEnd');
  btnDayEnd.addEventListener('click', submitDayEndReflection);

  // Journal Form
  const journalForm = document.getElementById('journalForm');
  journalForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('journalTitleInput').value.trim();
    const category = document.querySelector('input[name="journalCategory"]:checked').value;
    const content = document.getElementById('journalContentInput').value.trim();

    if (!title || !content) return;

    const btn = document.getElementById('btnSaveJournal');
    btn.disabled = true;
    btn.innerText = 'Ayna Yorumluyor...';

    try {
      const res = await fetch('/api/journal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content, category })
      });
      if (res.ok) {
        document.getElementById('journalTitleInput').value = '';
        document.getElementById('journalContentInput').value = '';
        await loadJournalEntries();
      }
    } catch (err) {
      alert('Not kaydedilirken hata oluştu.');
    } finally {
      btn.disabled = false;
      btn.innerText = 'Ayna\'ya Gönder & Kaydet';
    }
  });

  // Journal Filter Buttons
  const filterBtns = document.querySelectorAll('#journalFilterPills .filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadJournalEntries(btn.getAttribute('data-filter'));
    });
  });

  // Settings Save
  const btnSettings = document.getElementById('btnSaveSettings');
  btnSettings.addEventListener('click', async () => {
    const payload = {
      ollama_url: document.getElementById('settingOllamaUrl').value.trim(),
      ollama_model: document.getElementById('settingOllamaModel').value.trim(),
      user_name: document.getElementById('settingUserName').value.trim(),
      honesty_level: document.getElementById('settingHonestyLevel').value
    };
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        alert('Ayarlar kaydedildi.');
        checkSystemStatus();
      }
    } catch (err) {
      alert('Ayarlar kaydedilemedi.');
    }
  });
}

// Trigger AI Mirror Critique
async function triggerMirrorCritique() {
  const box = document.getElementById('mirrorCritiqueBox');
  const spinner = document.getElementById('critiqueSpinner');

  spinner.style.display = 'block';
  box.innerHTML = '<span style="color: #94a3b8;">Ayna planlarını ve geçmiş verilerini inceliyor...</span>';

  try {
    const res = await fetch('/api/plans/critique', { method: 'POST' });
    const data = await res.json();
    box.innerText = data.critique || 'Analiz üretilemedi.';
  } catch (err) {
    box.innerText = 'Ayna bağlantısında hata oluştu.';
  } finally {
    spinner.style.display = 'none';
  }
}

// Load and Render Day End Review Table
async function loadDayEndTable() {
  await loadTodayPlans();
  const tbody = document.getElementById('dayEndTableBody');

  if (!todayPlans.length) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center empty-placeholder">Bugüne ait kayıtlı taahhüt bulunmuyor.</td></tr>';
    return;
  }

  tbody.innerHTML = todayPlans.map(p => `
    <tr data-id="${p.id}">
      <td><span class="plan-cat-tag cat-tag-${p.category}">${p.category}</span></td>
      <td><strong>${escapeHtml(p.planned_text)}</strong></td>
      <td>${p.planned_hours} sa</td>
      <td>
        <input type="number" step="any" min="0" max="24" class="table-input" id="act_${p.id}" value="${p.actual_hours || p.planned_hours}">
      </td>
      <td>
        <select class="status-select" id="st_${p.id}">
          <option value="pending" ${p.status === 'pending' ? 'selected' : ''}>Bekliyor</option>
          <option value="completed" ${p.status === 'completed' ? 'selected' : ''}>Tamamlandı</option>
          <option value="partial" ${p.status === 'partial' ? 'selected' : ''}>Kısmen Yapıldı</option>
          <option value="skipped" ${p.status === 'skipped' ? 'selected' : ''}>Ertelendi / Yapılmadı</option>
        </select>
      </td>
      <td>
        <input type="text" class="table-excuse-input" id="ex_${p.id}" placeholder="Mazeret / Gözlem" value="${escapeHtml(p.excuse || '')}">
      </td>
      <td>
        <button class="btn-sm" onclick="savePlanActual(${p.id})">Kaydet</button>
      </td>
    </tr>
  `).join('');
}

// Save Single Plan Result
window.savePlanActual = async function(planId) {
  const actualHours = parseFloat(document.getElementById(`act_${planId}`).value) || 0;
  const status = document.getElementById(`st_${planId}`).value;
  const excuse = document.getElementById(`ex_${planId}`).value;

  try {
    const res = await fetch(`/api/plans/${planId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actual_hours: actualHours, status, excuse })
    });
    if (res.ok) {
      loadStats();
    }
  } catch (err) {
    alert('Güncellenirken hata oluştu.');
  }
};

// Submit Day End Review
async function submitDayEndReflection() {
  const note = document.getElementById('dayEndGeneralNote').value.trim();
  const box = document.getElementById('dayEndReflectionBox');
  const btn = document.getElementById('btnSubmitDayEnd');

  btn.disabled = true;
  btn.innerText = 'Ayna Değerlendiriyor...';
  box.style.display = 'block';
  box.innerText = 'Bugünkü taahhütlerin ve mazeretlerin analiz ediliyor...';

  try {
    const res = await fetch('/api/plans/day-end', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note })
    });
    const data = await res.json();
    box.innerText = data.reflection || 'Değerlendirme alınamadı.';
    loadStats();
  } catch (err) {
    box.innerText = 'Günün analizi alınırken hata oluştu.';
  } finally {
    btn.disabled = false;
    btn.innerText = 'Günü Kapat & Ayna Raporu Al';
  }
}

// Load Journal Entries
async function loadJournalEntries(category = 'all') {
  try {
    const url = (category && category !== 'all') ? `/api/journal?category=${category}` : '/api/journal';
    const res = await fetch(url);
    const data = await res.json();
    renderJournalFeed(data.entries || []);
  } catch (err) {
    console.error('Error loading journal:', err);
  }
}

function renderJournalFeed(entries) {
  const feed = document.getElementById('journalFeed');
  if (!entries.length) {
    feed.innerHTML = '<div class="empty-placeholder">Bu kategoride henüz bir düşünce notu yok.</div>';
    return;
  }

  feed.innerHTML = entries.map(item => `
    <div class="journal-card">
      <div class="journal-card-top">
        <span class="journal-card-title">${escapeHtml(item.title)}</span>
        <span class="plan-cat-tag cat-tag-${item.category}">${item.category}</span>
      </div>
      <div class="journal-card-date">${item.date}</div>
      <div class="journal-card-text">${escapeHtml(item.content)}</div>
      ${item.ai_reflection ? `<div class="journal-ai-quote"><strong>🪞 Ayna:</strong> ${escapeHtml(item.ai_reflection)}</div>` : ''}
    </div>
  `).join('');
}

// Load Reality Stats
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    cachedStats = data;

    // Sidebar Score
    const sideScore = document.getElementById('sidebarRealityScore');
    const sideBar = document.getElementById('sidebarRealityBar');
    const sideDesc = document.getElementById('sidebarScoreDesc');
    const sideBadge = document.getElementById('sidebarBiasBadge');

    sideScore.innerText = `%${data.reality_score}`;
    sideBar.style.width = `${Math.min(data.reality_score, 100)}%`;

    if (data.reality_score >= 80) {
      sideBadge.innerText = 'Yüksek Gerçekçilik';
      sideDesc.innerText = 'Kendine karşı çok dürüstsün.';
    } else if (data.reality_score >= 50) {
      sideBadge.innerText = 'Orta Sapma';
      sideDesc.innerText = 'Bazen kapasiteni aşıyorsun.';
    } else {
      sideBadge.innerText = 'Aşırı İyimser';
      sideDesc.innerText = 'Planlarınla gerçekler uyuşmuyor.';
    }

    // Tab Stats Grid
    document.getElementById('statTotalPlanned').innerText = `${data.total_planned} saat`;
    document.getElementById('statTotalActual').innerText = `${data.total_actual} saat`;
    document.getElementById('statRealityScore').innerText = `%${data.reality_score}`;
    document.getElementById('statOptimismBias').innerText = `+${data.optimism_bias_percentage}%`;

    // Pillar breakdown
    renderPillarStats(data.categories || {});
  } catch (err) {
    console.error('Stats loading error:', err);
  }
}

function renderPillarStats(categories) {
  const container = document.getElementById('pillarStatsGrid');
  const pillars = [
    { key: 'ders', label: '📚 Ders & Akademik', color: 'var(--color-ders)' },
    { key: 'is', label: '💼 İş & Projeler', color: 'var(--color-is)' },
    { key: 'muzik', label: '🎵 Müzik & Üretim', color: 'var(--color-muzik)' },
    { key: 'spor', label: '🏃 Spor & Beden', color: 'var(--color-spor)' }
  ];

  container.innerHTML = pillars.map(p => {
    const stat = categories[p.key] || { accuracy_percentage: 0, total_planned: 0, total_actual: 0 };
    return `
      <div class="pillar-stat-box">
        <div class="pillar-stat-header">
          <span class="pillar-stat-name" style="color: ${p.color};">${p.label}</span>
          <span class="pillar-stat-score">%${stat.accuracy_percentage}</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${Math.min(stat.accuracy_percentage, 100)}%; background: ${p.color};"></div>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-dim); display: flex; justify-content: space-between;">
          <span>Hedef: ${stat.total_planned} sa</span>
          <span>Fiili: ${stat.total_actual} sa</span>
        </div>
      </div>
    `;
  }).join('');
}

// Utility: Escape HTML
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
