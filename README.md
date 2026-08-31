# cpython-internals

A complete teardown of CPython 3.15, taught from absolute zero, as reactive notebooks, animations and browser playgrounds. The same work produces a second artifact: a specification precise enough that you can rebuild a compatible Python from scratch in Go or Rust, with a conformance suite that tells you how far you got.

**Status: M0, in progress.** The tooling landed first, because a lesson written before there is anything to check it with is a lesson nobody can trust. The first lessons are up and you can [run them in Colab](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t01-one-line-seven-stages/t01.ipynb) without installing anything. The plan is in the [milestones](https://github.com/tamnd/cpython-internals/milestones) and the decisions that have not been made yet are in the [open questions](https://github.com/tamnd/cpython-internals/issues?q=is%3Aissue+label%3Akind%2Fopen-question).

## Who this is for

Two people, and pretending they are one person is how projects like this fail.

The first knows Python, has never written C, and has never built an interpreter. They need a path with no cliff in it, where every claim is something they can watch happen on their own screen. They will quit at the first paragraph that says "the compiler then emits the appropriate bytecode" without showing them.

The second already knows what a bytecode VM is and wants to write one that passes CPython's own test suite. They do not need motivation. They need exact field layouts, exact algorithms, exact edge cases, exact error messages and a harness.

Every chapter therefore produces two things. The chapter teaches, in prose and pictures and runnable cells. The blueprint specifies, with structures, algorithms, invariants, edge cases and port notes, and no motivation at all. CI checks that the two agree.

## What is different about it

**Three passes, not one walk.** Linear internals books order the material the way data flows, which means a beginner spends three weeks in the tokenizer and arrives at the eval loop exhausted. The drop off curve of every CPython resource has its cliff in the same place. This one does three complete traversals of the whole machine instead. Pass one is a single day, standard library only, browser only, and ends with the reader able to draw the entire pipeline from memory. Pass two opens every box in C. Pass three changes them.

**Nothing is asserted without an experiment.** There is a [claim ledger](lessons/CLAIMS.md), it is published, and CI fails the build if a behavioural claim in the prose has no runnable cell behind it. The rule is that the evidence is the next code cell and it has to come before the next section heading, because a claim proved three sections later is a claim nobody checked. Claims that genuinely cannot be observed from Python are marked with the reason and capped at three per lesson, because without the cap they become the escape hatch that turns this back into a book. Every lesson written so far is marked up: 154 claims, 13 of which cannot be observed from Python and say why.

**Every chapter runs in a browser.** Pyodide 314 is CPython 3.14 compiled to WebAssembly, so real bytecode, refcount, dictionary layout and garbage collection experiments work on a locked down school laptop with nothing installed. Chapters that need a debug build and a debugger ship a recorded session you can step through instead, generated in CI against a real build rather than captured by hand.

That claim was measured rather than assumed. Fifteen checks run on a native CPython and inside a real WebAssembly runtime, and twelve of them behave identically: `_testinternalcapi`, `ctypes` reading a live object header, `sys.monitoring`, `sys.settrace`, the cycle collector, and the whole front end. Threads cannot start, one call has to be made slightly differently, and one bad argument crashes the runtime instead of raising. The matrix, the raw runs and the decision that came out of them are in [probes/pyodide](probes/pyodide), and CI runs the same checks on every pull request so a Pyodide release that takes something away is noticed here rather than by a reader.

Checks are a proxy for the promise, so the lessons themselves are run there too. Every notebook, every code cell, in order, in a fresh browser runtime each, on every pull request. All twelve run start to finish today, and a cell that stops running there fails the build unless somebody has written down why it cannot work.

**CPython already contains three machine readable specifications of itself, and almost nobody teaches this.** `Grammar/python.gram` is the grammar. `Parser/Python.asdl` is the AST. `Python/bytecodes.c` is the interpreter semantics, written in a DSL that `Tools/cases_generator` compiles into the tier 1 interpreter, the tier 2 interpreter, the optimizer cases and every metadata table. CPython does not hand write its front end or its interpreter, it generates them. So the right architecture for a reimplementation is not to port the C, it is to add a backend, which is what the capstone does.

**The compiler is already exposed to Python.** `_testinternalcapi` exports `compiler_codegen`, `optimize_cfg` and `assemble_code_object` on a stock interpreter. You can run the CPython compiler one stage at a time, from a notebook, and diff the control flow graph before and after optimization, with no build. This is the best teaching hook in the codebase and no existing course uses it.

It is a private test module with no compatibility promise, so "on a stock interpreter" is a claim about packaging and it was checked rather than assumed. Twelve ways of getting a Python were asked the question. Most of them ship it, including uv, Homebrew, conda-forge, the official Docker images, Debian and Ubuntu. Fedora's `python3` does not, which is a surprise because Fedora ships a newer Python than almost anybody else, and `dnf install python3-test` puts it back. The table, the raw answers and what the lessons do about it are in [probes/distributions](probes/distributions).

## What "compatible" is allowed to mean

Nobody has ever built a 100% compatible Python that is not CPython, and a project that claims otherwise gets taken apart in an afternoon, so the tiers are in the README rather than in a footnote.

| Tier | What it covers | Reachable |
|---|---|---|
| A | Language semantics: same results, same exceptions, same messages, same evaluation order | Yes, and this is the target |
| B | Introspection: `dis` output, code objects, line tables, exception tables, `ast.dump`, marshal | Mostly, and cheaply if you generate from CPython's own specs |
| C | The C API and ABI, so existing extension wheels load | No, not for a from scratch implementation, and the reasons are written down |
| D | `id()` values, exact refcounts, exact `getsizeof`, allocation addresses, scheduling, speed | No, and enumerating it is how you avoid wasting a week on it |

The capstone does not ship "it works". It ships a scorecard with a number, the failures enumerated, and each failure classified as a real semantic divergence or a tier D assertion. That is checkable by strangers, which a claim is not.

## Which CPython

Pinned to `v3.15.0rc1` today and moving to `v3.15.0` when it ships on 1 October 2026. Every code reference is written as `Python/ceval.c:1213@v3.15.0rc1#_PyEval_EvalFrameDefault` and checked by CI against the pinned tree, so when the pin moves we are told exactly which references broke instead of finding out from a reader. The trailing symbol is what makes that work: a bare line number drifts silently when upstream inserts a function above it, and the citation then points at something plausible and wrong, which is worse than pointing at nothing. A bot diffs every cited region against upstream weekly and files one issue per affected lesson.

3.15 is the right pin and the timing is good. It is the first release with a stable ABI for free threaded builds, it adds explicit lazy imports which drag a new object type through the grammar, the compiler, the import machinery and attribute lookup all at once, and its JIT is reported at 8 to 9 percent on x86-64 and 12 to 13 percent on AArch64 macOS. Pinning to 3.14 would mean rewriting the JIT chapter within a year.

## What is built so far

| | What it is | Where |
|---|---|---|
| `refcheck` | Resolves every `Path/File.c:START-END@TAG#symbol` citation in the repository against the pinned CPython tree, and fails CI when one drifts | [tools/refcheck](tools/refcheck) |
| `pyxray` | The instrumentation every lesson imports: build banner, object headers, reference counts, bytecode as data, and CPython's compiler run one stage at a time | [pyxray](pyxray) |
| `nbcheck` | The rules a lesson notebook has to follow, checked before review rather than after: the Colab badge points at itself, the build banner runs before anything it could explain, no code cell appears without a sentence introducing it, and no outputs are committed | [tools/nbcheck](tools/nbcheck) |
| `nbbuild` | Lessons are written as Python and generated into notebooks, because nobody should have to edit a `.ipynb` by hand or review a diff of one. The generated file is committed as well, and CI fails if it stops matching the code that produced it | [tools/nbbuild](tools/nbbuild) |
| `nbdiagram` | Every picture in a lesson is an Excalidraw scene drawn from Python, written out as an editable `.excalidraw` and as the `.svg` GitHub and Colab display. Colours, type and spacing come from one shared theme, so the diagrams, the charts and the animations look like one project | [tools/nbdiagram](tools/nbdiagram) |
| `nbversion` | The lessons are written against 3.15 and every reader in Colab or in a browser widget is on 3.14. This runs all of them on both, compares the output cell by cell, and fails when a cell that differs has no note saying so, or carries a note that stopped being true | [tools/nbversion](tools/nbversion) |
| `bpcheck` | The shape a blueprint has to have before somebody can implement from it: the nine sections in order, the header block, the invariant numbering, and no fact deferred to a lesson | [tools/bpcheck](tools/bpcheck) |
| `bpc` | The blueprint compiler. Where upstream ships the material in a form a program can read, the specification is generated from it rather than typed. It reads `Parser/Python.asdl` with CPython's own parser and writes the three sections of BP-AST that list all 113 node kinds, each one citing the line it is declared on | [tools/bpc](tools/bpc) |
| `cpybuild` | CPython built five ways, debug, release, free threaded, JIT and tail calling, on two architectures. Compiled once a week in CI and referred to everywhere else by digest, so that seeing what a debug build says takes a `docker run` rather than an evening with a toolchain | [tools/cpybuild](tools/cpybuild) |
| `tier1` | The handful of experiments a reader's own Python cannot run. Each one says why it needs the build it needs, runs in that build in CI, and has what it printed committed next to it and shown in the lesson, so the numbers are checked against a real interpreter rather than pasted in once | [tools/tier1](tools/tier1) |
| `boss` | The end of part boss fights: a problem with no worked answer anywhere in the text, and a grader a reader runs on their own Python with nothing installed. CI runs every grader against a submission that should pass and one that should fail, and checks the sentence it turns the failing one down with | [tools/boss](tools/boss) |
| `gdbrec` | Real gdb sessions against the debug build, run in the pinned image and committed command by command with the line of explanation that belongs above each one, so a reader with no debugger can still read one. Re run in CI and compared line by line, with addresses allowed to move and nothing else | [tools/gdbrec](tools/gdbrec) |
| `distprobe` | Asks every Python a reader is likely to be holding, twelve of them, whether it ships the private module the compiler lessons run on. Keeps a channel that could not be reached separate from a channel that answered no, because Docker being absent and Fedora not packaging a module would otherwise look the same | [tools/distprobe](tools/distprobe) |
| `wasmprobe` | Asks a browser Python which of the surfaces the lessons depend on actually work, runs the same questions on a native interpreter for comparison, and then runs the lesson notebooks themselves there, cell by cell. Fails the build when something stops working in the browser without a written decision about it | [tools/wasmprobe](tools/wasmprobe) |
| `xraymanim` | The animations, and the fifteen shapes they are allowed to be made of. Each one is planned as a storyboard that is checked in milliseconds, so a mistake is caught before anybody pays for a render | [xraymanim](xraymanim) |
| `xraywidgets` | The parts of a lesson you can click: a disassembler that shows what `dis` hides, a pipeline explorer with six panes from source to code object, and a prediction gate that asks before it tells. Each one renders twice from one piece of code: plain HTML with nothing installed, and the same picture with working buttons when anywidget is there | [xraywidgets](xraywidgets) |

## The lessons

Every lesson is a notebook with a Colab badge on it, so there is nothing to install and nothing to build. Each one is executed end to end in CI on 3.15.0rc1 and on 3.14 before it merges, and every claim it makes about CPython carries a file, a line range and a symbol that `refcheck` resolves against the pinned tree.

Where a cell prints something different on the two versions, the notebook says so, in a note under the cell or in a paragraph near the top. Those notes are checked rather than trusted: CI runs every lesson on both interpreters, compares the output cell by cell, and fails both when a cell that differs has no note and when a note is left on a cell that has stopped differing. Sixty four cells across the twelve lessons carry one today. A note about the reader's own machine rather than the version, like how many files are in their standard library, is marked as such, because two recordings cannot decide that one.

Vocabulary works the same way. There is one definition per term in [GLOSSARY.md](GLOSSARY.md), and a lesson links into it rather than explaining a word it explained forty lessons ago or assuming you remember one. Each entry says what the word means and then says the thing people reliably get wrong about it, and where a definition rests on something in CPython rather than on the language reference it carries a citation like everything else here.

Lessons do not invent a fresh example each time either. There are three programs, they are fixed, and they live in `pyxray.programs`. `L0` is `answer = 6 * 7`, one line, small enough that its bytecode and its tree and its symbol table fit on the screen together. `L1` is an iterative Fibonacci, and one call to it is enough for the interpreter to specialize the two instructions in its loop. `L2` is a small linked structure carrying a class, a generator, a closure, a dict, a `try`/`except`/`finally` and, on request, a reference cycle. Meeting a new program and a new subsystem in the same lesson is two jobs, and the one most readers drop is the subsystem.

The pictures are generated too. A lesson's `diagrams.py` sits next to its `build.py` and writes each scene out twice, once as an `.excalidraw` anybody can open and edit and once as the `.svg` the notebook embeds, and CI redraws them on every change to check the committed files still match. Every lesson opens with the same map of the pipeline, from shared data rather than from a copy per lesson, so it cannot drift apart as the material grows.

A lesson can also end with a boss fight, which is a problem the text does not solve for you. T05 has the first one: work out a function's local slot layout from its source, without compiling it. You copy a starter, fill in one function, and run `python lessons/t05-the-tree-becomes-bytecode/grade.py answer.py` on whatever Python you already have. The grader compiles fifty six functions itself, sixteen written by hand and forty generated at random, and when you are wrong it names the function and the first slot you disagree about rather than just saying no. CI runs every grader against a submission that should pass and one that should fail, over twenty different random corpora on both interpreters, because a grader nobody has watched fail is a grader that might be waving everything through.

| | Lesson | What you come away with | Milestone | Run it |
|---|---|---|---|---|
| Z01 | [C for people who will only ever read C](lessons/z01-reading-c/z01.ipynb) | Reading CPython's C without writing any, through one nine line function, and finishing by reimplementing the list growth formula in Python and checking it against a running interpreter | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/z01-reading-c/z01.ipynb) |
| Z02 | [How to be lost productively](lessons/z02-being-lost/z02.ipynb) | Finding the twenty lines that answer your question in two million, the rule that spots the third of the C nobody typed, a map of the tree that fits on one screen, and tracing a line of C back to the argument that put it there | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/z02-being-lost/z02.ipynb) |
| T01 | [One line, seven stages](lessons/t01-one-line-seven-stages/t01.ipynb) | Where `answer = 6 * 7` goes between the file and the answer, which CPython source file does each step, and why the multiplication never happens while your program is running | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t01-one-line-seven-stages/t01.ipynb) |
| T02 | [Text becomes tokens](lessons/t02-text-becomes-tokens/t02.ipynb) | How indentation actually works, why the tokenizer has never heard of a keyword, what mixed tabs and spaces really means, and what an f-string turns into | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t02-text-becomes-tokens/t02.ipynb) |
| T03 | [Tokens become a tree](lessons/t03-tokens-become-a-tree/t03.ipynb) | What a syntax tree keeps about your file and what it throws away, where the node types are written down, and a property test that says the tree is the whole meaning | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t03-tokens-become-a-tree/t03.ipynb) |
| T04 | [Names get scopes](lessons/t04-names-get-scopes/t04.ipynb) | Why the same line of code compiles to a different instruction in two functions, what the five possible answers are, and how one `global` statement inside a function changes the code outside it | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t04-names-get-scopes/t04.ipynb) |
| T05 | [The tree becomes bytecode](lessons/t05-the-tree-becomes-bytecode/t05.ipynb) | Where the multiplication in `6 * 7` goes, why some code you wrote is not in the file at all, and the four numbers that decide how much work the compiler is willing to do for you | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t05-the-tree-becomes-bytecode/t05.ipynb) |
| T06 | [Reading bytecode fluently](lessons/t06-reading-bytecode-fluently/t06.ipynb) | What the argument byte means for each instruction, why the offsets in a listing skip numbers, how jumps count, and where `co_stacksize` comes from | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t06-reading-bytecode-fluently/t06.ipynb) |
| T07 | [The machine runs](lessons/t07-the-machine-runs/t07.ipynb) | The loop that runs bytecode, what a frame is made of, why Python calling Python never touches the C stack, and how to watch a real function run one instruction at a time | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t07-the-machine-runs/t07.ipynb) |
| T08 | [Everything is an object](lessons/t08-everything-is-an-object/t08.ipynb) | The two fields in front of every value, the four questions you can ask about one, why `is` and `==` are unrelated, and why the famous `257 is 257` example measures the compiler rather than the small integer cache | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t08-everything-is-an-object/t08.ipynb) |
| T09 | [Memory appears and disappears](lessons/t09-memory-appears-and-disappears/t09.ipynb) | Why most freeing in CPython happens immediately, the one shape reference counting cannot free, the subtract trick the cycle collector uses to tell garbage from live data, and why freeing a large list does not make your process smaller | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t09-memory-appears-and-disappears/t09.ipynb) |
| T10 | [The napkin](lessons/t10-the-napkin/t10.ipynb) | The whole first part on one page, drawn from memory and then checked against the reference, plus the one line that explains most confusion about Python and seven things you have read that are nearly right | M1 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/t10-the-napkin/t10.ipynb) |
| B01 | [Building CPython](lessons/b01-building-cpython/b01.ipynb) | What your interpreter still remembers about the day it was compiled, three ways to have a CPython to poke at when only one of them involves a compiler, which files in the tree nobody wrote, and the flag `sysconfig` is unable to see | M2 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b01-building-cpython/b01.ipynb) |
| B02 | [Watching the interpreter stop](lessons/b02-the-debugger/b02.ipynb) | A whole pdb session written down in advance so it can be read rather than performed, a working debugger in four lines, and two real gdb sessions against the debug build that show seventeen C frames for four Python calls and name the line behind a segfault | M2 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b02-the-debugger/b02.ipynb) |
| B03 | [Asking CPython whether it still works](lessons/b03-the-test-suite/b03.ipynb) | How the suite that says CPython still works is put together, how to go from the command that runs four hundred files to the one that runs a single method, what regrtest adds on top of plain unittest, and a recorded debug build catching a reference leak in a test that passed | M2 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b03-the-test-suite/b03.ipynb) |
| B04 | [Reading the tree](lessons/b04-reading-the-tree/b04.ipynb) | Which files in the tree a person wrote and which a script wrote, how to get a file and a line range for anything in the standard library out of your own interpreter, and two recorded runs on a real tree: the count of how much of the C nobody typed, and an instruction added to Python/bytecodes.c turning into eval loop C | M2 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/b04-reading-the-tree/b04.ipynb) |
| F01 | [The tokenizer, in C](lessons/f01-the-tokenizer-in-c/f01.ipynb) | Where the token numbers come from and why neither the C nor the Python side decides them, the four ways text gets into the tokenizer and the one field they differ in, the eight fields that hold all of its memory, and why a TabError and an unterminated string are written in two different files | M3 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f01-the-tokenizer-in-c/f01.ipynb) |
| F02 | [f-strings in the lexer](lessons/f02-f-strings-in-the-lexer/f02.ipynb) | The stack of modes the tokenizer pushes when it walks into an f-string, two nesting limits that are nothing like each other, why a format spec is an f-string of its own, why the token for a backslash n is two characters long, and the private copy of your source that makes f"{x=}" print your spacing | M3 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f02-f-strings-in-the-lexer/f02.ipynb) |
| F03 | [The parser nobody wrote](lessons/f03-the-parser-nobody-wrote/f03.ipynb) | The parser is generated from Grammar/python.gram, and that one fact explains why 1 - 2 - 3 leans left while 2 ** 3 ** 4 leans right, why match is a keyword only where the grammar looks for one, and why some syntax errors name your mistake while others just say invalid syntax | M3 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f03-the-parser-nobody-wrote/f03.ipynb) |
| F04 | [The tree is generated too](lessons/f04-the-tree-is-generated-too/f04.ipynb) | Parser/Python.asdl is 154 lines with no code in it, and a generator turns it into the C structs the parser fills in and the classes you import from ast, so reading _fields is reading the schema back, plus what the tree throws away and why a tree you build by hand is checked twice in C | M3 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f04-the-tree-is-generated-too/f04.ipynb) |
| F05 | [Every name gets a number](lessons/f05-every-name-gets-a-number/f05.ipynb) | A whole pass of the compiler that emits no code, five scope constants in a header that every name in your program is sorted into, why nonlocal at module level parses fine and refuses to compile, where UnboundLocalError really comes from, and the one name the symbol table adds on your behalf so that super() works | M3 | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/tamnd/cpython-internals/blob/main/lessons/f05-every-name-gets-a-number/f05.ipynb) |

More are landing in order. [lessons/README.md](lessons/README.md) explains how one is put together and how to run them locally.

Four things the tooling has already found, all of which would have gone into prose as fact and been wrong. The small integer cache stops at 1024 on 3.15 rather than 256, so the `257 is 257` example every tutorial uses gives the opposite answer ([#33](https://github.com/tamnd/cpython-internals/issues/33)). `sys.getrefcount` stopped being reliably one too high in 3.14, because `LOAD_FAST_BORROW` passes a local without creating a reference while `LOAD_GLOBAL` still creates one, so the correction every introspection helper applies depends on the call site. `RESUME` grew an inline cache entry in 3.15, so it is two bytes on 3.14 and four on 3.15, which shifts every offset in a hand counted disassembly. And writing B01 turned up a bug in this project's own banner: `sysconfig` cannot see any macro in `pyconfig.h` whose name begins with an underscore, which is exactly where a tail calling build records itself, so those builds announced themselves as a stock release build for months ([#110](https://github.com/tamnd/cpython-internals/issues/110)).

## The animations

Some things are hard to see in a still picture, because the point of them is that something changes. A reference count going up and down, an instruction pointer walking along a strip of bytecode, a value moving on and off the stack. Those get a short animation instead, under ninety seconds, no sound, captions burned into the picture so it works on a phone with the volume off.

Everything in them is real. The tokens are what `tokenize` returns and the instruction listings are what CPython 3.15.0rc1 emits, because a reader watching an animation cannot stop and check the bytecode while it plays.

| | Animation | Lesson |
|---|---|---|
| a01 | [One line of Python, seven stages](anim/rendered/a01-seven-stages.gif) | T01 |
| a02 | [A name is a label, not a box](anim/rendered/a02-a-name-is-a-label.gif) | T08 |
| a03 | [The stack machine](anim/rendered/a03-the-stack-machine.gif) | T07 |
| a04 | [How a dict finds a key](anim/rendered/a04-how-a-dict-finds-a-key.gif) | T08 |
| a05 | [A cycle, and what frees it](anim/rendered/a05-a-cycle-and-the-collector.gif) | T09 |

They are all drawn from the same fifteen shapes, listed with what each one means in [xraymanim/VISUAL-SYSTEM.md](xraymanim/VISUAL-SYSTEM.md), and adding a sixteenth needs an amendment to that document first. That rule is not a convention somebody has to remember: the shape list is code, a storyboard that names a shape outside it fails, and a shape that is drawable but undescribed fails too. [anim/README.md](anim/README.md) has the index and how to render them.

## The blueprints

A lesson teaches and a blueprint specifies. Prose good enough for a beginner is too loose to implement from, so each subsystem gets a second document written for somebody who already understands it and is now typing a Python in Go or Rust. A blueprint has no motivation, no analogies, no history and no pictures, and it may not send the reader to a lesson for a fact, even where that means repeating a lesson word for word.

Every one has the same nine sections in the same order, so a reader who has read one knows where to look in all of them: purpose and scope, data structures, algorithms, invariants, observable behaviour, edge cases and error paths, interactions, conformance, port notes. The three that make it more than a rewrite of the header file are observable behaviour, which decides how closely a port has to match, edge cases, which is where the accidents are marked as accidents, and conformance, which names the test behind each claim and says plainly which claims have no test yet.

| | Blueprint | What it fixes |
|---|---|---|
| BP-MAP | [The shape of the whole interpreter](blueprints/BP-MAP.md) | The runtime, the interpreter, the thread state and the frame, what contains what, and which source file belongs to which blueprint so that two of them cannot claim the same code |
| BP-PIPELINE | [Source text to a running frame](blueprints/BP-PIPELINE.md) | The eight artifacts and the seven transitions between them, the arena that holds the middle five, the three depth limits and the three different exceptions they raise, and the exact point where compile time ends |
| BP-AST | [The node types and their fields](blueprints/BP-AST.md) | Every one of the 19 types, the 113 node kinds and the 198 fields, what each field holds and what happens when you leave it out, the arena the whole tree lives in, and the validation pass that rejects trees the grammar allows |

The pseudocode is one dialect across all of them, defined in [blueprints/NOTATION.md](blueprints/NOTATION.md), with explicit pointers, explicit allocation, explicit refcount operations and no exceptions. Their citations are resolved against the pinned tree along with everything else, and `bpcheck` holds the structure up.

Sections 1, 2 and 5 of BP-AST are not typed by anybody. They are compiled out of `Parser/Python.asdl` by [bpc](tools/bpc), using CPython's own ASDL parser, so the table of node kinds is right by construction and every row cites the line it came from. The prose lives in [blueprints/sources/BP-AST.md](blueprints/sources/BP-AST.md) and the finished document is committed next to the hand written ones, with markers showing where the generated parts start and stop.

## What is planned to be here

```
book/           the prose site, one directory per part
lessons/        the notebooks, the source of truth for every runnable cell
blueprints/     the normative specification, with sources/ holding the prose half
                of the ones whose mechanical sections are generated
anim/           manim scenes, built from one shared mobject library
apps/           the Gradio playgrounds
pyxray/         the instrumentation toolkit every lesson imports
xraywidgets/    the widgets a reader clicks, which still draw with nothing installed
xraymanim/      the visual grammar, so a hundred animations look like one project
conformance/    the differential harness, the golden corpora and the scorecard
reimpl/go/      the Go reference implementation, which is the specification's test suite
reimpl/rust/    the Rust one, which is also the handoff to a serious runtime project
vendor/cpython/ the pinned submodule
```

## The plan

| | Milestone | What it ships |
|---|---|---|
| M0 | Foundations | The toolkit, the build matrix, the visual grammar, and one lesson built to the full bar |
| M1 | The Tourist | Twelve lessons, one day, browser only, the first public release |
| M2 | Toolchain | Building CPython five ways, the debugger, the test suite, and the pin moves to 3.15.0 |
| M3 | The front end | Tokenizer through code objects, and the compile explorer |
| M4 | The object model | Fourteen lessons and twelve blueprints, the largest content milestone |
| M5 | The interpreter | Dispatch, frames, zero cost exceptions, specialization, tier 2 and the JIT |
| M6 | Version bump rehearsal | Pay the maintenance cost early and measure it, while there are fifty lessons and not eighty five |
| M7 | Memory | obmalloc, reference counting, the cycle collector, and the free threaded collector |
| M8 | Concurrency and runtime | The GIL, free threading, subinterpreters, startup, import and the C API |
| M9 | Surgeon | Add an opcode, add syntax, break the GC on purpose, and build the conformance harness |
| M10 | Go | An implementation, a scorecard, and a bug filed against every blueprint that was not enough |
| M11 | Rust | A second implementation, which is the real test of whether the blueprints specify CPython |
| M12 | 1.0 | The numbers published with the failures named |

There are four sane places to stop and each one leaves something worth having. M1 alone is the best free introduction to CPython that exists. M5 covers what most readers actually want. M8 is complete coverage. M11 is the whole thing.

## Prior art

`InternalDocs/` in the CPython tree is upstream truth, maintained by the people who write the code, and nineteen documents is also a map of what they consider hard. We link to it and never paraphrase it. What it does not have is an on ramp, a runnable experiment or a picture, and that is the gap this fills.

Anthony Shaw's *CPython Internals* is the closest thing to a competitor and is good, particularly on the memory allocator. It is a book, so it is frozen against a Python from several releases ago, and everything after 3.11 is either absent or predates the current design. `zpoint/CPython-Internals` is deep and heavily illustrated and written against 3.8 era source. *Crafting Interpreters* is not about CPython and is still the best book on this subject, because every chapter is code the reader types, and it is the standard to hit.

The gap all of them share is the same: nothing that is current, sequenced, hands on, visual, and precise enough to reimplement from. Any two of those five exist. Not all five.

## Licence

Code is MIT. Prose, diagrams and animations are CC BY 4.0. Quoted CPython source is under the PSF Licence with the notice retained, and every excerpt carries its path, line and tag.
