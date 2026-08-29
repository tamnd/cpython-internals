# Contributing

## Getting set up

```
just setup     # install the workspace with uv
just vendor    # fetch CPython v3.15.0rc1, shallow and blobless, about 200 MB
just check     # lint, then tests, then citations
```

Every CI job is runnable locally under the same name it has in the workflow. If a check only exists in CI, contributors find out it failed after they pushed, and the two versions drift apart until nobody trusts either.

You need Python 3.15.0rc1 to run the test suite the way CI runs it. `uv python install 3.15.0rc1` gets you one. The suite also runs on 3.14, because Pyodide is a release behind and a lesson that only works on the pin is a lesson the browser tier cannot run.

## Citations

Every claim about CPython source points at a tagged region of the pinned tree, written as `Objects/listobject.c:1232@v3.15.0rc1#list_append_impl`. See `tools/refcheck/README.md` for the format and what gets checked.

Before you write a citation, run `just show <citation>` and read the lines. A citation nobody has looked at is a citation that is probably off by a few lines, and being off by a few lines is worse than having no citation, because it looks right.

When `just citations` reports `not-in-lock` for something you added, that is the tool asking a human to confirm it. Confirm it by eye, then run `just recheck` and commit the lockfile change alongside your prose.

## The two reviewer rule

Every lesson needs two approvals. One from somebody at or below the level of the reader we are writing for, and one from somebody at or above core developer level.

The beginner review answers four questions. Where did you get lost, what word was used before it was defined, what did you have to read twice, and could you do the boss fight.

The expert review answers four different ones. Is anything wrong, is anything stale against the pin, is any citation misleading, and does the blueprint actually specify the thing rather than describe it.

The beginner review is the one that gets skipped when there is a deadline. Skipping it is how this becomes a book by an expert for experts, which is the thing it exists not to be.

## Writing

The house style is in `spec/12-authoring-guide.md` once that lands. The short version:

Write to one reader who knows Python and has never seen a struct. Say the thing, then explain it, not the other way around. Never write "simply", "just", "obviously", "of course" or "trivially", because in this material somebody will find every single thing hard. Admit what is ugly, because CPython has thirty five years of history in it and saying "this is here for a bad reason, here is the issue" teaches more than pretending everything was designed.

Numbers come from scripts, never from memory. If a paragraph says the small integer cache holds 1030 values, that number is interpolated from generated output rather than typed by a person.

## The 3.14 and 3.15 problem

Everything here is written against the pinned 3.15. Every reader who clicks a Colab badge is on 3.14, and so is every widget that runs in the browser, because Pyodide has not shipped 3.15 yet. That gap is not going away before the first milestone does, so lessons have to be honest about it rather than wait for it.

`just versions` runs every lesson on both interpreters and compares the output of every cell. A cell whose output differs has to say so, and a cell that says so has to actually differ. Both halves are checked, because a note that has stopped being true is worse than no note: a reader who checks one against their own interpreter, finds it wrong, and decides the notes are decoration has been misled by the thing meant to help them.

Declaring a difference is one keyword in the lesson's `build.py`:

```python
lesson.code(
    source,
    differs="On 3.14 the last instruction is LOAD_CONST rather than LOAD_COMMON_CONSTANT, and None is in co_consts.",
)
```

Say what the reader is looking at and what the other version does instead. "This differs on 3.14" is not a note, it is an apology. Add `quiet=True` when a paragraph near the top of the lesson already explains a difference that then turns up in a dozen cells, so the same sentence is not repeated under every one of them.

There is a second keyword for the other kind of cell. `varies=` is for output that depends on the reader's machine rather than on the version: which flags their interpreter was configured with, how many files are in their standard library, how deep the C stack goes before it runs out. It reads exactly the same to a reader and the check treats it differently. A `differs` note is a claim two recordings can test, so it fails when it stops being true. A `varies` note is not, because whether two runs agree about a machine difference depends on which two machines made them, and a CI box where both interpreters came from the same builder would delete a note that is still right for somebody on a framework install. So `varies` is reported and never fails. Do not reach for it to silence a real version difference.

When the differing cell is the lesson's central observation, the note is not enough. Either the lesson gets a short section explaining both versions, because the difference is itself worth teaching, or the example changes to one that behaves the same on both. Which of the two depends on whether the difference is interesting. `LOAD_COMMON_CONSTANT` is interesting and gets explained. A line number inside `asyncio` is not, and the cell should stop printing it.

## What the browser can and cannot do

A Tier 0 experiment has to run in a browser tab with nothing installed. Which surfaces survive that is measured, not assumed, and the answer lives in [probes/pyodide](probes/pyodide): a matrix, the two raw runs behind it, a notebook you can open in Colab to ask your own runtime the same questions, and a written decision.

Read `decision.md` before writing an experiment that pokes at the interpreter. Three things are known to be different today. `compiler_codegen` returns no constants list there, so `pyxray.compiler.stages` builds one from the instruction sequence and tells you, through `constants_known`, that the optimizer was working without the real values: do not report a constant fold without checking it. Handing `optimize_cfg` a constants list that is too short reads past the end of memory and kills the runtime, where a native interpreter raises a tidy `ValueError`, so go through `pyxray.compiler` rather than building one yourself, and never catch this instead of preventing it. And a thread cannot be started.

If you need a surface nobody has measured, add a check to `tools/wasmprobe/src/wasmprobe/checks.py` and run `just build-probe`. A check is a string of Python that leaves its answer in `result`, and it has to import everything it uses, because the check before it may have taken the runtime down. Mark it `TIER0` if a lesson would depend on it, and `just probe` will fail the build the day it stops working. If it already fails and you have decided what to do instead, write that decision in the check's `accepted` field rather than deleting the check, so the gap stays in the report and the next regression is still visible.

The checks are a proxy, and next to them is the thing itself. `wasmprobe lessons` takes every lesson notebook, boots a fresh Pyodide runtime for it, and runs its code cells in order in one namespace, with pyxray mounted off the disk rather than installed. The result is `lessons.json` and `lessons.md`, and CI runs it on every pull request, so a lesson that stops working in a browser is caught the day it stops. The only thing rewritten before a cell runs is the `%pip` line in the install cell, which becomes `pass`. The rest of that cell still runs.

When a cell fails there, decide rather than delete. If it cannot work in a browser and you know why, write the reason in `ACCEPTED` in `tools/wasmprobe/src/wasmprobe/lessons.py`, keyed by cell id, and it stays in the report without stopping the build. Anything else stops the build. A cell that takes the runtime down takes the rest of its lesson with it, and those cells are not retried in a fresh runtime, because a cell that ran in a different interpreter than the cells above it has not been tested, it has been let off.

## What the reader's own Python can and cannot do

The browser is one place a lesson runs. The other is whatever Python the reader already has, and that is not one thing either. `_testinternalcapi` is a private test module, distributions are free not to ship it, and the compiler lessons stop working where it is missing. Twelve ways of getting a Python were asked, and the answers are in [probes/distributions](probes/distributions) with the same shape as the browser probe: a table, the raw answers, and a written decision.

The short version is that most channels ship it and Fedora's `python3` does not. If you are writing a lesson that imports it, import it through `pyxray.compiler` and let that raise the message that names the package to install, rather than writing your own `try` around the import. If you are adding a channel, put it in `tools/distprobe/src/distprobe/channels.py` and run `just build-dist`. A channel that this machine cannot reach still belongs on the list, with a note saying what would answer it, because a table that quietly leaves out the hard rows looks finished when it is not.

## What neither of them can do

A few questions need an interpreter that was built a particular way. Counting every reference in the process is the first one the lessons hit: `sys.gettotalrefcount` only exists in a build configured with `--with-pydebug`, and that is a different binary rather than a flag anybody can turn on afterwards. Telling a beginner to compile CPython before lesson five is telling them to stop reading.

That is what Tier 1 is for, and it lives in [experiments](experiments). The program runs in the image `cpybuild` publishes, pinned by digest, and what it printed is committed next to it and shown in the lesson. CI pulls the same digest, runs it again and compares, so the numbers in the lesson are checked against a real interpreter on every pull request rather than pasted in once.

Before you add one, answer the field that asks why a stock interpreter cannot do it. That is the entry fee rather than documentation. An experiment that could have run in the reader's own notebook is worth ten times as much there, and the honest answer is usually that it could.

Mark every line whose value is a measurement with a leading `~` and give it a label. Those lines are compared by their label and not their value, because taking a measurement is itself Python and the same count taken twice does not come back the same. Put the assertion that would catch a real regression inside the program, where it runs against a live interpreter every time CI does, rather than leaning on the committed numbers to catch it.

## Definition of done for a lesson

No partial credit on any of these.

1. Prose complete, within the length caps, both reviews signed off
2. Every behavioural claim backed by a runnable cell, with at most three marked unobservable
3. Every citation resolving with a matching digest
4. A Tier 0 experiment that runs in the browser, in CI
5. A Tier 1 experiment where the part expects one, with a recording generated in CI
6. A boss fight with a grader that CI runs against a known good and a known bad submission
7. The blueprint fragment complete for its declared status
8. A diagram or animation with alt text written by a person
9. Three beginner testers have completed it
10. Every cell whose output depends on the interpreter version declared, so `just versions` is green

## Filing things

Bugs and enhancements get a `kind/` label, a `priority/` label and an `area/` label. If a lesson turns out to be wrong after it ships, that is a `kind/bug` at `priority/p0` and it goes on the errata page with a date, in place, rather than being quietly patched. A reader who learned the wrong thing needs to be able to find out that they did.
