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

## Why the browser decides nothing

Python computes the rows and renders the HTML. The JavaScript puts that HTML on the page, listens for a click on a toggle and a keystroke in the source box, and hands both back to Python. It contains no opcode names, no cache arithmetic and no idea what an exception table is, and there is a test that greps it for opcode names to keep it that way.

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
  disassembler.py the first one
  static/         one front end module per widget, named after its slug
```

## Installing

Nothing to do: it comes with the workspace, and `pyxray` is its only dependency. For the version with working buttons:

```
uv sync --extra live
```

CI installs that extra when it runs the tests, so the live path is exercised on every pull request rather than only on the machine of whoever happened to have anywidget installed.
