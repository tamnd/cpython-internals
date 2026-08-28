# nbcheck

Structural checks and execution for the lesson notebooks.

Every lesson in this repository ships as a notebook that a reader can open in Colab and run without installing anything first. That promise has a handful of preconditions, all of them easy to break by accident and none of them visible in a diff, so they are checked here rather than trusted.

## Using it

```
just notebooks      # lint every notebook under lessons/, then run every cell
nbcheck lint        # the structural checks on their own, fast, no kernel
nbcheck run         # execute every cell and fail on the first one that raises
```

`nbcheck lint` exits 0 when everything is fine, 1 when a notebook is wrong, and 2 when the command itself was used wrong. The difference between 1 and 2 is the point: a misused command must never be read by CI as a clean run.

## What it checks

The Colab badge is present, is the first thing in the file, and points at this notebook rather than at the one it was copied from. A badge that opens somebody else's notebook is worse than no badge, because the reader does not notice.

Something in the notebook installs pyxray from this repository. Colab does not have it, so a notebook without an install cell raises ImportError on the second cell, and a beginner reads that as the lesson being broken.

`pyxray.show()` runs within the first three code cells. Every observation in this material is build dependent, and a reader who does not know which binary produced a number will eventually see a result that contradicts the prose and conclude the prose is wrong.

Every code cell is preceded by a markdown cell. This is the rule that separates a lesson from a script with comments in it.

The kernel is a plain `python3`, which is the only one Colab offers. Every cell has an id, which nbformat has required since 4.5. No cell is empty. No cell has stored output or a leftover execution count, because committed output goes stale silently and there is no way for a reader to tell. No markdown cell contains an em dash or an en dash, which this project does not use in prose.

`nbcheck run` then executes the whole notebook in order and reports the first cell that raises, with the cell number and the line that was running. Nothing is written back to the file, so a successful run leaves no trace except an exit code.

## Why the rules live in code

Each one is a way a reader has actually been lost. Writing them down as a checklist in a contributing guide means they get checked when somebody remembers to, which is not often enough for the audience this material is written for. Writing them down here means the author finds out instead of the reader.
