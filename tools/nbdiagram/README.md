# nbdiagram

Draws the pictures in the lessons. Every diagram in this project is a Python script, and the script writes out two files: an `.excalidraw` you can open and edit, and an `.svg` that GitHub and Colab can display.

## Why not just draw them

Because a picture drawn by hand is a picture nobody ever updates. When a function moves in CPython 3.16 there are going to be forty diagrams naming the file it used to be in, and the only way that is a small job is if the diagrams are generated from something you can grep.

Generating them buys three other things. Every pipeline in the material looks like every other pipeline, because they all come from the same `pipeline()` call. The build is deterministic, so CI can regenerate the SVG and compare it to the committed one byte for byte and tell you when they have drifted. And the palette, the type sizes and the spacing all come from `pyxray.theme`, which the matplotlib charts and the manim animations import too, so the three of them look like one project.

## Why Excalidraw and not mermaid

Mermaid does not render in a Colab markdown cell at all, and Colab is where most readers will be. That rules it out on its own.

Excalidraw is also just nicer to look at, and the `.excalidraw` file is a real editable document. Somebody who thinks a box is in the wrong place can drag it onto excalidraw.com, move it, and send it back. The Python is still the source of truth, but the escape hatch is there and it costs nothing.

The scenes are drawn in architect mode, which is Excalidraw with the sketchy stroke turned off. The hand drawn look is charming once and tiring by the fortieth picture, and it makes a diagram of something exact look like somebody is estimating.

## Using it

A lesson has a `diagrams.py` next to its `build.py`:

```python
from nbdiagram import Gallery, stages

gallery = Gallery("t02-text-becomes-tokens")

gallery.add(
    stages.map(
        "where-we-are",
        highlight=stages.TOKENS,
        title="Where this lesson sits",
    )
)

raise SystemExit(gallery.save())
```

That writes `lessons/t02-text-becomes-tokens/diagrams/where-we-are.excalidraw` and the matching `.svg`. The lesson's `build.py` then embeds it:

```python
figure = Diagrams("t02-text-becomes-tokens").figure

figure("where-we-are", "the seven stages, with the tokenizer highlighted")
```

which gives you markdown pointing at the raw URL. It has to be absolute: Colab has no idea which repository the notebook came from, so a relative path is a broken image for every reader who clicked the badge.

`Diagrams` looks the file up on disk rather than importing the script that draws it, so asking for a diagram nobody has drawn fails while the notebook is being built instead of turning into a broken image a reader finds later.

## Commands

```
just build-diagrams    # redraw everything
just diagrams          # fail if a committed diagram no longer matches its script
```

Both run in CI, in the notebooks job.

## The stage map

There is one picture readers see more than any other: the row of boxes from the file you wrote to the answer you got, with the box this lesson is about lit up. It lives in `stages.py` rather than in any one lesson, because a map that quietly gains a box in lesson forty is worse than no map at all. By then the reader has stopped looking at it and will not notice it changed.

A lesson asks for it by name, using the index constants rather than a bare number, since an off by one in a highlight draws a perfectly good picture of the wrong box and no reviewer will catch it:

```python
gallery.add(stages.map("where-we-are", highlight=stages.SYMBOLS))
```

A lesson that genuinely covers more than one box passes a list, `highlight=[stages.INSTRUCTIONS, stages.OPTIMIZED, stages.CODE_OBJECT]`, which is what T05 does because one `compile()` call really does produce all three. Lighting one box there would tell the reader the lesson is smaller than it is. Every index in the list is checked, so a typo is an error and not a picture of the wrong boxes.

The stages are named after the artefact rather than the verb, so "tokens" and not "tokenizing". Each box is a thing you can print, and most lessons are built around printing what is in one box and watching it become the thing in the next. The second line under each box names the CPython file that does the work, which is the main reason the picture earns its place.

## The figures

`pipeline` is stages left to right with arrows between them, each with an optional second line naming the CPython file that does it. `flow` is the same thing down the page, for a chain too long to fit across one. `stack` draws a stack with the top at the top, which sounds obvious and is wrong in about half the stack diagrams in circulation. `table` is a trace: a few monospaced columns and one row per step, with an optional tint on the row where things go wrong. `compare` is two columns for showing that two things which look alike are not, with a verdict line under them saying what the difference was. The verdict is tinted red by default, since most comparisons in these lessons are showing you something that went wrong, but a comparison of the compiler doing its job correctly should pass `verdict_tone="durable"` for green. A red box under a picture of everything working reads as a warning and sends the reader back to look for the mistake. `spans` is a line of source with its pieces named underneath.

`tree` draws a tree downwards with every parent centred over its own children, for the syntax tree the front end lessons keep needing. `ast.dump` is correct and it makes the reader recover the shape of a tree from nested brackets, which is work they should not have to do.

`nest` draws boxes inside boxes, sized from the inside out so a container is exactly big enough for what it holds. T04 uses it for the symbol table, where the point being made is that a block contains other blocks and a decision is made once per block. A tree would have been the wrong picture there, because a tree says only that these things are related to each other and the claim is containment. Containers are drawn before their contents, since SVG has no z-index and a container drawn last paints over everything inside it.

`bars` is a horizontal bar chart, for the places where a column of numbers hides the shape of the answer. A list of `sys.getsizeof` results is something a reader skims past. The same numbers as bars show at a glance that one of them is four times the others, which is the thing worth noticing. The rule of thumb is that a ratio belongs in `bars` and an exact value belongs in `table`. Bars start at zero and are scaled to the largest value, because a chart that starts anywhere else is a chart that lies, and the value is printed at the end of each bar so nobody has to estimate it off an axis this deliberately does not have. A negative value is refused rather than drawn backwards, since bars in a lesson are sizes and counts.

`beside` takes finished scenes and lays them out left to right under their own headings, which is how T03 gets two syntax trees next to each other. Stacking them down the page does not work, because the reader ends up holding one in their head while looking at the other, and the comparison was the whole point. Any figure can be a panel, since a panel is only a scene, and each one comes from the same call that would have drawn it on its own.

`spans` is the one with an opinion in it. A token name is nearly always wider than the token it names, so labels parked under their spans either overlap each other or drift away from the thing they point at. Leader lines fix the overlap and then cross. So the labels go in a row of their own, in the same order as the spans, and each one is joined to its span by a filled ribbon. Two sequences in the same order cannot cross, and a shape reads at a glance where a thin line has to be traced.

Anything genuinely one of a kind gets drawn with the `Scene` primitives directly, which is what T02's INDENT and DEDENT picture does. That is fine. What is not fine is a second, slightly different pipeline figure.

Two `Scene` methods are worth knowing about before you start drawing by hand. `scene.box` centres its label, which is what you want for a box that is the whole thing. `scene.panel` puts the label in the top left corner instead and leaves the middle empty, which is what you want for a box you are about to draw other boxes inside. And a label with `\n` in it keeps the line breaks you wrote, so a box can hold a few lines of source without you laying out each line yourself.

## The renderer

`render.py` turns a scene into SVG. It is about two hundred lines and handles only the element types this package emits, rather than the several thousand a faithful Excalidraw renderer needs. The alternative was a headless browser in the build, which is slow, flaky, and a dependency that eventually breaks on a Tuesday.

Two things matter more than fidelity here. The output is deterministic, so the check step can compare. And it is self contained, with no external font or script, because GitHub and Colab both show an SVG through an `img` tag and an `img` tag will not fetch anything.

Two details in there look odd and are both load bearing. Every text element carries `xml:space="preserve"`, because SVG collapses whitespace by default and half of T02 is about indentation. And source text that something is lined up underneath gets `textLength` pinned, because otherwise the browser picks whichever monospace face it has, its advance width differs from ours, and every mark underneath drifts right.
