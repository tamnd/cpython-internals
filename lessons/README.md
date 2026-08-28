# Lessons

Each lesson is a notebook you can run. There is nothing to install and nothing to build: open the Colab badge at the top of a lesson and the first cell fetches what it needs.

| Lesson | What you come away with | Run it |
| --- | --- | --- |
| [T01. One line, seven stages](t01-one-line-seven-stages/t01.ipynb) | Where `answer = 6 * 7` goes between the file and the answer, and which CPython source file does each step | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t01-one-line-seven-stages/t01.ipynb) |
| [T02. Text becomes tokens](t02-text-becomes-tokens/t02.ipynb) | How indentation actually works, why the tokenizer has never heard of keywords, and what an f-string really is | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t02-text-becomes-tokens/t02.ipynb) |

## How a lesson is put together

Every code cell has a markdown cell in front of it saying what it is about to show. Every claim about CPython carries a reference to the source that makes it true, written as `Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault`, which is a file, a line range, a release tag and a function name. Those references are resolved against the pinned source tree on every change, so one that has gone stale fails the build rather than misleading you.

No notebook has its outputs committed. Every lesson is executed end to end in continuous integration on CPython 3.15.0rc1 and on 3.14 before it is merged, so the numbers you see are the ones your own interpreter produced rather than somebody else's screenshot. Where the two versions disagree the lesson says so and prints what your build did.

## Running them locally

```
just notebooks        # lint every notebook, then execute every cell
just notebooks-lint   # the structural checks only, no kernel, fast
```

Or open one in Jupyter, VS Code, or anything else that reads `.ipynb`. The first cell notices that the package is already installed and does nothing.

## Writing one

You do not edit the `.ipynb`. Each lesson is defined by the `build.py` next to it, which is ordinary Python with the prose in triple quoted strings, and the notebook is generated from that by [nbbuild](../tools/nbbuild). Run the builder to regenerate one, or `just build-lessons` for all of them. The generated notebook is committed too, because a reader clicking a Colab badge cannot run a build step first, and `just lessons` fails if the two have drifted apart.

The rules a lesson notebook has to follow are enforced by [nbcheck](../tools/nbcheck), and its README explains each of them and why it is there. The short version is that the Colab badge has to point at this notebook rather than the one it was copied from, the build banner has to run before anything it could explain, and no code cell appears without a sentence introducing it.
