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

## Filing things

Bugs and enhancements get a `kind/` label, a `priority/` label and an `area/` label. If a lesson turns out to be wrong after it ships, that is a `kind/bug` at `priority/p0` and it goes on the errata page with a date, in place, rather than being quietly patched. A reader who learned the wrong thing needs to be able to find out that they did.
