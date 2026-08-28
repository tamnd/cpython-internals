# Lessons

Each lesson is a notebook you can run. There is nothing to install and nothing to build: open the Colab badge at the top of a lesson and the first cell fetches what it needs.

| Lesson | What you come away with | Run it |
| --- | --- | --- |
| [Z01. C for people who will only ever read C](z01-reading-c/z01.ipynb) | What a pointer and a struct really are, the seven house style idioms that make CPython's C look foreign, new versus borrowed versus stolen references, and the list growth formula transcribed into Python and checked two thousand times | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/z01-reading-c/z01.ipynb) |
| [Z02. How to be lost productively](z02-being-lost/z02.ipynb) | The rule that spots the third of CPython's C that a script wrote, a map of the tree small enough to remember, the naming rule that finds the C behind any standard library module, and how to trace a strange line back to the issue that explains it | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/z02-being-lost/z02.ipynb) |
| [T01. One line, seven stages](t01-one-line-seven-stages/t01.ipynb) | Where `answer = 6 * 7` goes between the file and the answer, and which CPython source file does each step | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t01-one-line-seven-stages/t01.ipynb) |
| [T02. Text becomes tokens](t02-text-becomes-tokens/t02.ipynb) | How indentation actually works, why the tokenizer has never heard of keywords, and what an f-string really is | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t02-text-becomes-tokens/t02.ipynb) |
| [T03. Tokens become a tree](t03-tokens-become-a-tree/t03.ipynb) | What the tree keeps about your file and what it throws away, why every node class knows its own declaration, and a round trip checked against your whole standard library | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t03-tokens-become-a-tree/t03.ipynb) |
| [T04. Names get scopes](t04-names-get-scopes/t04.ipynb) | Why two functions holding the identical line get different instructions, the five places a value can live, and how to read the decision out of a program you did not write | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t04-names-get-scopes/t04.ipynb) |
| [T05. The tree becomes bytecode](t05-the-tree-becomes-bytecode/t05.ipynb) | Where the multiplication in `6 * 7` goes, why some code you wrote never reaches the file, and the four numbers that decide how much work the compiler does ahead of time | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t05-the-tree-becomes-bytecode/t05.ipynb) |
| [T06. Reading bytecode fluently](t06-reading-bytecode-fluently/t06.ipynb) | The four things you need to read a disassembly without guessing, and a Python version of CPython's stack depth rule that agrees with it on every code object in the standard library | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t06-reading-bytecode-fluently/t06.ipynb) |
| [T07. The machine runs](t07-the-machine-runs/t07.ipynb) | The interpreter loop in four boxes, the three ways a build can reach a handler, why ninety thousand Python calls are fine and two thousand calls through `sorted` are not, and a stepper built on `sys.monitoring` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t07-the-machine-runs/t07.ipynb) |
| [T08. Everything is an object](t08-everything-is-an-object/t08.ipynb) | The object header, `id` and `type` and `getrefcount` and `getsizeof` and what each one refuses to tell you, the small integer cache measured rather than quoted, and the string interning rule that is fifteen lines of C | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t08-everything-is-an-object/t08.ipynb) |
| [T09. Memory appears and disappears](t09-memory-appears-and-disappears/t09.ipynb) | Watching an object die through a weak reference, building a cycle that outlives every name for it, the three step trick `Python/gc.c` uses to decide what is garbage, the three generations and why integers are not tracked, and the blocks and pools and arenas underneath all of it | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t09-memory-appears-and-disappears/t09.ipynb) |
| [T10. The napkin](t10-the-napkin/t10.ipynb) | Drawing the machine from memory and checking it, the boundary between compile time and run time and the one thing that crosses it, `answer = 6 * 7` through all eight stages in a single cell, and seven common claims settled by running them | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t10-the-napkin/t10.ipynb) |

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

## The pictures

A lesson that needs diagrams has a `diagrams.py` next to its `build.py`. It builds Excalidraw scenes from Python using [nbdiagram](../tools/nbdiagram) and writes each one out twice, as an `.excalidraw` you can open and edit and as the `.svg` the notebook points at. `just build-diagrams` redraws them and `just diagrams` fails when a committed file no longer matches the script.

The `build.py` then embeds one by name:

```python
figure = Diagrams("t02-text-becomes-tokens").figure

lesson.md(f"...{figure('where-a-tab-lands', 'a tab landing on a tab stop')}...")
```

The URL that produces is absolute rather than relative, because Colab has no idea which repository the notebook came from and a relative path would be a broken image for every reader who arrived through the badge. Asking for a diagram that has not been drawn yet is an error at build time rather than a broken image in the notebook.

Every lesson opens with the same map, the row of boxes from your file to the answer, with its own box lit up. That map is shared data in `nbdiagram.stages` rather than something each lesson lays out for itself, so it cannot drift apart between one lesson and the next.
