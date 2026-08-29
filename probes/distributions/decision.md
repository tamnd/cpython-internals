# What the front end lessons do about the Pythons that cannot run them

This is the written half of gate Q4. The measured half is `report.md` next to it, and the raw answers are in `answers.json`. Reproduce them with `just build-dist`, or run `uv run distprobe question` and paste what it prints into whatever Python you have.

## The short version

The teaching hook holds. Twelve channels, ten of them measured, and eight of those give a reader everything the compiler lessons need with nothing extra installed.

Two do not, and neither of them changes what the lessons are. One is fixed by installing a package, and the lessons now name that package in the error. The other is a Python from 2021 that nobody should be learning on, and the version banner already tells that reader to get a newer one.

## What was measured

Whether `_testinternalcapi` imports, and whether `compiler_codegen`, `optimize_cfg` and `assemble_code_object` are on it. Those three are what `pyxray.compiler.stages` calls, and they are what lets a beginner run CPython's compiler one stage at a time from a notebook without building anything.

The question is a self contained script that imports only `json`, `sys` and `sysconfig`, because it has to run on the interpreters where the answer is no. The container rows ran as `linux/arm64`, which is written into the recording, because a measurement that does not say what it measured cannot be checked later.

## The two that answered no

**Fedora's `python3` does not ship the module.** `dnf install python3` on `fedora:43` gives you CPython 3.14.7, which is newer than what Debian, Ubuntu, conda-forge or Homebrew hand out, and importing `_testinternalcapi` raises `ModuleNotFoundError`. That is the finding this gate existed to catch, and it is a surprise in the direction nobody would guess: the most up to date distribution on the list is the one that cannot run the lessons.

It is a packaging split rather than a build option. `dnf install python3 python3-test` puts the module back, all three functions included, on the same 3.14.7. The package that owns the shared object is `python3-test-3.14.7-1.fc43`.

So the fix is one line and the problem is that nobody knows to type it. `pyxray.compiler.Unavailable` now carries that line in its message, so the reader who hits the wall is told what to install rather than being told that a wall exists. The same sentence is in the contributing guide for anybody writing a new lesson.

**The macOS system Python has the module and none of the functions.** `/usr/bin/python3` on this machine is 3.9.6. `_testinternalcapi` imports, and the three functions are not on it, because they arrived in 3.12.

Nothing is done about this beyond what is already done. Every lesson opens with the `pyxray` build banner, which prints the version and says plainly when it is too old, and a reader on 3.9 will hit that in the first cell rather than four cells later in a compiler stage. This row is in the table because a beginner on a Mac types `python3` and gets it, so it is worth knowing that the failure is a missing attribute rather than a missing module, which is a much more confusing error to receive.

## The two that were not measured, and why they stay on the table

The python.org installers, macOS and Windows. Neither can be answered from here: the macOS package needs an administrator password to install, and the Windows one needs a Windows machine.

They stay in the table with a note saying what would answer them, because a table that quietly leaves out the rows nobody could reach looks complete when it is not. The macOS one has a method written down that does not need an install: fetch the `.pkg`, expand it with `pkgutil --expand-full`, and look for a `_testinternalcapi` shared object inside `Python_Framework.pkg`. That was started and abandoned when the download came down at about a megabyte a minute, so the method is recorded and the result is not, which is the honest way round.

Anybody with either machine can settle both rows in a minute with `uv run distprobe question`.

## What this changes

The front end lessons stay as they are. `_testinternalcapi` remains the hook they are built on, and no fallback tier is needed for it outside the browser.

Three things came out of it. The `Unavailable` message names the Fedora package, so the one reader in the table who is genuinely stuck is unstuck by the error itself. `just check` now reads this recording on every run, so a distribution that changes its mind shows up here rather than in somebody's issue. And the build lesson has a table to point at when it explains why a private test module is a reasonable thing to teach from.

## Where this could go wrong later

The module is private and has no compatibility promise, and that is the real risk rather than any single distribution. Two things would matter: upstream renaming or removing one of the three functions, and a distribution that ships the module today deciding to split it out the way Fedora has.

The first is caught by the citation checker and the version matrix, which run against the pinned tree. The second is only caught by asking again, so `just build-dist` is worth running when the pin moves. It takes half an hour and needs Docker, which is why it is not in `just check`.
