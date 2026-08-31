# Debugger sessions somebody else already ran

Everything else in this project is something you run. This directory is the exception, and it is on purpose.

Watching a stopped interpreter needs three things a reader in a browser tab does not have: an interpreter built with `--with-pydebug`, a debugger, and the C source the debugger reads back to you. Asking for all three before lesson twelve is asking most people to stop reading. It is also the one thing in this material that genuinely cannot be faked in Pyodide, because there is no second process in a browser tab and nothing to attach to.

So the sessions ran here instead. They ran in the debug image this project publishes, pinned by digest in `images/cpython.lock.json`, and gdb's output is committed command by command with the line of explanation that belongs above each one. B02 lays them out in order with its own paragraphs in between, so you go through a session at the pace somebody at the prompt would have.

## What is here

| Transcript | Lesson | Build | Question |
|---|---|---|---|
| [b02-the-two-stacks](b02-the-two-stacks.arm64.md) | B02 | debug | What does a stopped interpreter look like from C, and from Python, at the same instant? |
| [b02-where-a-crash-came-from](b02-where-a-crash-came-from.arm64.md) | B02 | debug | When the interpreter segfaults, which line of Python was responsible? |

## The commands

```
uv run gdbrec list          every session and what it asks
uv run gdbrec show SLUG     one transcript, as the lesson shows it
just gdb                    the offline checks, which is what `just check` runs
just build-gdb              run them in the image and rewrite the transcripts
just verify-gdb             run them and compare, writing nothing, which is what CI does
```

The first three need nothing and take milliseconds. The last two need Docker, a few hundred megabytes of image on a cold cache, and a machine of the architecture you are recording.

## Why the filenames say an architecture

A backtrace is not portable. The same stopped program on arm64 and on amd64 disagrees about more than addresses: different frames survive the unwinder, arm64 marks pointer authenticated returns with `[PAC]`, and the shared library paths carry the target triple. You could scrub all of that out and compare what was left, but what is left after scrubbing that hard is thin enough for a real regression to hide in.

So a transcript belongs to one architecture, says so in its header, and is only ever compared against a run on that architecture. There is one file per architecture per session, and neither is the real one. If you are on a machine this project has no transcript for, `just build-gdb` will make one and it is welcome.

## What is checked, and what is not

The offline check asks whether the transcript still belongs to the session above it, whether the commands and the notes are still the ones in the catalogue, whether it came from the image this project pins today, and whether the lesson it was written for actually shows it. That last one is not a formality: a transcript nobody shows passes everything else and teaches nobody anything.

The Docker check runs the sessions again and compares, line by line, including how many lines each command printed. Addresses are allowed to move, because the kernel loads the program somewhere new every time, and so are process ids. Nothing else is. An address in a backtrace is there to show you that there is an address, not to be that particular address.

## Adding one

Put a `Session` in `tools/gdbrec/src/gdbrec/sessions.py`. It needs a program, a list of `Step`s, a one sentence question, and one sentence on why it needs the debug build rather than any Python you have lying around. That last field is the entry fee: gdb attaches to a release build perfectly well, so if the honest answer is that a release build shows the same thing, the session is not earning its image.

Every step carries the line of explanation that goes above its output. Write that at the same time as the command, not afterwards, because a command you cannot explain in one line is usually two commands.

Then run `just build-gdb`, read the diff, show it in the lesson with `gdbrec.show`, and commit the transcript with the code.
