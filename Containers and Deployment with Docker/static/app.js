const form = document.querySelector("#measurement-form");
const valueInput = document.querySelector("#value");
const result = document.querySelector("#result");
const responseBox = document.querySelector("#response-box");
const chartSection = document.querySelector(".chart-section");
const chart = document.querySelector("#measurements-chart");
const chartData = document.querySelector("#chart-data");
let lastMeasurements = [];

const formatNumber = (value) => value === null || value === undefined ? "—" : Number(value).toFixed(2);

function renderChart(measurements = []) {
  lastMeasurements = measurements;
  chartSection.classList.toggle("has-data", measurements.length > 0);
  chartData.replaceChildren();

  const dataStart = Math.max(0, measurements.length - 12);
  measurements.slice(dataStart).forEach((item, index) => {
    const label = document.createElement("span");
    const itemNumber = dataStart + index + 1;
    label.className = `chart-data-item${item.anomaly === true ? " anomaly" : item.status === "warming_up" ? " context" : ""}`;
    label.textContent = `#${itemNumber} · ${formatNumber(item.value)} °C`;
    chartData.appendChild(label);
  });

  const width = Math.max(Math.round(chart.clientWidth), 280);
  const height = Math.max(Math.round(chart.clientHeight), 220);
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  chart.width = Math.round(width * scale);
  chart.height = Math.round(height * scale);
  const context = chart.getContext("2d");
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, height);

  const margin = { top: 18, right: 18, bottom: 34, left: 48 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const plotRight = margin.left + plotWidth;
  const plotBottom = margin.top + plotHeight;
  const values = measurements.map((item) => Number(item.value));

  context.font = "12px system-ui, sans-serif";
  context.lineWidth = 1;
  context.strokeStyle = "#ebe7f2";
  context.fillStyle = "#8a8196";
  context.textAlign = "right";
  context.textBaseline = "middle";

  if (values.length) {
    const rawMinimum = Math.min(...values);
    const rawMaximum = Math.max(...values);
    const lowerBound = Math.min(0, rawMinimum);
    const usefulRange = Math.max(rawMaximum - lowerBound, 50);
    const magnitude = 10 ** Math.floor(Math.log10(usefulRange / 4));
    const step = Math.max(1, Math.ceil(usefulRange / 4 / magnitude) * magnitude);
    const minimum = Math.floor(lowerBound / step) * step;
    const maximum = Math.max(Math.ceil(rawMaximum / step) * step, minimum + step * 4);
    const tickCount = Math.round((maximum - minimum) / step);

    for (let tick = 0; tick <= tickCount; tick += 1) {
      const value = minimum + tick * step;
      const y = plotBottom - ((value - minimum) / (maximum - minimum)) * plotHeight;
      context.beginPath();
      context.moveTo(margin.left, y);
      context.lineTo(plotRight, y);
      context.stroke();
      context.fillText(`${formatNumber(value).replace(".00", "")} °C`, margin.left - 10, y);
    }

    context.beginPath();
    context.moveTo(margin.left, margin.top);
    context.lineTo(margin.left, plotBottom);
    context.lineTo(plotRight, plotBottom);
    context.strokeStyle = "#dcd5e7";
    context.stroke();

    const visibleStart = Math.max(0, measurements.length - 24);
    const visibleMeasurements = measurements.slice(visibleStart);
    const point = (item, index) => ({
      x: visibleMeasurements.length === 1 ? margin.left + plotWidth / 2 : margin.left + (index / (visibleMeasurements.length - 1)) * plotWidth,
      y: plotBottom - ((Number(item.value) - minimum) / (maximum - minimum)) * plotHeight,
    });
    const points = visibleMeasurements.map(point);
    const colorFor = (item) => item.anomaly === true ? "#a21caf" : item.status === "warming_up" ? "#c4b5fd" : "#6d28d9";

    context.beginPath();
    context.moveTo(points[0].x, plotBottom);
    points.forEach((position) => context.lineTo(position.x, position.y));
    context.lineTo(points[points.length - 1].x, plotBottom);
    context.closePath();
    const fill = context.createLinearGradient(0, margin.top, 0, plotBottom);
    fill.addColorStop(0, "rgba(109, 40, 217, .10)");
    fill.addColorStop(1, "rgba(109, 40, 217, 0)");
    context.fillStyle = fill;
    context.fill();

    context.beginPath();
    points.forEach((position, index) => {
      if (index === 0) context.moveTo(position.x, position.y);
      else context.lineTo(position.x, position.y);
    });
    context.strokeStyle = "#8b5cf6";
    context.lineWidth = 2.5;
    context.lineJoin = "round";
    context.lineCap = "round";
    context.stroke();

    visibleMeasurements.slice(1).forEach((item, index) => {
      if (item.anomaly !== true && visibleMeasurements[index].anomaly !== true) return;
      context.beginPath();
      context.moveTo(points[index].x, points[index].y);
      context.lineTo(points[index + 1].x, points[index + 1].y);
      context.strokeStyle = "#a21caf";
      context.lineWidth = 3;
      context.stroke();
    });

    points.forEach((position, index) => {
      const item = visibleMeasurements[index];
      context.beginPath();
      context.arc(position.x, position.y, item.anomaly === true ? 5 : 4, 0, Math.PI * 2);
      context.fillStyle = "#ffffff";
      context.fill();
      context.beginPath();
      context.arc(position.x, position.y, item.anomaly === true ? 4 : 3, 0, Math.PI * 2);
      context.fillStyle = colorFor(item);
      context.fill();
    });

    const labelIndices = visibleMeasurements.length <= 5
      ? visibleMeasurements.map((_, index) => index)
      : [0, Math.floor((visibleMeasurements.length - 1) / 2), visibleMeasurements.length - 1];
    context.fillStyle = "#8a8196";
    context.textAlign = "center";
    context.textBaseline = "alphabetic";
    labelIndices.forEach((index) => {
      context.fillText(`#${visibleStart + index + 1}`, points[index].x, height - 9);
    });
  } else {
    context.beginPath();
    context.moveTo(margin.left, margin.top);
    context.lineTo(margin.left, plotBottom);
    context.lineTo(plotRight, plotBottom);
    context.strokeStyle = "#dcd5e7";
    context.stroke();
  }
}

function showResult(data) {
  const analysis = data.analysis;
  const isAnomaly = analysis.anomaly === true;
  const warmingUp = analysis.status === "warming_up";

  result.classList.toggle("is-alert", isAnomaly);
  document.querySelector("#verdict-label").textContent = warmingUp ? "Collecting context" : isAnomaly ? "Anomaly detected" : "Signal normal";
  document.querySelector("#verdict-value").textContent = formatNumber(data.measurement.value);
  document.querySelector("#verdict-detail").textContent = warmingUp ? "More signals are needed to compare the pattern." : isAnomaly ? "The error is above the configured threshold." : "The signal is within the learned pattern.";
  document.querySelector("#prediction").textContent = formatNumber(analysis.prediction);
  document.querySelector("#error").textContent = formatNumber(analysis.error);
  responseBox.textContent = "Measurement stored in RedisTimeSeries.";
  renderChart(data.measurements);
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
  responseBox.textContent = "Analyzing…";

  try {
    const response = await fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value: valueInput.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not analyze the measurement.");
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
  document.querySelector("#verdict-label").textContent = "No analysis yet";
  document.querySelector("#verdict-value").textContent = "—";
  document.querySelector("#verdict-detail").textContent = "The result will appear here.";
  document.querySelector("#prediction").textContent = "—";
  document.querySelector("#error").textContent = "—";
  responseBox.textContent = "Test reset.";
  renderChart([]);
});

loadMeasurements();
window.addEventListener("resize", () => renderChart(lastMeasurements));
