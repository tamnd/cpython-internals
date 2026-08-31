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
| [B01. Building CPython](b01-building-cpython/b01.ipynb) | What your interpreter still remembers about the day it was compiled, three ways to have a CPython to poke at when only one of them is a compiler, which files in the tree nobody wrote, and the flag `sysconfig` is unable to see | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b01-building-cpython/b01.ipynb) |
| [B02. Watching the interpreter stop](b02-the-debugger/b02.ipynb) | A pdb session driven from a list of commands instead of a prompt, a debugger in four lines of `sys.settrace`, and two recorded gdb sessions showing the C stack and the Python stack of one stopped interpreter side by side | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b02-the-debugger/b02.ipynb) |
| [B03. Asking CPython whether it still works](b03-the-test-suite/b03.ipynb) | The test suite is unittest with bookkeeping on top, how to run one test instead of all of them, the twenty eight things a test is not allowed to leave changed, and a leak hunt on a real debug build | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b03-the-test-suite/b03.ipynb) |
| [B04. Reading the tree](b04-reading-the-tree/b04.ipynb) | Reading source without a checkout, an index of a file in nine lines, spotting a generated file, watching three lines added to bytecodes.c become an opcode number and a block of C, and going from a line to the issue that put it there | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b04-reading-the-tree/b04.ipynb) |
| [F01. The tokenizer, in C](f01-the-tokenizer-in-c/f01.ipynb) | The generated table the token numbers come out of, four constructors that differ in one function pointer, a recorded debug build showing the buffer holding one line at a time, the counter behind DEDENT tokens that all claim the same position, and the two places tokenizer error messages are written | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f01-the-tokenizer-in-c/f01.ipynb) |
| [F02. f-strings in the lexer](f02-f-strings-in-the-lexer/f02.ipynb) | Nine tokens where a plain string is one, the mode stack that makes nesting work and the two very different ceilings on it, a format spec that is an f-string in its own right, escape decoding that happens in the parser rather than the lexer, and the buffer of raw source text behind the equals sign and t-strings | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f02-f-strings-in-the-lexer/f02.ipynb) |
| [F03. The parser nobody wrote](f03-the-parser-nobody-wrote/f03.ipynb) | Where the 39486 lines of Parser/parser.c come from, why associativity is the shape of a rule rather than a table of precedences, how a soft keyword can be a variable name in the same file, and the 68 grammar rules whose only job is to write a better error message than invalid syntax | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f03-the-parser-nobody-wrote/f03.ipynb) |

## The three programs

Lessons do not invent a fresh example each time. There are three programs, they are fixed, and they live in `pyxray.programs` so that every lesson gets the same text rather than a retyped copy of it.

| | What it is | Why it exists |
| --- | --- | --- |
| `L0` | `answer = 6 * 7`, one line | Its bytecode, its tree and its symbol table all fit on the screen at once, so nothing in the program competes with the stage being explained. |
| `L1` | an iterative Fibonacci, six lines | The smallest program with a loop the interpreter notices. One call is enough to specialize the two instructions inside it, so the interpreter lessons can show that happening without asking you to run anything ten thousand times. |
| `L2` | a small linked structure, sixty lines | A class, a generator, a closure, a dict, a `try`/`except`/`finally`, and a reference cycle if you ask for one. Each of those is there because a later lesson points at it, and none of them is in there twice. |

The reason to reuse three programs rather than write a good example per lesson is that meeting a new program and a new subsystem at the same time is two jobs, and the one most readers drop is the subsystem. By the time the exception table turns up, you should already know what `L2` does well enough to spend all of your attention on the table.

```python
from pyxray import programs

print(programs.L1.describe())
print(programs.L1.run())  # 832040
nodes = programs.L2.load()  # a fresh namespace every time, nothing cached
first = nodes.chain(("a", "b", "c"), ring=True)
```

## The claim ledger

[CLAIMS.md](CLAIMS.md) lists every behavioural claim the lessons make and the cell that proves it. It is generated, and `just claims` fails when a claim has lost its evidence.

An author marks a claim where they make it, and the sentence comes back unchanged, so the prose reads the same and the reader sees nothing:

```python
lesson.md(f"""
{lesson.claim("the 42 is not in the constants table")}. It is the argument byte of the instruction itself.
""")
```

The evidence is the next code cell, and it has to come before the next section heading. That second half is the part that makes it mean something: without it every claim in a lesson would find some cell further down and the check would pass on a lesson that proves nothing.

A few true things cannot be shown from Python at all, like the shape of the graph the optimizer builds, which is made and thrown away inside the compiler. Those are marked with the reason they cannot be shown, and a lesson gets at most three.

## The glossary

There is one definition per term and it lives in [GLOSSARY.md](../GLOSSARY.md). A lesson uses a word and links to it rather than stopping to explain it, which means you can follow a link when you need one and ignore it when you do not.

A builder writes `{lesson.term("code object")}` and gets a link into that file. Asking for a term nobody has defined fails while the lesson is being built, so a lesson cannot ship a link that lands at the top of the page and looks fine.

The file is generated from `pyxray/src/pyxray/glossary.py`, which is also where the definitions are edited. Run `just build-glossary` after changing them. Where a definition rests on something in CPython rather than on the language reference it carries a citation, and those are resolved against the pinned tree along with every other claim in the project.

## How a lesson is put together

Every code cell has a markdown cell in front of it saying what it is about to show. Every claim about CPython carries a reference to the source that makes it true, written as `Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault`, which is a file, a line range, a release tag and a function name. Those references are resolved against the pinned source tree on every change, so one that has gone stale fails the build rather than misleading you.

No notebook has its outputs committed. Every lesson is executed end to end in continuous integration on CPython 3.15.0rc1 and on 3.14 before it is merged, so the numbers you see are the ones your own interpreter produced rather than somebody else's screenshot. Where the two versions disagree the lesson says so and prints what your build did.

## The nine blocks

Every lesson is the same nine blocks in the same order, so a reader four lessons in knows where they are without looking:

1. A title and a hook under it, which is a question and something surprising the reader can run
2. About the source references, generated
3. Setup, generated, which installs the package and prints the build banner
4. Which Python is this, so the reader knows which interpreter produced everything below
5. The tour, which is the lesson itself and the only block whose headings are the author's to choose
6. Try it yourself, the exercises
7. Boss fight, when the lesson has one, so the reader has warmed up on the exercises first
8. What just happened, the recap
9. Where this goes next

`nbcheck blocks` checks all of that by heading, and it also checks that the tour has at least one picture in it. It prints three word counts for every lesson as it goes: the hook, the tour, and the whole lesson. The caps are 150, 2500 and 3500 words of prose, where prose means everything except code cells, code fences, images, HTML and the generated front matter, so a lesson cannot buy room by adding a diagram.

The first of those three is the number from the authoring guide and the other two are not. The guide asked for a 1500 word tour and a 2500 word lesson, and twelve lessons later nothing lands near that: the shortest tour is 1269 words and the median is over 2300. The caps are set where they bite on the longest lessons rather than where they would declare nine of twelve broken, and the reasoning is written out at the top of [blocks.py](../tools/nbcheck/src/nbcheck/blocks.py).

## How it is written

Plain English, aimed at somebody who has written Python and has never opened a C file. A sentence explains the subject rather than the lesson, so "this is the part that catches everybody out" is fine and "now the part that catches everybody out" is not, because the second one is building suspense about a paragraph the reader has not read yet.

Short dramatic fragments used as punctuation are the thing to watch for. A paragraph that ends on "There it is." or "Not once." or "Then it does not." is performing rather than explaining, and joining the fragment back into the sentence it was cut off from loses nothing. The same goes for the "not X, Y" shape: "These are not vague guidelines. They are exact." says less than "They are exact rather than rules of thumb."

Short sentences are fine when they carry something. The answer to a prediction cell, a fact like "an instruction is two bytes", and a line out of a quoted C comment all belong.

The mechanical rules are that there are no em dashes, no hard wrapping inside a paragraph, and no horizontal rules. A term links into the glossary the first time a lesson uses it and not after that. Exercise lists are numbered in bold, `**One.**` through `**Five.**`.

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
