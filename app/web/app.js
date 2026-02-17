const endpointOverview = "/api/v1/monitoring/overview?hours=24";
const endpointSeries = "/api/v1/monitoring/timeseries?hours=24";
const endpointDrilldown = "/api/v1/monitoring/drilldown?hours=24&limit=8";

let ws = null;
let wsHeartbeat = null;

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function fmtNum(value, decimals = 2) {
  return Number(value || 0).toFixed(decimals);
}

function drawLineChart(svgId, values, color) {
  const svg = document.getElementById(svgId);
  if (!svg) return;
  const width = 640;
  const height = 220;
  const pad = 18;
  const maxVal = Math.max(...values, 1);
  const minVal = Math.min(...values, 0);
  const span = maxVal - minVal || 1;

  const points = values
    .map((value, i) => {
      const x = pad + (i * (width - pad * 2)) / Math.max(values.length - 1, 1);
      const y = height - pad - ((value - minVal) / span) * (height - pad * 2);
      return `${x},${y}`;
    })
    .join(" ");

  const baseLine = `<line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="rgba(130,173,210,0.3)" />`;
  const path = `<polyline fill="none" stroke="${color}" stroke-width="3" points="${points}" />`;
  const dots = values
    .map((value, i) => {
      const x = pad + (i * (width - pad * 2)) / Math.max(values.length - 1, 1);
      const y = height - pad - ((value - minVal) / span) * (height - pad * 2);
      return `<circle cx="${x}" cy="${y}" r="2.3" fill="${color}" />`;
    })
    .join("");

  svg.innerHTML = `${baseLine}${path}${dots}`;
}

function renderRows(targetId, entries, valueFormatter) {
  const target = document.getElementById(targetId);
  if (!target) return;
  if (!entries.length) {
    target.innerHTML = `<div class="row"><span>Sem dados</span><strong>0</strong></div>`;
    return;
  }
  target.innerHTML = entries
    .map(([key, value]) => `<div class="row"><span>${key}</span><strong>${valueFormatter(value)}</strong></div>`)
    .join("");
}

function renderDrilldownRows(targetId, rows, titleField, valueBuilder) {
  const target = document.getElementById(targetId);
  if (!target) return;
  if (!rows || !rows.length) {
    target.innerHTML = `<div class="row"><span>Sem dados</span><strong>-</strong></div>`;
    return;
  }
  target.innerHTML = rows
    .map((row) => `<div class="row"><span>${row[titleField]}</span><strong>${valueBuilder(row)}</strong></div>`)
    .join("");
}

function updateStatusBadge(status) {
  const el = document.getElementById("model-status");
  if (!el) return;
  if (status === "ready") {
    el.className = "pill ok";
    el.textContent = "models ready";
    return;
  }
  el.className = "pill warn";
  el.textContent = "models learning";
}

function renderPayload(overview, series, drilldown) {
  const k = overview.kpis || {};
  setText("kpi-logins", `${k.total_logins || 0}`);
  setText("kpi-success-rate", `${fmtNum(k.login_success_rate, 1)}%`);
  setText("kpi-login-risk", fmtNum(k.avg_login_risk, 3));
  setText("kpi-latency", `${fmtNum(k.p95_login_latency_ms, 0)} ms`);
  setText("kpi-network-anomaly", `${fmtNum(k.network_anomaly_rate, 1)}%`);
  setText("kpi-blocks", `${k.blocked_actions || 0}`);
  setText("kpi-block-rate", `${fmtNum(k.defense_block_rate, 1)}%`);
  setText("kpi-models", `${k.active_models || 0}`);
  setText("last-update", new Date(overview.collected_at).toLocaleString("pt-BR"));

  updateStatusBadge((overview.model_health || {}).status || "learning");

  const actionEntries = Object.entries(overview.actions_distribution || {}).sort((a, b) => b[1] - a[1]);
  renderRows("actions-list", actionEntries, (v) => `${v}`);

  const healthRaw = Object.entries(overview.model_health || {});
  const healthEntries = healthRaw
    .filter(([key]) => key !== "status")
    .map(([key, value]) => [key, typeof value === "boolean" ? (value ? "OK" : "OFF") : fmtNum(value, 3)]);
  renderRows("health-list", healthEntries, (v) => `${v}`);

  const points = series.points || [];
  drawLineChart("chart-login-volume", points.map((p) => p.login_volume || 0), "#44c8ff");
  drawLineChart("chart-risk", points.map((p) => p.avg_login_risk || 0), "#ffba49");
  drawLineChart("chart-blocked", points.map((p) => p.blocked_attempts || 0), "#ff6b6b");
  drawLineChart("chart-network", points.map((p) => p.network_anomalies || 0), "#3ad4a0");

  renderDrilldownRows(
    "users-list",
    drilldown.top_users_by_risk || [],
    "username",
    (row) => `risk ${fmtNum(row.avg_risk, 3)}`
  );
  renderDrilldownRows(
    "ips-list",
    drilldown.top_source_ips || [],
    "source_ip",
    (row) => `ev ${row.events} | anom ${row.anomalies}`
  );
  renderDrilldownRows(
    "signatures-list",
    drilldown.top_attack_signatures || [],
    "signature",
    (row) => `${row.attack_family} | risk ${fmtNum(row.avg_risk, 3)}`
  );
}

async function refreshDashboard() {
  try {
    const [overviewRes, seriesRes, drilldownRes] = await Promise.all([
      fetch(endpointOverview),
      fetch(endpointSeries),
      fetch(endpointDrilldown),
    ]);
    if (!overviewRes.ok || !seriesRes.ok || !drilldownRes.ok) {
      throw new Error("Falha ao carregar monitoramento");
    }
    const [overview, series, drilldown] = await Promise.all([
      overviewRes.json(),
      seriesRes.json(),
      drilldownRes.json(),
    ]);
    renderPayload(overview, series, drilldown);
  } catch (error) {
    setText("last-update", "erro ao atualizar");
    console.error(error);
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const wsUrl = `${protocol}://${window.location.host}/ws/monitoring`;
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    if (wsHeartbeat) clearInterval(wsHeartbeat);
    wsHeartbeat = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 15000);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "monitoring.update") {
        const payload = data.payload || {};
        renderPayload(payload.overview || {}, payload.timeseries || {}, payload.drilldown || {});
      }
    } catch (error) {
      console.error(error);
    }
  };

  ws.onclose = () => {
    if (wsHeartbeat) {
      clearInterval(wsHeartbeat);
      wsHeartbeat = null;
    }
    setTimeout(connectWebSocket, 3000);
  };
}

refreshDashboard();
setInterval(refreshDashboard, 15000);
connectWebSocket();
