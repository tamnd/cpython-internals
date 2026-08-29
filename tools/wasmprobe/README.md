# wasmprobe

Asks a browser Python which of the surfaces this project needs actually work, and puts the answer next to the same question asked on a normal interpreter.

Every Tier 0 experiment in the lessons is meant to run in a browser tab with nothing installed. That rests on Pyodide, which is CPython compiled to WebAssembly by Emscripten, and on things like `_testinternalcapi`, `ctypes`, `sys.monitoring` and the cycle collector surviving that build. Most of them do. Not all of them, and the ones that do not are worth knowing about before a reader finds them.

## Running it

```
just build-probe
```

That records the checks twice and rewrites the report and the notebook. It needs `node` on PATH and `npm install` run once inside this directory, and it needs a 3.14 to use as the control, because Pyodide ships 3.14 and comparing it against a native 3.15 would report version differences as build differences.

```
just probe
```

That is the fast half, and the one in `just check`. It reads the two committed recordings, fails when a check the lessons depend on works natively and not in the browser, fails when the report or the notebook has fallen behind the checks, and then runs the notebook to make sure it still works.

## What is in here

`checks.py` is the list of questions. Each one is a string of Python rather than a function, because the same source has to run in two places and shipping the source is the only way to stop the two copies drifting. A check leaves its answer in a variable called `result`, must not print, and must not depend on any earlier check, because a check that takes the runtime down leaves the next one a brand new one.

Each check carries a weight. `tier0` means a lesson depends on it and a failure moves that experiment to Tier 1. `nice` means we want it and can live without it. `info` means the number is worth recording and nothing hangs on it. A `tier0` check can also carry an `accepted` sentence, which says we already know it fails in the browser and what we do instead. That keeps a known gap visible in the report without leaving the build permanently red, so the next regression is still noticeable.

`driver.mjs` is the Node side. It boots Pyodide, runs the checks one at a time, and when one takes the whole runtime down it records that against the right check and boots a fresh runtime for the next one. That is not hypothetical: handing `optimize_cfg` a constants list that is too short reads past the end of memory in this build, where a native interpreter raises a tidy `ValueError`.

`browser.py` drives that script and fills in a `skipped` outcome for anything the driver never reached. `native.py` runs the same checks here. `report.py` turns the two into the matrix. `notebook.py` writes the checks out as a notebook a reader can open in Colab or JupyterLite and run on their own runtime, which is the version of this that does not ask anybody to trust our recording.

## The results

They live in `probes/pyodide` at the top of the repository: `native.json`, `pyodide.json`, the rendered `report.md`, and `probe.ipynb`.

## Node, not a real browser

The WebAssembly is the same either way, and a headless browser in CI is another thing to keep working. What this does miss is the browser's own limits, so the boot time in the report is a floor rather than a promise, and anything about tab memory or a service worker is not answered here. The notebook exists to cover that gap: run it where you actually are.
