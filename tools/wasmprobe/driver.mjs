// Runs the checks inside Pyodide, which is CPython built for WebAssembly.
//
// Node rather than a real browser because the WebAssembly is the same either way and a
// headless browser in CI is a second thing to keep working. The one thing this misses is
// the browser's own limits, which is why the boot time here is a floor rather than a
// promise.
//
// The awkward part, and the reason this is not four lines. A check can take the whole
// runtime down: `optimize_cfg` in the build shipping today does, with a memory access out
// of bounds, and after that every later check would look broken. So the checks run one at
// a time, a fatal error is recorded against the check that caused it, and the next check
// starts in a runtime that was booted fresh.
//
//   node driver.mjs checks.json out.json

import { readFileSync, statSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { loadPyodide } from "pyodide";

const [checksPath, outPath] = process.argv.slice(2);
if (!checksPath || !outPath) {
  console.error("usage: node driver.mjs checks.json out.json");
  process.exit(2);
}

const checks = JSON.parse(readFileSync(checksPath, "utf8"));
const outcomes = [];
let bootSeconds = 0;
let python = "unknown";

// What a browser has to fetch before the first cell can run. Node reads these off the
// disk, so the boot time above is far better than a real one, and this number is the part
// that decides whether somebody on a phone waits or closes the tab.
function payloadBytes() {
  const require = createRequire(import.meta.url);
  const home = dirname(require.resolve("pyodide"));
  const needed = ["pyodide.asm.wasm", "pyodide.asm.mjs", "python_stdlib.zip", "pyodide-lock.json"];
  let total = 0;
  for (const name of needed) {
    try {
      total += statSync(join(home, name)).size;
    } catch {
      // A file that moved between Pyodide releases. Better an undercount than a crash.
    }
  }
  return total;
}

// The check's source leaves its answer in `result`. Doing the JSON encoding inside Python
// rather than handing the object across means a value Pyodide cannot convert, and there
// are several, shows up as a check that raised rather than as a driver that crashed.
const wrap = (source) => `
import json, traceback
__wasmprobe__ = {}
try:
    exec(${JSON.stringify(source)}, __wasmprobe__)
    __out__ = json.dumps({"status": "ok", "value": __wasmprobe__.get("result")}, default=str)
except BaseException:
    __line__ = traceback.format_exc().strip().splitlines()[-1]
    __out__ = json.dumps({"status": "raised", "error": __line__})
__out__
`;

async function boot() {
  const started = performance.now();
  const runtime = await loadPyodide({ stdout: () => {}, stderr: () => {} });
  const seconds = (performance.now() - started) / 1000;
  return { runtime, seconds };
}

let session = await boot();
bootSeconds = session.seconds;
python = session.runtime.runPython("import platform; platform.python_version()");

const save = () =>
  writeFileSync(
    outPath,
    JSON.stringify(
      {
        runtime: "pyodide",
        python,
        seconds: Number(bootSeconds.toFixed(3)),
        payload_bytes: payloadBytes(),
        outcomes,
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );

for (const check of checks) {
  // Written before the check runs, so a crash that takes the process out as well as the
  // runtime still leaves the file naming the check that did it.
  outcomes.push({ key: check.key, status: "fatal", error: "the runtime did not come back" });
  save();
  let answer;
  try {
    answer = JSON.parse(session.runtime.runPython(wrap(check.source)));
  } catch (error) {
    // A Python exception is caught inside Python above, so anything arriving here has
    // taken the runtime with it and the next check needs a new one.
    outcomes[outcomes.length - 1] = {
      key: check.key,
      status: "fatal",
      error: String(error.message || error).split("\n")[0],
    };
    save();
    session = await boot();
    continue;
  }
  outcomes[outcomes.length - 1] = { key: check.key, ...answer };
  save();
}

save();
