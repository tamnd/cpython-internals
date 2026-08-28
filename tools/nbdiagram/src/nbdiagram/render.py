"""Rendering an Excalidraw scene to SVG.

The `.excalidraw` file is the editable source, but nothing renders it: GitHub will not, and
neither will Colab. So each scene is also rendered to an SVG, and the SVG is what a lesson
actually embeds.

This renderer is deliberately narrow. It handles the element types this project emits and
nothing else, which is about two hundred lines instead of the several thousand a faithful
Excalidraw renderer needs. That is the right trade: the alternative is a headless browser
in the build, which is slow, flaky, and a dependency that eventually breaks on a Tuesday.

Two properties matter more than fidelity. The output is deterministic, so CI can compare a
committed SVG against a fresh render byte for byte. And it is self contained, with no
external font or script reference, because GitHub and Colab both display an SVG through an
`img` tag, and an `img` tag will not load anything from outside the file.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from pyxray import theme

from .scene import Element, Scene

#: Space left around the drawing, so nothing touches the edge of the image.
MARGIN = 24

#: The arrowhead, as the two strokes of a V rather than a filled triangle, which is what
#: Excalidraw draws and is lighter on the page.
ARROWHEAD_LENGTH = 14
ARROWHEAD_ANGLE = 0.45


def _dash(element: Element) -> str:
    if element.data.get("strokeStyle") == "dashed":
        return ' stroke-dasharray="10 8"'
    return ""


def _rectangle(element: Element) -> str:
    data = element.data
    radius = theme.CORNER_RADIUS if data.get("roundness") else 0
    return (
        f'<rect x="{data["x"]:.1f}" y="{data["y"]:.1f}" '
        f'width="{data["width"]:.1f}" height="{data["height"]:.1f}" rx="{radius}" '
        f'fill="{data["backgroundColor"]}" stroke="{data["strokeColor"]}" '
        f'stroke-width="{data["strokeWidth"]}"{_dash(element)}/>'
    )


def _ellipse(element: Element) -> str:
    data = element.data
    return (
        f'<ellipse cx="{data["x"] + data["width"] / 2:.1f}" '
        f'cy="{data["y"] + data["height"] / 2:.1f}" '
        f'rx="{data["width"] / 2:.1f}" ry="{data["height"] / 2:.1f}" '
        f'fill="{data["backgroundColor"]}" stroke="{data["strokeColor"]}" '
        f'stroke-width="{data["strokeWidth"]}"{_dash(element)}/>'
    )


def _diamond(element: Element) -> str:
    data = element.data
    x, y, w, h = data["x"], data["y"], data["width"], data["height"]
    corners = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
    points = " ".join(f"{px:.1f},{py:.1f}" for px, py in corners)
    return (
        f'<polygon points="{points}" fill="{data["backgroundColor"]}" '
        f'stroke="{data["strokeColor"]}" stroke-width="{data["strokeWidth"]}"{_dash(element)}/>'
    )


def _polyline(element: Element) -> str:
    data = element.data
    points = " ".join(
        f"{data['x'] + px:.1f},{data['y'] + py:.1f}" for px, py in data.get("points", [])
    )
    fill = data["backgroundColor"] if data.get("polygon") else "none"
    stroke = data["strokeColor"]
    if stroke == "transparent":
        stroke = "none"
    opacity = data.get("opacity", 100)
    faded = f' opacity="{opacity / 100:.2f}"' if opacity != 100 else ""
    return (
        f'<polyline points="{points}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{data["strokeWidth"]}" stroke-linecap="round" '
        f'stroke-linejoin="round"{faded}{_dash(element)}/>'
    )


def _arrow(element: Element) -> str:
    import math

    data = element.data
    parts = [_polyline(element)]
    points = data.get("points", [])
    if len(points) < 2:
        return "".join(parts)
    (x0, y0), (x1, y1) = points[-2], points[-1]
    tip_x, tip_y = data["x"] + x1, data["y"] + y1
    angle = math.atan2(y1 - y0, x1 - x0)
    for turn in (ARROWHEAD_ANGLE, -ARROWHEAD_ANGLE):
        back = angle + math.pi + turn
        wing_x = tip_x + ARROWHEAD_LENGTH * math.cos(back)
        wing_y = tip_y + ARROWHEAD_LENGTH * math.sin(back)
        parts.append(
            f'<line x1="{tip_x:.1f}" y1="{tip_y:.1f}" x2="{wing_x:.1f}" y2="{wing_y:.1f}" '
            f'stroke="{data["strokeColor"]}" stroke-width="{data["strokeWidth"]}" '
            f'stroke-linecap="round"/>'
        )
    return "".join(parts)


def _text(element: Element) -> str:
    """Text, positioned the way SVG wants rather than the way Excalidraw stores it.

    Excalidraw anchors a text box at its top left and centres within it. SVG has no vertical
    centring at all, so the baseline is worked out here. The 0.32 is the share of the line
    box that sits below the baseline for these faces, close enough that nothing looks off.
    """
    data = element.data
    size = data["fontSize"]
    family = theme.MONO if data["fontFamily"] == 3 else theme.SANS
    lines = data["text"].split("\n")
    line_height = size * theme.LINE_HEIGHT
    block_height = line_height * len(lines)

    if data.get("verticalAlign") == "middle":
        top = data["y"] + (data["height"] - block_height) / 2
    else:
        top = data["y"]

    align = data.get("textAlign", "left")
    if align == "center":
        anchor, x = "middle", data["x"] + data["width"] / 2
    elif align == "right":
        anchor, x = "end", data["x"] + data["width"]
    else:
        anchor, x = "start", data["x"]

    # Leading spaces matter in this material more than in most: half of T02 is about
    # indentation, and SVG collapses whitespace by default, which would silently delete the
    # thing the picture is about.
    custom = data.get("customData") or {}
    measured = custom.get("textLength")
    # Pinning the drawn width is the only way to guarantee that a mark underneath a piece
    # of source lines up with it. Without it the browser picks whichever monospace face it
    # has, its advance width differs from the estimate, and every underline drifts right.
    stretch = f' textLength="{measured:.1f}" lengthAdjust="spacing"' if measured else ""

    out = []
    for index, line in enumerate(lines):
        baseline = top + line_height * (index + 1) - line_height * 0.32
        out.append(
            f'<text x="{x:.1f}" y="{baseline:.1f}" font-family="{escape(family)}" '
            f'font-size="{size}" fill="{data["strokeColor"]}" text-anchor="{anchor}" '
            f'xml:space="preserve"{stretch}>{escape(line)}</text>'
        )
    return "".join(out)


DRAW = {
    "rectangle": _rectangle,
    "ellipse": _ellipse,
    "diamond": _diamond,
    "line": _polyline,
    "arrow": _arrow,
    "text": _text,
}


def to_svg(scene: Scene) -> str:
    """The scene as a standalone SVG document.

    Shapes are drawn before text so a label is never hidden behind the box it belongs to,
    which is the one ordering bug this renderer could plausibly have.
    """
    left, top, right, bottom = scene.bounds()
    width = right - left + 2 * MARGIN
    height = bottom - top + 2 * MARGIN

    shapes = [element for element in scene.elements if element.data["type"] != "text"]
    labels = [element for element in scene.elements if element.data["type"] == "text"]
    body = "".join(DRAW[element.data["type"]](element) for element in [*shapes, *labels])

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="{left - MARGIN:.1f} {top - MARGIN:.1f} {width:.1f} {height:.1f}" '
        f'role="img" aria-label="{escape(scene.name)}">'
        f'<rect x="{left - MARGIN:.1f}" y="{top - MARGIN:.1f}" width="{width:.1f}" '
        f'height="{height:.1f}" fill="{theme.PAPER}"/>'
        f"{body}"
        "</svg>\n"
    )
