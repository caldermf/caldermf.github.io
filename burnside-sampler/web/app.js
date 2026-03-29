const elements = {
  primeSlider: document.querySelector("#prime-slider"),
  primeDisplay: document.querySelector("#prime-display"),
  n: document.querySelector("#dimension-n"),
  steps: document.querySelector("#step-count"),
  seed: document.querySelector("#seed"),
  start: document.querySelector("#start-state"),
  randomizeStartButton: document.querySelector("#randomize-start-button"),
  initializeButton: document.querySelector("#initialize-button"),
  runButton: document.querySelector("#run-button"),
  stepButton: document.querySelector("#step-button"),
  resetButton: document.querySelector("#reset-button"),
  status: document.querySelector("#status-text"),
  history: document.querySelector("#history-strip"),
  topStates: document.querySelector("#top-states"),
  chart: document.querySelector("#distribution-chart"),
};

const worker = new Worker(new URL("./worker.mjs", import.meta.url), { type: "module" });

const PRIME_MAX = 7919;
const DEFAULT_PRIME = 733;

let workerReady = false;
let busy = false;
let latestSnapshot = null;
const cellMetadataCache = new Map();

function generatePrimes(limit) {
  const sieve = new Array(limit + 1).fill(true);
  sieve[0] = false;
  sieve[1] = false;
  for (let value = 2; value * value <= limit; value += 1) {
    if (!sieve[value]) {
      continue;
    }
    for (let multiple = value * value; multiple <= limit; multiple += value) {
      sieve[multiple] = false;
    }
  }
  return sieve.flatMap((isPrime, value) => (isPrime ? [value] : []));
}

const PRIMES = generatePrimes(PRIME_MAX);

function getSelectedPrime() {
  return PRIMES[Number(elements.primeSlider.value)];
}

function permutationLabel(permutation) {
  return `[${permutation.join(", ")}]`;
}

function permutationStateKey(permutation) {
  return permutation.join(",");
}

function parsePermutation(text, n) {
  const tokens = text
    .trim()
    .split(/[\s,]+/)
    .filter(Boolean)
    .map((value) => Number(value));

  if (tokens.length === 0) {
    return Array.from({ length: n }, (_, index) => index + 1);
  }
  if (tokens.length !== n) {
    throw new Error(`Start permutation must contain exactly ${n} entries.`);
  }
  const sorted = [...tokens].sort((left, right) => left - right);
  const target = Array.from({ length: n }, (_, index) => index + 1);
  if (!sorted.every((value, index) => value === target[index])) {
    throw new Error(`Start permutation must be a rearrangement of 1 through ${n}.`);
  }
  return tokens;
}

function setStatus(message) {
  elements.status.textContent = message;
}

function updatePrimeDisplay() {
  elements.primeDisplay.textContent = String(getSelectedPrime());
}

function setBusy(nextBusy) {
  busy = nextBusy;
  const controlsDisabled = nextBusy || !workerReady;
  for (const control of [
    elements.n,
    elements.steps,
    elements.seed,
    elements.start,
    elements.primeSlider,
    elements.randomizeStartButton,
    elements.initializeButton,
    elements.runButton,
    elements.stepButton,
    elements.resetButton,
  ]) {
    control.disabled = controlsDisabled;
  }
}

function postWorkerMessage(message, statusText) {
  setBusy(true);
  setStatus(statusText);
  worker.postMessage(message);
}

function initializePrimeSlider() {
  elements.primeSlider.min = "0";
  elements.primeSlider.max = String(PRIMES.length - 1);
  const defaultIndex = Math.max(0, PRIMES.indexOf(DEFAULT_PRIME));
  elements.primeSlider.value = String(defaultIndex);
  updatePrimeDisplay();
}

function createPermutationOrder(n) {
  const values = Array.from({ length: n }, (_, index) => index + 1);
  const permutations = [];

  function recurse(prefix, remaining) {
    if (remaining.length === 0) {
      permutations.push(prefix);
      return;
    }
    for (let index = 0; index < remaining.length; index += 1) {
      recurse(
        [...prefix, remaining[index]],
        [...remaining.slice(0, index), ...remaining.slice(index + 1)],
      );
    }
  }

  recurse([], values);
  return permutations;
}

const permutationOrderCache = new Map();

function getPermutationOrder(n) {
  if (!permutationOrderCache.has(n)) {
    permutationOrderCache.set(n, createPermutationOrder(n));
  }
  return permutationOrderCache.get(n);
}

function randomPermutation(n) {
  const permutation = Array.from({ length: n }, (_, index) => index + 1);
  for (let index = permutation.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [permutation[index], permutation[swapIndex]] = [permutation[swapIndex], permutation[index]];
  }
  return permutation;
}

function setStartPermutation(permutation) {
  elements.start.value = permutation.join(" ");
}

function setRandomStart() {
  const n = Number(elements.n.value);
  if (!Number.isInteger(n) || n < 2 || n > 7) {
    return;
  }
  setStartPermutation(randomPermutation(n));
}

function hashString(text) {
  let hash = 0;
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash * 33 + text.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function buildCellStyle(cellKey, index) {
  const hash = hashString(cellKey);
  const hue = (index * 137.508 + (hash % 31)) % 360;
  const saturation = 54 + (hash % 4) * 7;
  const lightness = 35 + (Math.floor(hash / 5) % 4) * 7;
  return {
    solid: `hsl(${hue.toFixed(1)}, ${saturation}%, ${lightness}%)`,
    faint: `hsla(${hue.toFixed(1)}, ${Math.max(46, saturation - 8)}%, ${Math.min(82, lightness + 24)}%, 0.34)`,
  };
}

function cacheCellMetadata(n, cellKeys) {
  const permutations = getPermutationOrder(n);
  if (!Array.isArray(cellKeys) || cellKeys.length !== permutations.length) {
    return null;
  }

  const uniqueKeys = [...new Set(cellKeys)].sort();
  const palette = new Map();
  uniqueKeys.forEach((cellKey, index) => {
    palette.set(cellKey, buildCellStyle(cellKey, index));
  });

  const byState = new Map();
  permutations.forEach((permutation, index) => {
    const cellKey = cellKeys[index];
    byState.set(permutationStateKey(permutation), {
      cellKey,
      style: palette.get(cellKey),
    });
  });

  const metadata = { n, cellKeys, palette, byState };
  cellMetadataCache.set(n, metadata);
  return metadata;
}

function getCellMetadata(n) {
  return cellMetadataCache.get(n) ?? null;
}

function drawChart(snapshot) {
  const canvas = elements.chart;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(360, Math.floor(rect.width * dpr));
  const height = Math.max(260, Math.floor(rect.height * dpr));
  canvas.width = width;
  canvas.height = height;

  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);

  const cssWidth = width / dpr;
  const cssHeight = height / dpr;
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  ctx.fillStyle = "#faf7f0";
  ctx.fillRect(0, 0, cssWidth, cssHeight);

  const counts = snapshot?.histogramCounts ?? [];
  const n = snapshot?.n ?? Number(elements.n.value);
  const permutations = getPermutationOrder(n);
  const metadata = getCellMetadata(n);
  const margin = { top: 28, right: 20, bottom: 76, left: 58 };
  const chartWidth = cssWidth - margin.left - margin.right;
  const chartHeight = cssHeight - margin.top - margin.bottom;
  const baselineY = margin.top + chartHeight;
  const stateCount = Math.max(1, counts.length || permutations.length);
  const maxCount = Math.max(1, ...counts, 0);

  ctx.strokeStyle = "rgba(31, 38, 34, 0.1)";
  ctx.lineWidth = 1;
  for (let tick = 0; tick <= 4; tick += 1) {
    const y = margin.top + (chartHeight * tick) / 4;
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(margin.left + chartWidth, y);
    ctx.stroke();
    const value = Math.round(maxCount * (1 - tick / 4));
    ctx.fillStyle = "#5b645d";
    ctx.font = '11px "IBM Plex Mono"';
    ctx.fillText(String(value), 10, y + 4);
  }

  ctx.strokeStyle = "#1f2622";
  ctx.beginPath();
  ctx.moveTo(margin.left, baselineY);
  ctx.lineTo(margin.left + chartWidth, baselineY);
  ctx.stroke();

  const slotWidth = chartWidth / stateCount;
  const barWidth = Math.max(1, slotWidth - 0.25);
  for (let index = 0; index < stateCount; index += 1) {
    const x = margin.left + index * slotWidth;
    const faintFill = metadata?.palette.get(metadata.cellKeys[index])?.faint ?? "rgba(35, 75, 57, 0.12)";
    ctx.fillStyle = faintFill;
    ctx.fillRect(x, baselineY, barWidth, 1);
  }

  counts.forEach((count, index) => {
    if (count <= 0) {
      return;
    }
    const x = margin.left + index * slotWidth;
    const barHeight = (count / maxCount) * chartHeight;
    const solidFill = metadata?.palette.get(metadata.cellKeys[index])?.solid ?? "#234b39";
    ctx.fillStyle = solidFill;
    ctx.fillRect(x, baselineY - barHeight, barWidth, barHeight);
  });

  const tickCount = Math.min(8, permutations.length);
  ctx.fillStyle = "#5b645d";
  ctx.font = '11px "IBM Plex Mono"';
  for (let tick = 0; tick < tickCount; tick += 1) {
    const index = tickCount === 1
      ? 0
      : Math.round((tick * (permutations.length - 1)) / (tickCount - 1));
    const x = margin.left + index * slotWidth;
    ctx.beginPath();
    ctx.moveTo(x, baselineY);
    ctx.lineTo(x, baselineY + 6);
    ctx.strokeStyle = "rgba(31, 38, 34, 0.22)";
    ctx.stroke();

    ctx.save();
    ctx.translate(x + 4, baselineY + 18);
    ctx.rotate(-Math.PI / 5);
    ctx.textAlign = "right";
    ctx.fillText(permutationLabel(permutations[index]), 0, 0);
    ctx.restore();
  }

  ctx.fillStyle = "#5b645d";
  ctx.font = '12px "IBM Plex Mono"';
  ctx.fillText("Permutations in lexicographic order", margin.left, cssHeight - 12);
}

function renderTopStates(snapshot) {
  const rows = snapshot.topStates ?? [];
  const metadata = getCellMetadata(snapshot.n);
  if (rows.length === 0) {
    elements.topStates.innerHTML = '<div class="empty-state">No visit counts yet.</div>';
    return;
  }

  const body = rows
    .map((entry, index) => {
      const stateMetadata = metadata?.byState.get(permutationStateKey(entry.permutation)) ?? null;
      const swatch = stateMetadata?.style?.solid ?? "rgba(35, 75, 57, 0.24)";
      const title = stateMetadata?.cellKey
        ? `Right Steinberg cell P=${stateMetadata.cellKey.replace(/\|/g, " / ")}`
        : "Right Steinberg cell";
      return `
        <tr>
          <td class="mono">${index + 1}</td>
          <td class="mono permutation-cell">
            <span class="cell-swatch" style="background:${swatch}" title="${title}"></span>
            ${permutationLabel(entry.permutation)}
          </td>
          <td class="mono">${entry.count}</td>
        </tr>`;
    })
    .join("");

  elements.topStates.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Permutation</th>
          <th>Visits</th>
        </tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  `;
}

function renderHistory(snapshot) {
  const history = snapshot.history ?? [];
  if (history.length === 0) {
    elements.history.innerHTML = '<div class="empty-state">No trajectory yet.</div>';
    return;
  }

  elements.history.innerHTML = history
    .map((state) => `<span class="history-pill">${permutationLabel(state)}</span>`)
    .join("");
}

function renderSnapshot(snapshot) {
  if (snapshot.cellKeys) {
    cacheCellMetadata(snapshot.n, snapshot.cellKeys);
  }
  latestSnapshot = snapshot;
  renderHistory(snapshot);
  renderTopStates(snapshot);
  drawChart(snapshot);
}

function readControls() {
  const n = Number(elements.n.value);
  const q = getSelectedPrime();
  const steps = Number(elements.steps.value);
  const seed = elements.seed.value === "" ? null : Number(elements.seed.value);
  const start = parsePermutation(elements.start.value, n);

  if (!Number.isInteger(n) || n < 2 || n > 7) {
    throw new Error("n must be between 2 and 7 for the browser view.");
  }
  if (!Number.isInteger(steps) || steps < 1) {
    throw new Error("Steps must be a positive integer.");
  }
  if (seed !== null && !Number.isInteger(seed)) {
    throw new Error("Seed must be an integer.");
  }

  return { q, n, steps, seed, start };
}

function initializeSession() {
  const controls = readControls();
  postWorkerMessage(
    { type: "init", ...controls },
    `Initializing q=${controls.q}, n=${controls.n}…`,
  );
}

function reinitializeFromControls() {
  if (!workerReady || busy) {
    return;
  }
  try {
    initializeSession();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
}

function resetIdentity() {
  const n = Number(elements.n.value);
  const start = Array.from({ length: n }, (_, index) => index + 1);
  setStartPermutation(start);
  if (!workerReady) {
    return;
  }
  postWorkerMessage({ type: "reset", start }, "Resetting to the identity permutation…");
}

worker.addEventListener("message", (event) => {
  const { type, payload, message } = event.data ?? {};

  if (type === "ready") {
    workerReady = true;
    setBusy(false);
    setStatus(message);
    initializeSession();
    return;
  }

  if (type === "snapshot") {
    renderSnapshot(payload);
    setBusy(false);
    setStatus(message);
    return;
  }

  if (type === "error") {
    setBusy(false);
    setStatus(`Error: ${message}`);
  }
});

worker.addEventListener("error", (event) => {
  setBusy(false);
  const location = event.filename ? ` (${event.filename}:${event.lineno ?? 0})` : "";
  setStatus(`Worker failed to load${location}. Check network access to Pyodide.`);
});

worker.addEventListener("messageerror", () => {
  setBusy(false);
  setStatus("Worker message failed to deserialize.");
});

elements.initializeButton.addEventListener("click", () => {
  try {
    initializeSession();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
});

elements.runButton.addEventListener("click", () => {
  try {
    const controls = readControls();
    postWorkerMessage({ type: "run", steps: controls.steps }, `Running ${controls.steps} steps…`);
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
});

elements.stepButton.addEventListener("click", () => {
  postWorkerMessage({ type: "step" }, "Advancing one step…");
});

elements.resetButton.addEventListener("click", () => {
  try {
    resetIdentity();
  } catch (error) {
    setStatus(error instanceof Error ? error.message : String(error));
  }
});

elements.randomizeStartButton.addEventListener("click", () => {
  setRandomStart();
  reinitializeFromControls();
});

elements.n.addEventListener("change", () => {
  const n = Number(elements.n.value);
  if (Number.isInteger(n) && n >= 2 && n <= 7) {
    setRandomStart();
    reinitializeFromControls();
  }
});

elements.primeSlider.addEventListener("input", () => {
  updatePrimeDisplay();
});

elements.primeSlider.addEventListener("change", () => {
  reinitializeFromControls();
});

elements.seed.addEventListener("change", () => {
  reinitializeFromControls();
});

elements.start.addEventListener("change", () => {
  reinitializeFromControls();
});

window.addEventListener("resize", () => {
  if (latestSnapshot) {
    drawChart(latestSnapshot);
  }
});

initializePrimeSlider();
setRandomStart();
drawChart({
  n: Number(elements.n.value),
  histogramCounts: new Array(getPermutationOrder(Number(elements.n.value)).length).fill(0),
});
setBusy(true);
