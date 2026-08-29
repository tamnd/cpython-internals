// Runs a lesson's code cells inside Pyodide, in order, in one namespace.
//
// The checks in driver.mjs ask whether a surface exists. This asks the question a reader
// actually cares about: does the lesson run. Same runtime, same reason for using Node, and
// one important difference. The checks are independent and get a fresh runtime whenever one
// takes the old one down. A lesson is not independent: cell nine uses what cell seven made,
// so a lesson runs start to finish in one runtime, and when the runtime dies the rest of
// that lesson is reported as never reached rather than retried in a new one.
//
// pyxray is not installed. It is mounted off the disk and put on the path, so this needs no
// network and no wheel, and it tests the source in the checkout rather than whatever is
// published. That is also why the install cell is skipped: it is there for Colab.
//
//   node lesson.mjs plan.json out.json

import { readFileSync, writeFileSync } from "node:fs";
import { loadPyodide } from "pyodide";

const [planPath, outPath] = process.argv.slice(2);
if (!planPath || !outPath) {
  console.error("usage: node lesson.mjs plan.json out.json");
  process.exit(2);
}

const plan = JSON.parse(readFileSync(planPath, "utf8"));
const lessons = [];
let python = "unknown";

// Every cell runs in this one dictionary, which is what makes a notebook a notebook. The
// output is captured on the Python side rather than through Pyodide's stdout handler,
// because that handler is global and would mix the cells together.
const SETUP = (paths) => `
import sys, io, json, contextlib, traceback
for __one__ in ${JSON.stringify(paths)}:
    if __one__ not in sys.path:
        sys.path.insert(0, __one__)
__cells__ = {"__name__": "__main__"}
`;

const CELL = (source, name) => `
__buf__ = io.StringIO()
try:
    with contextlib.redirect_stdout(__buf__), contextlib.redirect_stderr(__buf__):
        exec(compile(${JSON.stringify(source)}, ${JSON.stringify(name)}, "exec"), __cells__)
    __out__ = json.dumps({"status": "ok", "printed": __buf__.getvalue()})
except BaseException:
    __line__ = traceback.format_exc().strip().splitlines()[-1]
    __out__ = json.dumps({"status": "raised", "printed": __buf__.getvalue(), "error": __line__})
__out__
`;

async function boot() {
  const runtime = await loadPyodide({ stdout: () => {}, stderr: () => {} });
  // The checkout, read only, at the same place every time so a traceback in the recording
  // does not carry somebody's home directory in it.
  runtime.mountNodeFS("/repo", plan.root);
  runtime.runPython(SETUP(plan.paths.map((one) => "/repo/" + one)));
  return runtime;
}

const save = () =>
  writeFileSync(
    outPath,
    JSON.stringify({ runtime: "pyodide", python, lessons }, null, 2) + "\n",
    "utf8",
  );

for (const lesson of plan.lessons) {
  let runtime = await boot();
  python = runtime.runPython("import platform; platform.python_version()");
  const cells = [];
  lessons.push({ slug: lesson.slug, cells });
  save();
  let dead = false;
  for (const cell of lesson.cells) {
    if (dead) {
      cells.push({ name: cell.name, status: "skipped", error: "the runtime went down first" });
      continue;
    }
    // Written before the cell runs, so a crash that takes Node with it still leaves the
    // file naming the cell that did it.
    cells.push({ name: cell.name, status: "fatal", error: "the runtime did not come back" });
    save();
    let answer;
    try {
      answer = JSON.parse(runtime.runPython(CELL(cell.source, cell.name)));
    } catch (error) {
      // A Python exception is caught inside Python above, so anything arriving here took
      // the runtime with it. The rest of the lesson cannot run: it would be running in a
      // different interpreter than the cells above it.
      cells[cells.length - 1] = {
        name: cell.name,
        status: "fatal",
        error: String(error.message || error).split("\n")[0],
      };
      dead = true;
      save();
      continue;
    }
    cells[cells.length - 1] = { name: cell.name, ...answer };
    save();
  }
  runtime = null;
  save();
}

save();
