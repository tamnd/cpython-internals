"""The stylesheet, generated from `pyxray.theme` rather than written next to it.

The palette is decided once, in `pyxray.theme`, and the Excalidraw diagrams, the matplotlib
charts and the manim animations all read it. A widget that hardcoded `#1971c2` would look
right on the day it was written and would drift the first time a tone changed, which is
exactly the failure the theme module exists to prevent. So the colours here are read out of
the theme and written into CSS custom properties, and everything else in the sheet is
written against those properties.

Dark mode keeps the tone colours and swaps the neutrals. That is not laziness. The tones
are pale fills with dark strokes, and they read as chips sitting on the page rather than as
page colour, so they work against either background as long as the text on them stays dark.
Recolouring six tones for a second theme would mean six more decisions and a second palette
to keep in step with the diagrams, which cannot follow it, because an SVG committed to the
repository has one set of colours in it.
"""

from __future__ import annotations

from pyxray import theme

#: The prefix on every class name and custom property this package emits. Widgets get
#: dropped into notebooks next to other people's CSS, and two letters is cheap insurance.
PREFIX = "xw"


def variables() -> str:
    """The palette as CSS custom properties, one block, read from the theme."""
    lines = [
        f"  --{PREFIX}-ink: {theme.INK};",
        f"  --{PREFIX}-muted: {theme.MUTED};",
        f"  --{PREFIX}-line: {theme.LINE};",
        f"  --{PREFIX}-paper: {theme.PAPER};",
        f"  --{PREFIX}-sans: {theme.SANS};",
        f"  --{PREFIX}-mono: {theme.MONO};",
    ]
    for name, tone in theme.TONES.items():
        lines.append(f"  --{PREFIX}-{name}-stroke: {tone.stroke};")
        lines.append(f"  --{PREFIX}-{name}-fill: {tone.fill};")
    return "\n".join(lines)


#: The layout half of the sheet, which has no colours in it, only references to the
#: properties above. Kept as one string rather than assembled, because CSS read as CSS is
#: easier to check than CSS read as a list of Python strings.
LAYOUT = f"""
.{PREFIX} {{
  font-family: var(--{PREFIX}-sans);
  color: var(--{PREFIX}-ink);
  background: var(--{PREFIX}-paper);
  border: 1px solid var(--{PREFIX}-line);
  border-radius: 12px;
  padding: 16px;
  line-height: 1.4;
  font-size: 14px;
}}
.{PREFIX} * {{ box-sizing: border-box; }}
.{PREFIX}-head {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}}
.{PREFIX}-title {{ font-weight: 700; font-size: 16px; }}
.{PREFIX}-note {{ color: var(--{PREFIX}-muted); font-size: 12px; }}
.{PREFIX}-source {{
  font-family: var(--{PREFIX}-mono);
  white-space: pre;
  overflow-x: auto;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--{PREFIX}-input-stroke);
  background: var(--{PREFIX}-input-fill);
  color: {theme.INK};
  margin-bottom: 12px;
}}
textarea.{PREFIX}-source {{
  display: block;
  width: 100%;
  resize: vertical;
  font-size: 13px;
  line-height: 1.5;
}}
.{PREFIX}-source:focus-visible {{
  outline: 2px solid var(--{PREFIX}-focus-stroke);
  outline-offset: 1px;
}}
.{PREFIX}-toggles {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
.{PREFIX}-toggle {{
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--{PREFIX}-line);
  background: transparent;
  color: inherit;
}}
.{PREFIX}-toggle[aria-pressed="true"] {{
  border-color: var(--{PREFIX}-focus-stroke);
  background: var(--{PREFIX}-focus-fill);
  color: {theme.INK};
  font-weight: 700;
}}
.{PREFIX}-toggle:focus-visible {{
  outline: 2px solid var(--{PREFIX}-focus-stroke);
  outline-offset: 2px;
}}
.{PREFIX}-toggle[disabled] {{ cursor: default; opacity: 0.75; }}
.{PREFIX} table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
.{PREFIX} th {{
  text-align: left;
  font-weight: 700;
  color: var(--{PREFIX}-muted);
  border-bottom: 1px solid var(--{PREFIX}-line);
  padding: 4px 8px 6px 0;
  white-space: nowrap;
}}
.{PREFIX} td {{ padding: 3px 8px 3px 0; vertical-align: top; }}
.{PREFIX} td.{PREFIX}-mono {{ font-family: var(--{PREFIX}-mono); white-space: nowrap; }}
.{PREFIX} tr.{PREFIX}-cache td {{ color: var(--{PREFIX}-muted); font-size: 12px; }}
.{PREFIX}-chip {{
  display: inline-block;
  font-size: 11px;
  font-family: var(--{PREFIX}-sans);
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid currentColor;
  white-space: nowrap;
}}
.{PREFIX} pre {{
  font-family: var(--{PREFIX}-mono);
  font-size: 12px;
  line-height: 1.45;
  margin: 0;
  overflow-x: auto;
  white-space: pre;
}}

/* The six panes of the pipeline explorer. `auto-fit` with a minimum rather than a fixed
   column count, so the same widget is six columns on a wide screen, two in a notebook
   sidebar and one on a phone, without a media query deciding which is which. */
.{PREFIX}-panes {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}}
.{PREFIX}-pane {{
  border: 1px solid var(--{PREFIX}-line);
  border-radius: 8px;
  padding: 8px 10px;
  min-width: 0;
}}
.{PREFIX}-pane-head {{
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}}
.{PREFIX}-pane-title {{ font-weight: 700; font-size: 12px; }}
/* The prediction gate. */
.{PREFIX}-question {{ font-size: 15px; margin: 0 0 12px; }}
.{PREFIX}-options {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
.{PREFIX}-option {{
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--{PREFIX}-line);
  background: transparent;
  color: inherit;
}}
.{PREFIX}-option[aria-pressed="true"] {{
  border-color: var(--{PREFIX}-focus-stroke);
  background: var(--{PREFIX}-focus-fill);
  color: {theme.INK};
}}
.{PREFIX}-option:focus-visible {{
  outline: 2px solid var(--{PREFIX}-focus-stroke);
  outline-offset: 2px;
}}
.{PREFIX}-options-list {{ margin: 0 0 12px; padding-left: 22px; }}
.{PREFIX}-options-list li {{ margin-bottom: 4px; }}
.{PREFIX}-verdict {{ margin: 0 0 12px; }}
.{PREFIX}-explanations {{ list-style: none; margin: 0; padding: 0; }}
.{PREFIX}-explanation {{
  border-top: 1px solid var(--{PREFIX}-line);
  padding: 10px 0;
}}
.{PREFIX}-explanation p {{ margin: 4px 0 0; color: var(--{PREFIX}-muted); }}
.{PREFIX}-option-label {{ font-weight: 700; }}
.{PREFIX}-reveal summary {{ cursor: pointer; font-size: 13px; }}
.{PREFIX}-reveal summary:focus-visible {{
  outline: 2px solid var(--{PREFIX}-focus-stroke);
  outline-offset: 2px;
}}
.{PREFIX}-error {{
  border: 1px solid var(--{PREFIX}-warning-stroke);
  background: var(--{PREFIX}-warning-fill);
  color: {theme.INK};
  border-radius: 8px;
  padding: 10px 12px;
  font-family: var(--{PREFIX}-mono);
  font-size: 12px;
}}
"""

#: One rule per tone, so a chip picks its colours by class name. Written as a loop because
#: six near identical CSS blocks written out by hand are six chances to paste the wrong hue.
TONE_RULES = "\n".join(
    f".{PREFIX}-{name} {{ color: var(--{PREFIX}-{name}-stroke); "
    f"background: var(--{PREFIX}-{name}-fill); }}"
    for name in theme.TONES
)

#: Dark mode. Only the neutrals move: the page goes dark and the text goes light, and the
#: tone chips keep their own colours because they carry their own background with them.
DARK = f"""
@media (prefers-color-scheme: dark) {{
  .{PREFIX} {{
    --{PREFIX}-ink: #e9ecef;
    --{PREFIX}-muted: #adb5bd;
    --{PREFIX}-line: #495057;
    --{PREFIX}-paper: #1a1b1e;
  }}
}}
"""


def stylesheet() -> str:
    """The whole sheet, ready to drop into a `<style>` tag or hand to anywidget."""
    return f".{PREFIX} {{\n{variables()}\n}}\n{LAYOUT}\n{TONE_RULES}\n{DARK}"
