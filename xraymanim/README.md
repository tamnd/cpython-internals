# xraymanim

The visual grammar for the animations, the six named CPython objects built out of it, and the renderer that turns a scene file into the GIF that ends up in the repository.

The rules it holds up are in [VISUAL-SYSTEM.md](VISUAL-SYSTEM.md). The animations themselves live in [anim/](../anim).

```
uv run xraymanim list                  # every animation, in order, with its length
uv run xraymanim check                 # storyboards, scene files, GIFs and the index
uv sync --extra anim                   # install manim, which is not installed by default
uv run xraymanim render a01-seven-stages
```

## Importing it does not import manim

That is the one structural decision worth knowing about. `import xraymanim` gives you the grammar, the storyboards and the checks, and none of that needs cairo, pango, ffmpeg or numpy. The drawing is one import further in:

```python
from xraymanim.primitives import box, arrow, highlight
from xraymanim.mobjects import PyObjectBox, CodeStrip
from xraymanim.scene import Explainer
```

The reason is that manim brings about thirty packages with it, and every CI job in this repository would otherwise install all of them to check that a caption is not too long. So manim is an extra, `uv sync --extra anim` installs it, and only the animations job needs it.

## Storyboards

An animation is expensive to look at. Rendering takes a minute, so the loop where you change something and see what happened is a minute long, and a mistake in the plan costs several of those. So the plan is data, and it is checked in milliseconds.

Every animation is declared in [catalogue.py](src/xraymanim/catalogue.py) as a list of beats: what the caption says, how long the step lasts, and which shapes the scene is allowed to draw. That is what the ninety second cap is enforced against and what the caption track is built from, so the words and the picture cannot fall out of step.

A scene is free to disagree with its storyboard by accident, so it does not get to. `Explainer` counts the beats the scene actually played and fails the render if the number is wrong.

## The files

| | |
|---|---|
| [grammar.py](src/xraymanim/grammar.py) | Colours, type, geometry, timing, the ninety second cap, and the list of shapes that exist. No manim |
| [storyboard.py](src/xraymanim/storyboard.py) | `Beat` and `Storyboard`, and everything that can be wrong with one. No manim |
| [catalogue.py](src/xraymanim/catalogue.py) | Every animation in the project, in course order. No manim |
| [checks.py](src/xraymanim/checks.py) | The checks that do not need a renderer, which is nearly all of them. No manim |
| [primitives.py](src/xraymanim/primitives.py) | The nine shapes |
| [mobjects.py](src/xraymanim/mobjects.py) | The six named CPython objects |
| [scene.py](src/xraymanim/scene.py) | `Explainer`, the base scene: page colour, caption track, beat tally |
| [render.py](src/xraymanim/render.py) | Manim to mp4, ffmpeg to a palette optimised GIF |

## What is not checked

Whether the animation is any good, and whether it shows what the caption says it shows. Nothing can check that. Watch it.

The committed GIFs are also not compared byte for byte, unlike the diagrams and the notebooks. Video encoders are not reproducible across versions and platforms, and a check that fails when somebody upgrades ffmpeg is a check people learn to ignore. CI renders the scenes again instead and fails if one of them raises, which catches the mistake that actually happens.
