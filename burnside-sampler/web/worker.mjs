import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide.mjs";

const PYODIDE_VERSION = "0.29.3";
const INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

let pyodide = null;
let ready = false;

async function installPythonModule() {
  const moduleUrl = new URL("../burnside_sampler/pure_python.py", import.meta.url);
  const source = await fetch(moduleUrl).then((response) => {
    if (!response.ok) {
      throw new Error(`Could not load ${moduleUrl.href}`);
    }
    return response.text();
  });

  pyodide.FS.mkdirTree("/burnside_sampler");
  pyodide.FS.writeFile(
    "/burnside_sampler/__init__.py",
    "from .pure_python import PrimeFieldBurnsideSampler\n",
  );
  pyodide.FS.writeFile("/burnside_sampler/pure_python.py", source);

  await pyodide.runPythonAsync(`
import sys
sys.path.insert(0, "/")
`);
}

async function bootstrapBridge() {
  await pyodide.runPythonAsync(`
import itertools
import math
import random

from burnside_sampler.pure_python import PrimeFieldBurnsideSampler, right_steinberg_cell_key


class BrowserSession:
    def __init__(self, q, n, start=None, seed=None):
        self.q = int(q)
        self.n = int(n)
        self.seed = None if seed is None else int(seed)
        self.sampler = PrimeFieldBurnsideSampler(self.q)
        self.rng = random.Random(self.seed)
        self.all_states = list(itertools.permutations(range(1, self.n + 1)))
        self.cell_keys = {state: right_steinberg_cell_key(state) for state in self.all_states}
        self._identity = tuple(range(1, self.n + 1))
        self.current = tuple(start) if start is not None else self._identity
        self.history = [self.current]
        self.counts = {state: 0 for state in self.all_states}

    def _top_states(self, limit=24):
        ranked = sorted(self.counts.items(), key=lambda item: (-item[1], item[0]))
        return [
            {"permutation": list(state), "count": count}
            for state, count in ranked[:limit]
            if count > 0
        ]

    def _recent_history(self, limit=16):
        return [list(state) for state in self.history[-limit:]]

    def snapshot(self, include_metadata=False):
        data = {
            "q": self.q,
            "n": self.n,
            "seed": self.seed,
            "current": list(self.current),
            "steps": len(self.history) - 1,
            "visited": sum(1 for count in self.counts.values() if count > 0),
            "totalStates": math.factorial(self.n),
            "histogramCounts": [self.counts[state] for state in self.all_states],
            "topStates": self._top_states(),
            "history": self._recent_history(),
        }
        if include_metadata:
            data["cellKeys"] = [self.cell_keys[state] for state in self.all_states]
        return data

    def step(self):
        self.current = tuple(self.sampler.next_step(self.current, self.rng))
        self.history.append(self.current)
        self.counts[self.current] += 1
        return self.snapshot()

    def run(self, steps):
        total_steps = int(steps)
        if total_steps < 1:
            raise ValueError("Steps must be a positive integer.")
        for _ in range(total_steps):
            self.step()
        return self.snapshot()

    def reset(self, start=None):
        self.current = tuple(start) if start is not None else self._identity
        self.history = [self.current]
        self.counts = {state: 0 for state in self.all_states}
        return self.snapshot()


SESSION = None


def create_session(q, n, start=None, seed=None):
    global SESSION
    SESSION = BrowserSession(q, n, start, seed)
    return SESSION.snapshot(include_metadata=True)


def step_session():
    if SESSION is None:
        raise RuntimeError("The browser session is not initialized yet.")
    return SESSION.step()


def run_session(steps):
    if SESSION is None:
        raise RuntimeError("The browser session is not initialized yet.")
    return SESSION.run(steps)


def reset_session(start=None):
    if SESSION is None:
        raise RuntimeError("The browser session is not initialized yet.")
    return SESSION.reset(start)
`);
}

async function ensureReady() {
  if (ready) {
    return;
  }
  pyodide = await loadPyodide({ indexURL: INDEX_URL });
  await installPythonModule();
  await bootstrapBridge();
  ready = true;
}

async function callPython(name, ...args) {
  const fn = pyodide.globals.get(name);
  try {
    const result = fn(...args);
    const data = result.toJs({ dict_converter: Object.fromEntries });
    result.destroy?.();
    return data;
  } finally {
    fn.destroy?.();
  }
}

async function handleMessage(event) {
  try {
    await ensureReady();

    if (event.data?.type === "init") {
      const payload = await callPython(
        "create_session",
        event.data.q,
        event.data.n,
        event.data.start ?? null,
        event.data.seed ?? null,
      );
      self.postMessage({ type: "snapshot", payload, message: "Session initialized." });
      return;
    }

    if (event.data?.type === "step") {
      const payload = await callPython("step_session");
      self.postMessage({ type: "snapshot", payload, message: "Advanced one Burnside step." });
      return;
    }

    if (event.data?.type === "run") {
      const payload = await callPython("run_session", event.data.steps);
      self.postMessage({ type: "snapshot", payload, message: `Ran ${event.data.steps} steps.` });
      return;
    }

    if (event.data?.type === "reset") {
      const payload = await callPython("reset_session", event.data.start ?? null);
      self.postMessage({ type: "snapshot", payload, message: "Session reset." });
      return;
    }
  } catch (error) {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  }
}

self.addEventListener("message", handleMessage);

ensureReady()
  .then(() => {
    self.postMessage({
      type: "ready",
      message: `Pyodide ${PYODIDE_VERSION} loaded.`,
    });
  })
  .catch((error) => {
    self.postMessage({
      type: "error",
      message: error instanceof Error ? error.message : String(error),
    });
  });
