# nbbuild

Build the lesson notebooks from the Python files that define them.

A `.ipynb` is JSON with the prose stored as lists of strings with the newlines left on. That is fine for a machine and hostile to a human. Changing one word in a paragraph produces a diff nobody can read, every cell needs a unique id that is easy to duplicate by hand, and there is nowhere to put a comment saying why a cell is the way it is.

So the source of truth for every lesson is a `build.py` sitting next to it, and the notebook is generated from that. The notebook is still committed, because a reader clicking a Colab badge cannot run a build step first, and `nbbuild check` is what stops the two from drifting apart.

## Using it

```
just build-lessons   # regenerate every notebook from its builder
just lessons         # fail if a committed notebook no longer matches its builder
just build-claims    # rewrite the claim ledger at lessons/CLAIMS.md
just claims          # fail if a claim has no runnable cell behind it
```

Or run one builder on its own while you are writing, which is what you actually do most of the time:

```
python lessons/t02-text-becomes-tokens/build.py
python lessons/t02-text-becomes-tokens/build.py --check
```

Both exit 0 on success and 1 on failure, and `nbbuild` itself exits 2 when the command was used wrong. The difference between 1 and 2 is the point: a misused command must never be read by CI as a clean run.

## What a builder looks like

```python
from nbbuild import Lesson

lesson = Lesson("t02-text-becomes-tokens", "t02")
badge = lesson.badge
cite = lesson.cite

lesson.md(f"""
# T02. Text becomes tokens

{badge}

A Python file is a pile of characters.
""")

lesson.code("""
import pyxray
pyxray.show()
""")

raise SystemExit(lesson.save())
```

`slug` is the directory and `stem` is both the file name and the prefix on every cell id, so this one writes `lessons/t02-text-becomes-tokens/t02.ipynb` with cells `t02-01` upwards. Ids are counted rather than typed, which removes the whole class of mistake.

`lesson.badge` is built from the path the notebook is about to be written to. Copying the previous lesson and forgetting to change the badge link is the easiest mistake in this project, and generating it means it cannot happen at all.

`lesson.cite("Parser/lexer/lexer.c:1626-1635@v3.15.0rc1#_PyTokenizer_Get")` returns a markdown link built by the same parser `refcheck` validates citations with. A malformed citation therefore fails while you are building the lesson rather than in review, and there is never a second implementation of the URL format to go wrong.

## The claim ledger

The promise at the top of the project README is that nothing is asserted without an experiment. That is easy to write and easy to drift away from, because the sentence that quietly becomes untrue is never the one anybody was watching. So a lesson marks its behavioural claims where it makes them:

```python
lesson.md(f"""
{lesson.claim("the 42 is not in the constants table")}. It is the argument byte of the instruction itself.
""")
```

`claim` hands the sentence straight back, so the prose reads exactly as it would have and nothing shows up in the notebook. What it adds is a record and a rule: **the evidence is the next code cell, and it has to come before the next section heading.**

The second half is what makes the rule mean anything. Without it, every claim would find some code cell further down the lesson and the check would pass on a lesson that proves nothing. It also looks at headings inside the claim's own cell, because cells here often end with the heading that opens the next section, and a claim in the paragraph above one of those would otherwise borrow the next section's cell.

Claims are resolved by `Lesson.save`, in both `--build` and `--check`, rather than only when the ledger is rebuilt. A claim that lost its evidence has to fail where somebody is looking.

Some true things cannot be observed from Python: the layout of `PyObject`, what the allocator does with a freed block, the graph the optimizer builds and throws away. Those take the reason instead of a cell.

```python
lesson.claim(
    "the optimizer cuts the instruction list into basic blocks",
    unobservable="the graph is built, used and thrown away inside the compiler",
)
```

A lesson gets three of those. The cap is the point: without it the exception becomes the rule. It is `UNOBSERVABLE_CAP` in `claims.py` rather than a note in a style guide, so raising it is a visible decision somebody has to review.

`nbbuild claims` collects the ledger by running each builder with `--claims` and reading back JSON, in the same separate process the other commands use. Importing the builders would be less code and would mean a builder behaves differently under the command than it does when an author runs it directly.

## What it refuses

An empty cell, because nbformat allows one and a reader gains nothing from it.

An em dash or an en dash in prose. This project does not use either, and both are close enough to a hyphen that no human has ever caught one in review.

## Why the output is stable

`nbbuild check` compares the committed file to the text a fresh build produces, byte for byte, so anything unstable in the output would make CI fail at random. Keys are written in alphabetical order, which is what nbformat writes, so opening a lesson in Jupyter and saving it does not reorder the file. Code cells carry a null execution count and an empty output list, because outputs are never committed: the only proof a cell works is CI executing it, and a stored output is a screenshot that goes stale without telling anybody.
