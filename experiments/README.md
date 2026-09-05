# Experiments that need a different interpreter

Nearly everything in the lessons is Tier 0: open the notebook, run the cell, watch it happen on whatever Python you already have. That is the default and it is worth defending, because an experiment a reader cannot run is a paragraph with numbers in it.

A few questions do not fit. Counting every reference in the process needs an interpreter configured with `--with-pydebug`, and that is a different binary rather than a flag you can turn on. Telling a beginner to compile CPython before lesson five is telling them to stop reading.

So those programs run somewhere else. They run in the images this project publishes, pinned by digest in `images/cpython.lock.json`, and what each one printed is committed here and shown in the lesson it belongs to. The reader gets the program and the numbers. Anybody who wants to check gets one `docker run` and the same digest.

## What is here

| Recording | Lesson | Build | Question |
|---|---|---|---|
| [t05-compiling-costs-nothing-that-lasts](tier1/t05-compiling-costs-nothing-that-lasts.md) | T05 | debug | Does compiling the same line over and over leave anything behind? |
| [b03-a-leak-you-can-see](tier1/b03-a-leak-you-can-see.md) | B03 | debug | What does it look like when the test suite catches a reference leak? |
| [b04-what-a-script-wrote](tier1/b04-what-a-script-wrote.md) | B04 | debug | How much of the C in CPython was written by a script rather than by a person? |
| [b04-changing-the-source-of-truth](tier1/b04-changing-the-source-of-truth.md) | B04 | debug | What happens to the generated C when you add an instruction to Python/bytecodes.c? |
| [f01-one-line-at-a-time](tier1/f01-one-line-at-a-time.md) | F01 | debug | How much of your file is in the tokenizer's memory while it is being read? |
| [f03-a-parser-nobody-wrote](tier1/f03-a-parser-nobody-wrote.md) | F03 | debug | What does the parser generator actually do, and what does it write? |
| [m06-the-count-that-is-not-there](tier1/m06-the-count-that-is-not-there.md) | M06 | freethreaded | What does sys.getrefcount return for an object the interpreter has stopped counting? |
| [m06-one-count-each-way](tier1/m06-one-count-each-way.md) | M06 | freethreaded | Where does a reference go when the thread taking it is not the one that made the object? |
| [m08-no-lists-to-be-in](tier1/m08-no-lists-to-be-in.md) | M08 | freethreaded | Which generation is an object in on a build that does not keep generation lists? |
| [m08-the-count-another-thread-cannot-see](tier1/m08-the-count-another-thread-cannot-see.md) | M08 | freethreaded | How stale is the collector's count when another thread is the one doing the allocating? |
| [m08-nothing-runs-while-it-walks](tier1/m08-nothing-runs-while-it-walks.md) | M08 | freethreaded | How much time does a thread with no interest in the collector lose to a collection? |
| [c01-the-same-work-without-the-lock](tier1/c01-the-same-work-without-the-lock.md) | C01 | freethreaded | What does the same two thread benchmark do when there is no lock to take? |
| [c01-nothing-to-wait-for](tier1/c01-nothing-to-wait-for.md) | C01 | freethreaded | How much does another thread get done during one long C call when there is no GIL? |
| [c02-one-lock-each-or-one-between-them](tier1/c02-one-lock-each-or-one-between-them.md) | C02 | freethreaded | Does a lock in every object mean four threads with four lists go faster than four threads with one? |
| [c02-the-lock-switched-back-on](tier1/c02-the-lock-switched-back-on.md) | C02 | freethreaded | What happens to a racing counter when the same free threaded binary is started with the lock back on? |
| [c03-the-daemon-that-never-came-back](tier1/c03-the-daemon-that-never-came-back.md) | C03 | freethreaded | Does a daemon thread still get hung at shutdown on a build that has no lock to hang it with? |
| [c04-four-cores-with-the-lock](tier1/c04-four-cores-with-the-lock.md) | C04 | release | How much does giving each job its own interpreter buy on a build that has a GIL? |
| [c04-four-cores-without-the-lock](tier1/c04-four-cores-without-the-lock.md) | C04 | freethreaded | Does giving each job its own interpreter still buy anything once there is no GIL? |
| [c05-the-message-that-waited](tier1/c05-the-message-that-waited.md) | C05 | release | How late can an injected script be when the target never reaches a periodic check? |
| [c05-the-same-message-without-the-lock](tier1/c05-the-same-message-without-the-lock.md) | C05 | freethreaded | Does taking the GIL away change how late an injected script can be? |
| [c06-reading-what-nobody-counts](tier1/c06-reading-what-nobody-counts.md) | C06 | freethreaded | Does taking the lock away make reads scale, or does it depend on what is being read? |
| [c06-the-same-two-lists-with-the-lock](tier1/c06-the-same-two-lists-with-the-lock.md) | C06 | release | Do the two lists behave differently on a build where the threads take turns anyway? |
| [c07-what-one-thread-pays](tier1/c07-what-one-thread-pays.md) | C07 | freethreaded | What does a build with no GIL charge a program that only ever has one thread? |
| [c07-what-one-thread-pays-with-the-lock](tier1/c07-what-one-thread-pays-with-the-lock.md) | C07 | release | What do the same eight workloads cost on a build that kept the lock? |
| [c08-three-ways-to-split-the-work](tier1/c08-three-ways-to-split-the-work.md) | C08 | release | Does handing work to another interpreter pay, and what decides whether it does? |
| [c08-three-ways-without-the-lock](tier1/c08-three-ways-without-the-lock.md) | C08 | freethreaded | Once plain threads run in parallel too, is there anything left for interpreters? |
| [r01-what-startup-costs](tier1/r01-what-startup-costs.md) | R01 | release | How much is already loaded before your program starts, and how long did that take? |
| [r01-what-startup-costs-on-a-debug-build](tier1/r01-what-startup-costs-on-a-debug-build.md) | R01 | debug | Does a debug build do more work at startup, or the same work more slowly? |

## The commands

```
uv run tier1 list       every experiment and the build it needs
uv run tier1 show SLUG  the recording, as the lesson shows it
just tier1              the offline checks, which is what `just check` runs
just build-tier1        run them in the image and rewrite the recordings
just verify-tier1       run them and compare, writing nothing, which is what CI does
```

The first three need nothing and take milliseconds. The last two need Docker and a couple of hundred megabytes of image on a cold cache.

## What is checked, and what is not

The offline check asks whether the recording still belongs to the experiment above it, whether it came from the image this project pins today, and whether the lesson it was written for actually shows it. That last one is not a formality: a recording nobody shows passes everything else and teaches nobody anything, and it is the state this directory decays into if left alone.

The Docker check runs the programs again and compares. Not byte for byte, though. A line that starts with `~` is a measurement, and its number is compared by nobody, only its label. That is not a shortcut around a flaky test. Taking the measurement is itself Python: the collector runs, an f-string gets built, a few objects are made and dropped, so the same count taken twice in a row does not come back the same. A check that demanded byte equality of a number like that would go red once a fortnight for no reason, and what happens next is somebody deletes the check.

The assertion that would catch a real regression is inside the program instead, where it runs against a live interpreter every time CI does. The T05 one says that two thousand compiles must not move the total by fifty. If every compile kept one object it would move it by two thousand.

## Adding one

Put an `Experiment` in `tools/tier1/src/tier1/experiments.py`. It has to say what it asks in one sentence, and why a stock interpreter cannot answer it. That second field is the entry fee rather than documentation: if the honest answer is that a stock interpreter could answer it fine, the experiment belongs in the lesson as a cell the reader runs, where it is worth ten times as much.

Mark every line whose value is a measurement with a leading `~` and give it a label, then run `just build-tier1`, read the diff, show it in the lesson with `tier1.show`, and commit the recording with the code.
