let BACKEND_URL = window.location.origin;
let SESSION_ID  = 'default';
let isThinking  = false;

const messagesWrap   = document.getElementById('messages-wrap');
const userInput      = document.getElementById('user-input');
const sendBtn        = document.getElementById('send-btn');
const welcomeScreen  = document.getElementById('welcome-screen');
const statusDot      = document.getElementById('status-dot');
const statusLabel    = document.getElementById('status-label');
const sessionDisplay = document.getElementById('session-display');

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function scrollToBottom() {
  messagesWrap.scrollTo({ top: messagesWrap.scrollHeight, behavior: 'smooth' });
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function setStatus(status) {
  const states = {
    ready:    { color: 'var(--accent-green)',  text: 'Agent Ready' },
    thinking: { color: 'var(--accent-amber)',  text: 'Thinking…' },
    calling:  { color: 'var(--accent-purple)', text: 'Calling Tools…' },
    error:    { color: 'var(--accent-pink)',   text: 'Error' },
  };
  const s = states[status] || states.ready;
  statusDot.style.background   = s.color;
  statusDot.style.boxShadow    = `0 0 10px ${s.color}`;
  statusLabel.textContent      = s.text;
}

function hideWelcome() {
  if (welcomeScreen) {
    welcomeScreen.style.opacity = '0';
    welcomeScreen.style.transition = 'opacity 0.3s ease';
    setTimeout(() => welcomeScreen.remove(), 300);
  }
}

function createUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'msg-row user';
  row.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-content">
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-time">${formatTime(new Date())}</div>
    </div>`;
  return row;
}

function createTypingIndicator() {
  const row = document.createElement('div');
  row.className = 'msg-row ai';
  row.id = 'typing-row';
  row.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <span class="typing-label">WeatherAI is thinking…</span>
      </div>
    </div>`;
  return row;
}

function createToolBadge(toolName, location) {
  const badge = document.createElement('div');
  badge.className = 'tool-badge';
  const icon = toolName === 'get_current_weather' ? '🌡️' : '📅';
  badge.innerHTML = `
    <div class="tool-dot"></div>
    <span>${icon} Calling <strong>${toolName}</strong> for "${location}"</span>`;
  return badge;
}

function createAIMessage(text, toolCalls) {
  const row = document.createElement('div');
  row.className = 'msg-row ai';

  // Parse text: detect if there are weather card data embedded
  const bubbleText = escapeHtml(text).replace(/\n/g, '<br>');

  let toolTraceHtml = '';
  if (toolCalls && toolCalls.length > 0) {
    const items = toolCalls.map(tc => {
      const inputStr = JSON.stringify(tc.input);
      const status = tc.error
        ? `<span style="color:var(--accent-pink)">❌ Error: ${escapeHtml(tc.error)}</span>`
        : `<span style="color:var(--accent-green)">✓ Success</span>`;
      return `<div class="trace-item">⚡ <code>${tc.tool}</code> · Input: <code>${escapeHtml(inputStr)}</code> · ${status}</div>`;
    }).join('');

    toolTraceHtml = `
      <div class="tool-trace">
        <div class="tool-trace-header" onclick="toggleTrace(this)">
          <span class="trace-arrow">▶</span>
          ⚡ ${toolCalls.length} tool call${toolCalls.length > 1 ? 's' : ''} executed
        </div>
        <div class="tool-trace-body">${items}</div>
      </div>`;
  }

  // Render weather cards for tool results
  const weatherCardsHtml = (toolCalls || [])
    .filter(tc => !tc.error && tc.result)
    .map(tc => renderWeatherCard(tc.result))
    .join('');

  row.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-content" style="max-width:80%;">
      <div class="msg-bubble">${bubbleText}</div>
      ${weatherCardsHtml}
      ${toolTraceHtml}
      <div class="msg-time">${formatTime(new Date())}</div>
    </div>`;
  return row;
}

function renderWeatherCard(data) {
  if (!data) return '';
  if (data.type === 'current_weather') return renderCurrentCard(data);
  if (data.type === 'weather_forecast') return renderForecastCard(data);
  return '';
}

function renderCurrentCard(d) {
  const temp = d.temperature_c != null ? Math.round(d.temperature_c) : '--';
  const feels = d.feels_like_c != null ? Math.round(d.feels_like_c) : '--';
  const hum   = d.humidity_percent != null ? d.humidity_percent : '--';
  const wind  = d.wind_speed_kmh != null ? Math.round(d.wind_speed_kmh) : '--';
  const uv    = d.uv_index != null ? d.uv_index.toFixed(1) : '--';
  const press = d.pressure_hpa != null ? Math.round(d.pressure_hpa) : '--';

  return `
  <div class="weather-card">
    <div class="wc-header">
      <div>
        <div class="wc-location">📍 ${escapeHtml(d.location || '')}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${escapeHtml(d.timezone || '')}</div>
      </div>
      <div class="wc-type">Live</div>
    </div>
    <div class="wc-body">
      <div class="wc-current-main">
        <div class="wc-icon-big">${d.icon || '🌡️'}</div>
        <div>
          <div class="wc-temp-big">${temp}<span>°C</span></div>
          <div class="wc-condition-label">${escapeHtml(d.condition || '')} · Feels like ${feels}°C</div>
        </div>
      </div>
      <div class="wc-stats">
        <div class="wc-stat">
          <div class="wc-stat-label">Humidity</div>
          <div class="wc-stat-value">${hum}<span class="wc-stat-unit">%</span></div>
        </div>
        <div class="wc-stat">
          <div class="wc-stat-label">Wind</div>
          <div class="wc-stat-value">${wind}<span class="wc-stat-unit"> km/h</span></div>
        </div>
        <div class="wc-stat">
          <div class="wc-stat-label">UV Index</div>
          <div class="wc-stat-value">${uv}</div>
        </div>
        <div class="wc-stat">
          <div class="wc-stat-label">Pressure</div>
          <div class="wc-stat-value">${press}<span class="wc-stat-unit"> hPa</span></div>
        </div>
        <div class="wc-stat">
          <div class="wc-stat-label">Rain</div>
          <div class="wc-stat-value">${d.precipitation_mm ?? 0}<span class="wc-stat-unit"> mm</span></div>
        </div>
        <div class="wc-stat">
          <div class="wc-stat-label">Visibility</div>
          <div class="wc-stat-value">${d.visibility_m != null ? (d.visibility_m/1000).toFixed(1) : '--'}<span class="wc-stat-unit"> km</span></div>
        </div>
      </div>
    </div>
  </div>`;
}

function renderForecastCard(d) {
  if (!d.forecast || d.forecast.length === 0) return '';

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const daysHtml = d.forecast.map(day => {
    const date  = new Date(day.date + 'T12:00:00');
    const name  = dayNames[date.getDay()];
    const high  = day.temp_max_c != null ? Math.round(day.temp_max_c) : '--';
    const low   = day.temp_min_c != null ? Math.round(day.temp_min_c) : '--';
    const rain  = day.precipitation_probability != null ? day.precipitation_probability : null;
    const cond  = (day.condition || '').length > 14 ? (day.condition || '').slice(0,12)+'…' : (day.condition || '');

    return `
    <div class="wc-day">
      <div class="wc-day-name">${name}</div>
      <div class="wc-day-icon">${day.icon || '🌡️'}</div>
      <div class="wc-day-cond">${escapeHtml(cond)}</div>
      <div class="wc-day-temps">
        <span class="wc-temp-high">${high}°</span>
        <span class="wc-temp-low">${low}°</span>
      </div>
      ${rain !== null ? `<div class="wc-day-rain">💧 ${rain}%</div>` : ''}
    </div>`;
  }).join('');

  return `
  <div class="weather-card">
    <div class="wc-header">
      <div>
        <div class="wc-location">📍 ${escapeHtml(d.location || '')}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${d.days_requested}-day forecast</div>
      </div>
      <div class="wc-type">Forecast</div>
    </div>
    <div class="wc-body">
      <div class="wc-forecast-grid">${daysHtml}</div>
    </div>
  </div>`;
}

// ── Escape HTML ──────────────────────────────────────────────
function escapeHtml(str) {
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

function toggleTrace(header) {
  const arrow = header.querySelector('.trace-arrow');
  const body  = header.nextElementSibling;
  arrow.classList.toggle('open');
  body.classList.toggle('open');
}

function toggleSettings() {
  const panel = document.getElementById('settings-panel');
  panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function saveSettings() {
  BACKEND_URL = document.getElementById('backend-url').value.trim().replace(/\/$/, '');
  SESSION_ID  = document.getElementById('session-id-input').value.trim() || 'default';
  sessionDisplay.textContent = `Session: ${SESSION_ID}`;
  toggleSettings();
  showToast('Settings saved');
}

function showToast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  Object.assign(t.style, {
    position: 'fixed', bottom: '32px', right: '32px',
    background: 'rgba(79,142,247,0.9)', color: '#fff',
    padding: '10px 20px', borderRadius: '10px',
    fontSize: '13px', zIndex: 1000,
    animation: 'fadeUp 0.3s ease',
    backdropFilter: 'blur(10px)',
    boxShadow: '0 4px 20px rgba(79,142,247,0.4)',
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isThinking) return;

  hideWelcome();
  isThinking = true;
  sendBtn.disabled = true;
  setStatus('thinking');

  // Add user message
  const userRow = createUserMessage(text);
  messagesWrap.appendChild(userRow);
  userInput.value = '';
  autoResize(userInput);
  scrollToBottom();

  // Add typing indicator
  const typingRow = createTypingIndicator();
  messagesWrap.appendChild(typingRow);
  scrollToBottom();

  try {
    const response = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: SESSION_ID,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();

    // Update status if tools were called
    if (data.tool_calls && data.tool_calls.length > 0) {
      setStatus('calling');
      await new Promise(r => setTimeout(r, 300)); // brief visual pause
    }

    // Remove typing indicator
    typingRow.remove();

    // Add AI response
    const aiRow = createAIMessage(data.reply, data.tool_calls);
    messagesWrap.appendChild(aiRow);
    scrollToBottom();

  } catch (err) {
    typingRow.remove();
    const errRow = document.createElement('div');
    errRow.className = 'msg-row ai';
    errRow.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="msg-bubble" style="border-color:rgba(236,72,153,0.3);background:rgba(236,72,153,0.06);">
          ⚠️ <strong>Connection Error</strong><br>
          ${escapeHtml(err.message)}<br><br>
          <span style="color:var(--text-muted);font-size:12px;">
            Make sure the backend is running:<br>
            <code style="background:rgba(255,255,255,0.06);padding:2px 6px;border-radius:4px;">
              cd backend &amp;&amp; uvicorn main:app --reload
            </code>
          </span>
        </div>
      </div>`;
    messagesWrap.appendChild(errRow);
    scrollToBottom();
    setStatus('error');
  } finally {
    isThinking = false;
    sendBtn.disabled = false;
    setTimeout(() => setStatus('ready'), 2000);
  }
}

function sendQuickMessage(btn) {
  const msg = btn.dataset.msg;
  if (!msg || isThinking) return;
  userInput.value = msg;
  sendMessage();
}

function sendChip(el) {
  const text = el.textContent.replace(/^[^\s]+\s/, '').trim(); // strip emoji
  if (isThinking) return;
  userInput.value = el.textContent.trim();
  sendMessage();
}

async function clearChat() {
  try {
    await fetch(`${BACKEND_URL}/chat/${SESSION_ID}`, { method: 'DELETE' });
  } catch (_) {}

  // Clear messages except welcome screen area
  messagesWrap.innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <div class="welcome-icon">🌦️</div>
      <h1 class="welcome-title">Ask me anything about weather</h1>
      <p class="welcome-sub">
        I'm powered by <strong>AWS Bedrock (Nova)</strong> and use real tool-calling to fetch 
        live weather data from anywhere in the world.
      </p>
      <div class="welcome-chips">
        <button class="chip" onclick="sendChip(this)">🌡️ Current weather in Paris</button>
        <button class="chip" onclick="sendChip(this)">📅 5-day forecast for Dubai</button>
        <button class="chip" onclick="sendChip(this)">🌧️ Will it rain in Berlin this week?</button>
        <button class="chip" onclick="sendChip(this)">❄️ Is it cold in Moscow right now?</button>
        <button class="chip" onclick="sendChip(this)">🌬️ Wind conditions in Chicago?</button>
        <button class="chip" onclick="sendChip(this)">🌊 Weather in Bali, Indonesia</button>
      </div>
    </div>`;

  setStatus('ready');
  showToast('Chat cleared');
}

function handleKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

window.addEventListener('DOMContentLoaded', () => {
  userInput.focus();
  sessionDisplay.textContent = `Session: ${SESSION_ID}`;
  document.getElementById('backend-url').value = BACKEND_URL;
});
