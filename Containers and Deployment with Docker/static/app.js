const form = document.querySelector("#measurement-form");
const valueInput = document.querySelector("#value");
const result = document.querySelector("#result");
const responseBox = document.querySelector("#response-box");
const chartSection = document.querySelector(".chart-section");
const chart = document.querySelector("#measurements-chart");
let lastMeasurements = [];

const formatNumber = (value) => value === null || value === undefined ? "—" : Number(value).toFixed(2);

function renderChart(measurements = []) {
  lastMeasurements = measurements;
  chartSection.classList.toggle("has-data", measurements.length > 0);

  const width = Math.max(chart.clientWidth, 280);
  const height = 180;
  const scale = window.devicePixelRatio || 1;
  chart.width = width * scale;
  chart.height = height * scale;
  const context = chart.getContext("2d");
  context.scale(scale, scale);
  context.clearRect(0, 0, width, height);

  context.strokeStyle = "#eeeaf4";
  context.lineWidth = 1;
  [35, 90, 145].forEach((y) => {
    context.beginPath();
    context.moveTo(0, y);
    context.lineTo(width, y);
    context.stroke();
  });

  if (!measurements.length) return;

  const values = measurements.map((item) => item.value);
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = Math.max(maximum - minimum, 1);
  const padding = 18;
  const point = (item, index) => ({
    x: measurements.length === 1 ? width / 2 : (index / (measurements.length - 1)) * width,
    y: height - padding - ((item.value - minimum) / range) * (height - padding * 2),
  });

  context.beginPath();
  measurements.forEach((item, index) => {
    const position = point(item, index);
    if (index === 0) context.moveTo(position.x, position.y);
    else context.lineTo(position.x, position.y);
  });
  context.strokeStyle = "#8b5cf6";
  context.lineWidth = 2;
  context.stroke();

  measurements.forEach((item, index) => {
    const position = point(item, index);
    context.beginPath();
    context.arc(position.x, position.y, item.anomaly === true ? 5 : 3.5, 0, Math.PI * 2);
    context.fillStyle = item.anomaly === true ? "#a21caf" : item.status === "warming_up" ? "#c4b5fd" : "#6d28d9";
    context.fill();
  });
}

function showResult(data) {
  const analysis = data.analysis;
  const isAnomaly = analysis.anomaly === true;
  const warmingUp = analysis.status === "warming_up";

  result.classList.toggle("is-alert", isAnomaly);
  document.querySelector("#verdict-label").textContent = warmingUp ? "Recopilando contexto" : isAnomaly ? "Anomalía detectada" : "Señal normal";
  document.querySelector("#verdict-value").textContent = formatNumber(data.measurement.value);
  document.querySelector("#verdict-detail").textContent = warmingUp ? "Necesitamos más señales para comparar el patrón." : isAnomaly ? "El error supera el umbral configurado." : "La señal está dentro del patrón aprendido.";
  document.querySelector("#prediction").textContent = formatNumber(analysis.prediction);
  document.querySelector("#error").textContent = formatNumber(analysis.error);
  responseBox.textContent = "Medición guardada en RedisTimeSeries.";
  renderChart(data.measurements);
}

async function checkConnection() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    document.querySelector("#system-state").textContent = data.redis === "connected" ? "Conectado" : "Redis no disponible";
  } catch (error) {
    document.querySelector("#system-state").textContent = "Sin conexión";
  }
}

async function loadMeasurements() {
  try {
    const response = await fetch("/api/measurements?limit=40");
    if (!response.ok) return;
    const data = await response.json();
    renderChart(data.measurements);
  } catch (error) {
    renderChart([]);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!valueInput.value) return;
  responseBox.textContent = "Analizando…";

  try {
    const response = await fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: valueInput.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "No se pudo analizar la medición.");
    showResult(data);
    valueInput.value = "";
  } catch (error) {
    responseBox.textContent = error.message;
  }
});

document.querySelectorAll("[data-value]").forEach((button) => {
  button.addEventListener("click", () => {
    valueInput.value = button.dataset.value;
    valueInput.focus();
  });
});

document.querySelector("#reset-button").addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  result.classList.remove("is-alert");
  document.querySelector("#verdict-label").textContent = "Sin análisis";
  document.querySelector("#verdict-value").textContent = "—";
  document.querySelector("#verdict-detail").textContent = "El resultado aparecerá aquí.";
  document.querySelector("#prediction").textContent = "—";
  document.querySelector("#error").textContent = "—";
  responseBox.textContent = "Prueba reiniciada.";
  renderChart([]);
});

checkConnection();
loadMeasurements();
window.addEventListener("resize", () => renderChart(lastMeasurements));
