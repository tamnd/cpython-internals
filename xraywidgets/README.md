# xraywidgets

The interactive parts of a lesson. Type some Python, see what the compiler made of it, and turn on the things `dis` leaves out.

Every widget here renders twice from one piece of code. Without anywidget installed you get plain HTML: a real picture with real numbers in it, just with the buttons switched off. With anywidget installed you get the same picture with the buttons working. That is not a fallback bolted on at the end, it is how the package is built, and there is a section below on why.

## The disassembler

```python
from xraywidgets import Disassembler

Disassembler("total = sum(values)")
```

In a notebook that prints the bytecode as a table. Four things are off by default and can be turned on, either by passing them in or by clicking:

| Toggle | What it adds |
|---|---|
| Specialized opcodes | The rewritten forms the interpreter installs after it has watched an instruction run a few times, so `LOAD_ATTR` shows up as `LOAD_ATTR_INSTANCE_VALUE` once it has settled |
| Inline caches | The cache entries sitting between the instructions. They take up real bytes in the code object, and `dis` hides them by default, which is why offsets appear to skip |
| Stack depth | How tall the value stack is before and after each instruction, which is the fastest way to see why an expression compiles the way it does |
| Exception table | Where a `try` went. Since 3.11 there are no `SETUP_FINALLY` instructions to look at, and the handlers live in a side table instead |

They are off to start with because a first disassembly with all four on is a wall of numbers, and a reader who has not yet worked out what an offset is will not get past it.

```python
Disassembler(some_function, depths=True).live()  # buttons work, needs `uv sync --extra live`
```

The argument can be a string, a function, a method or a code object, so a lesson can hand it the function it was just talking about rather than a copy of the text of it.

## The pipeline explorer

```python
from xraywidgets import PipelineExplorer

PipelineExplorer("answer = 6 * 7")
```

Six panes side by side, one per stage: the token stream, the tree, the symbol table, the instructions as code generation left them, the same instructions after the optimizer, and the finished code object. Typing in the source box redraws all six.

The point of showing them together is that each stage throws away something the one before it had, and that is hard to believe from prose. Add a comment to the end of the line and watch it sit in the tokens and be gone by the tree. Leave `6 * 7` alone and watch a `BINARY_OP` come out of code generation and be a plain `LOAD_SMALL_INT 42` by the time there is a code object. That is one edit and two panes, which beats a paragraph saying that constants are folded.

Two of the six panes, code generation and the optimizer, need `_testinternalcapi`, which not every build ships. On a build without it those two say so and the other four still work. A widget that shows nothing because one interpreter hook is missing teaches nobody anything about the four stages that would have run fine.

Long output is cut at forty lines per pane and the cut is announced, because six panes of a hundred lines is a page nobody scrolls through.

## The prediction gate

```python
from xraywidgets import Option, PredictGate

PredictGate(
    question="The compiler sees 6 * 7. What ends up in the code object?",
    options=[
        Option(
            "A BINARY_OP that multiplies at run time",
            why="That is what happens for a * b, where the compiler cannot know the values.",
        ),
        Option(
            "The constant 42",
            why="Both sides are literals, so the multiplication happens once, while compiling.",
            correct=True,
        ),
    ],
    check="dis.dis(compile('6 * 7', '<here>', 'eval'))",
)
```

A question in front of an output, with the answer behind a gate. Reading a disassembly teaches almost nothing on its own: it makes sense while you look at it, you move on, and your model of the compiler is exactly as wrong as it was before, because nothing made you commit to a prediction that could turn out wrong. Being wrong on purpose, in private, and then finding out why is the part that sticks.

`Option` will not be built without a `why`, including on the right answer. A wrong option is only worth offering if somebody could plausibly pick it, and if somebody could plausibly pick it then the reason it is wrong is worth teaching. When the answer is revealed every option's explanation is shown, not only the picked one and not only the right one, so a reader who guessed correctly still learns why the option they nearly picked was wrong.

Which option was picked is written to the reader's own browser with `localStorage` and goes nowhere else. Nothing is scored and nothing is uploaded. A reader who thinks a wrong answer is being logged somewhere stops guessing and starts reading ahead, and guessing is the whole mechanism. The storage exists because notebooks get re-run, and being asked six questions you have already answered is a good way to stop answering them.

The static rendering gates too. The options are a numbered list and the explanations go inside a `<details>`, which folds and unfolds with no JavaScript and is reachable from the keyboard, so a reader looking at a rendered notebook on GitHub still gets asked before they get told.

## Why the browser decides nothing

Python computes the rows and renders the HTML. The JavaScript puts that HTML on the page, listens for a click on a toggle and a keystroke in the source box, and hands both back to Python. It contains no opcode names, no cache arithmetic and no idea what an exception table is, and there is a test that greps it for opcode names to keep it that way. The one exception is the prediction gate, which reads and writes the reader's own answer in their own browser, because that is the only thing in this package that is nobody else's business.

The reason is not tidiness. If the front end worked out which opcodes were specialized, there would be two answers to that question in this repository, and the one written in JavaScript is the one nobody runs a test against. It would drift, and it would drift in the direction of looking right, because the person who noticed would be a reader who trusted the widget over `dis` and got the wrong idea about CPython. Keeping the logic on one side means the picture in a rendered notebook and the picture you can click are the same picture by construction.

It is also what makes the static rendering real. There is no code path where a widget is only correct once a browser is involved, so the version a reader sees on GitHub, in an nbconvert render, in a PDF export, or in the seconds before Pyodide has finished starting is a version with the right numbers in it.

## Colour is never the only signal

Every coloured thing in a widget is a chip, and `parts.chip` will not build one without a label. So the badge on a specialized opcode says the word "specialized" and not just a blue tint, which is what a reader with any of the common kinds of colour blindness needs, and also what survives a printed handout or a screenshot pasted into a chat with the saturation eaten by compression. Making the label a required argument is cheaper than writing that review comment every time.

The toggles are real `<button>` elements with `aria-pressed`, not styled `<div>`s, so they are reachable by tab and operable by space bar without a line of JavaScript, and a screen reader can say whether one is on. The static rendering marks them disabled, because a button that looks live and does nothing is worse than one that admits it.

## The palette comes from one place

There is no hex colour written in this package. `style.py` reads `pyxray.theme`, the same module the Excalidraw diagrams, the matplotlib charts and the manim animations read, and writes it out as CSS custom properties. A test greps the stylesheet for hand written colours and fails if it finds one, so a widget cannot quietly fork away from the diagrams next to it.

Dark mode swaps the neutrals and leaves the tones alone. The tones are pale fills with dark strokes and they read as chips sitting on the page rather than as page colour, so they work against either background. Giving them a second set of values would mean a second palette to keep in step with the diagrams, and an SVG committed to a repository has one set of colours in it.

## Layout

```
src/xraywidgets/
  html.py         building HTML in about eighty lines, with escaping that is not optional
  strings.py      every word a widget shows, in one dictionary
  style.py        the stylesheet, generated from pyxray.theme
  parts.py        the markup more than one widget needs, so it only looks one way
  base.py         what a widget is, and its two forms
  disassembler.py bytecode as a table, with four things dis leaves out
  pipeline.py     six panes, source through code object
  predict.py      ask before you show
  static/         one front end module per widget, plus the part they share
```

## Installing

Nothing to do: it comes with the workspace, and `pyxray` is its only dependency. For the version with working buttons:

```
uv sync --extra live
```

CI installs that extra when it runs the tests, so the live path is exercised on every pull request rather than only on the machine of whoever happened to have anywidget installed.
