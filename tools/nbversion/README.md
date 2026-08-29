# nbversion

Finds the lesson cells whose output depends on which Python is running, and checks that every one of them is declared. Run with `just versions`, which records the lessons twice and compares the two.

```
uv run nbversion record --into build/versions
uv run nbversion compare build/versions/3.15 build/versions/3.14
```

## Why this exists

The lessons are written against the pinned CPython 3.15. A reader who clicks the Colab badge is on whatever Google installed, which is 3.14, and so is every WASM widget, because Pyodide has not shipped 3.15 yet. Most cells do not notice. Some do, and those are the dangerous ones, because the cell still runs and still prints something that looks right.

The one that started this is `LOAD_COMMON_CONSTANT`. On 3.15 a function that falls off the end loads `None` with that instruction and `co_consts` does not contain `None` at all. On 3.14 it is a `LOAD_CONST` and `None` is in the table. A lesson that says "look, `co_consts` is `(6,)`" is teaching the reader to read their own screen wrong, and nothing about the cell says so.

So the lessons are executed on both interpreters and the outputs compared. Anything that differs has to carry a note.

## The two halves

`record` runs on one interpreter and writes a small JSON file per notebook: cell id to normalised output. It is not an executed notebook, because the diff of two executed notebooks is mostly metadata.

`compare` reads two of those directories and produces one of five verdicts per cell.

| verdict | what it means | fails |
| --- | --- | --- |
| `declared` | the cell differs and the notebook says so | no |
| `noted` | the cell's output depends on the machine, so there is nothing to check | no |
| `undeclared` | the cell differs and nothing says so | yes |
| `stale` | the cell carries a note and the two interpreters now agree | yes |
| `missing` | the two runs saw different sets of cells | yes |

`stale` is the half people forget. A note that has stopped being true is worse than no note: a reader who checks one against their own interpreter, finds it wrong, and concludes the notes are decoration has been misled by the thing that was supposed to help.

## Declaring a difference

In the lesson's `build.py`:

```python
lesson.code(
    "import dis\ndis.dis(compile('answer = 6 * 7', '<lesson>', 'exec'))\n",
    differs="On 3.14 the last instruction is LOAD_CONST rather than LOAD_COMMON_CONSTANT, and None is in co_consts.",
)
```

That writes the sentence into the cell's metadata, where `compare` looks for it, and adds a markdown cell underneath so a reader on Colab sees it without opening the metadata. Pass `quiet=True` to skip the visible cell, for the lessons where one paragraph near the top already covers a difference that a dozen cells then show. Repeating it under every one of them teaches people to skip the notes.

The metadata looks like this, and survives a round trip through Jupyter because it is on the cell rather than in a list somewhere else:

```json
"metadata": {"cpython_internals": {"differs": "On 3.14 ..."}}
```

`varies=` is the other keyword, for a cell whose output depends on the reader's machine rather than on the version: the flags their interpreter was built with, how many files their standard library has, how deep the C stack goes. It writes the same kind of note under a `varies` key, and it is the `noted` verdict above. Two recordings cannot check that kind of claim, because whether they agree depends on which two machines made them, and running the comparison on a CI box where both interpreters came from the same builder would call the note stale and delete something that is still true for a reader on a framework install.

## Normalising

Every substitution in `normalise.py` throws away a real difference, and the differences worth finding are exactly the ones a careless normaliser sweeps up. So a pattern gets normalised only when it varies between two runs of the *same* interpreter, which makes it noise rather than a version difference. That is addresses, absolute paths, temporary file names and durations, and nothing else. An opcode name, a size, a byte count and an offset all survive, because those are the point.

Errors keep the exception type and the message and lose the traceback. A lesson that raises on purpose cares about which exception it got, not about how many frames were on the stack.

## What it does not do

It does not decide what a lesson should say about a difference. It can tell you `co_consts` differs, and only a person can tell a reader why. It does not run the lessons on Pyodide, which is a separate question tracked in the issue this tool came from. And it does not replace `nbcheck run`, which is what fails when a cell raises by accident. `record` deliberately keeps going past an exception, so that one broken lesson cannot hide every version difference in the lessons after it.
