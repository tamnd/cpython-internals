"""Tests for the scene model and the SVG renderer.

Most of these are about things that are invisible until they are wrong: a label that does
not fit its box, whitespace that the browser quietly threw away, an id that changes on
every build and turns `nbdiagram check` into a coin toss.
"""

from __future__ import annotations

import json

import pytest

from nbdiagram.render import to_svg
from nbdiagram.scene import Scene, text_width, wrap
from pyxray import theme


def test_a_scene_starts_empty():
    assert Scene("blank").elements == []
    assert Scene("blank").bounds() == (0, 0, 0, 0)


def test_a_box_carries_its_label_as_a_bound_element():
    scene = Scene("one")
    box = scene.box("hello", 0, 0)
    container, label = scene.elements
    assert box is container
    assert label.data["containerId"] == container.id
    assert container.data["boundElements"] == [{"id": label.id, "type": "text"}]


def test_a_box_is_wide_enough_for_its_label():
    scene = Scene("one")
    box = scene.box("a fairly long label goes here", 0, 0)
    assert box.data["width"] >= text_width("a fairly long label goes here", theme.BODY_SIZE)


def test_a_box_grows_taller_when_its_label_has_to_wrap():
    scene = Scene("one")
    short = scene.box("one two", 0, 0, width=200)
    tall = scene.box("one two three four five six seven eight nine ten", 0, 0, width=200)
    assert tall.data["height"] > short.data["height"]


def test_text_that_fits_is_never_reflowed():
    # Half the labels in this project are monospaced source lines padded into columns, and
    # reflowing collapses the padding that does the aligning.
    assert wrap("tab      -> col 8", 1000, 16, mono=True) == ["tab      -> col 8"]


def test_text_that_does_not_fit_is_broken_on_spaces():
    assert wrap("alpha beta gamma", 60, 16) == ["alpha", "beta", "gamma"]


def test_a_word_too_wide_for_the_box_is_left_alone():
    # Better a symbol that pokes out of its box than `_PyTokenizer_` on one line and `Get`
    # on the next, which no reader would recognise.
    assert wrap("_PyTokenizer_Get", 10, 16) == ["_PyTokenizer_Get"]


def test_monospaced_labels_are_left_aligned_by_default():
    scene = Scene("one")
    scene.box("x = 1", 0, 0, mono=True)
    assert scene.elements[1].data["textAlign"] == "left"


def test_prose_labels_are_centred_by_default():
    scene = Scene("one")
    scene.box("a label", 0, 0)
    assert scene.elements[1].data["textAlign"] == "center"


def test_an_arrow_binds_to_the_boxes_at_each_end():
    scene = Scene("two")
    first = scene.box("a", 0, 0)
    second = scene.box("b", 400, 0)
    arrow = scene.arrow(first, second)
    assert arrow.data["startBinding"]["elementId"] == first.id
    assert arrow.data["endBinding"]["elementId"] == second.id
    assert {"id": arrow.id, "type": "arrow"} in first.data["boundElements"]


def test_an_arrow_between_bare_points_binds_to_nothing():
    scene = Scene("two")
    arrow = scene.arrow((0, 0), (100, 0))
    assert arrow.data["startBinding"] is None
    assert arrow.data["endBinding"] is None


def test_ids_depend_on_content_and_not_on_when_the_build_ran():
    def build():
        scene = Scene("stable")
        scene.box("a", 0, 0)
        scene.text("b", 0, 200)
        return scene.document()

    assert build() == build()


def test_two_scenes_with_different_names_do_not_share_ids():
    first = Scene("first")
    first.box("a", 0, 0)
    second = Scene("second")
    second.box("a", 0, 0)
    assert first.elements[0].id != second.elements[0].id


def test_the_document_is_a_valid_excalidraw_file():
    scene = Scene("one")
    scene.box("a", 0, 0)
    book = json.loads(scene.document())
    assert book["type"] == "excalidraw"
    assert book["version"] == 2
    assert len(book["elements"]) == 2


def test_the_document_ends_with_a_newline():
    scene = Scene("one")
    scene.box("a", 0, 0)
    assert scene.document().endswith("\n")


def test_bounds_cover_every_element():
    scene = Scene("one")
    scene.box("a", 100, 50, width=200, height=80)
    assert scene.bounds() == (100, 50, 300, 130)


def test_bounds_cover_an_arrow_that_points_the_other_way():
    # A leftward arrow is stored with a negative width, and reading that back unsorted put
    # the right edge to the left of the left edge. The viewBox then had the drawing outside
    # it and the whole scene rendered as a strip of white with one arrow in it.
    scene = Scene("one")
    scene.arrow((400, 10), (0, 10))
    left, _, right, _ = scene.bounds()
    assert (left, right) == (0, 400)


def test_an_upward_arrow_is_measured_the_same_way():
    scene = Scene("one")
    scene.arrow((10, 400), (10, 0))
    _, top, _, bottom = scene.bounds()
    assert (top, bottom) == (0, 400)


def test_ports_sit_on_the_edges():
    scene = Scene("one")
    box = scene.box("a", 0, 0, width=100, height=80)
    assert box.port("left") == (0, 40)
    assert box.port("right") == (100, 40)
    assert box.port("top") == (50, 0)
    assert box.port("bottom") == (50, 80)


def test_the_svg_is_self_contained():
    # GitHub and Colab both show an SVG through an img tag, and an img tag will not fetch a
    # font or run a script. Anything external is simply missing for every reader.
    scene = Scene("one")
    scene.box("a", 0, 0)
    svg = to_svg(scene)
    assert "http://www.w3.org/2000/svg" in svg
    assert "<script" not in svg
    assert "@import" not in svg
    assert "xlink:href" not in svg


def test_the_svg_preserves_leading_spaces():
    # Half of T02 is about indentation. SVG collapses whitespace unless told not to, which
    # would silently delete the thing the picture is about.
    scene = Scene("one")
    scene.text("    return", 0, 0, mono=True)
    svg = to_svg(scene)
    assert 'xml:space="preserve"' in svg
    assert "    return" in svg


def test_exact_text_pins_its_drawn_width():
    scene = Scene("one")
    scene.text("    return", 0, 0, mono=True, exact=True)
    assert "textLength=" in to_svg(scene)
    assert 'lengthAdjust="spacing"' in to_svg(scene)


def test_ordinary_text_does_not_pin_its_width():
    scene = Scene("one")
    scene.text("hello", 0, 0)
    assert "textLength=" not in to_svg(scene)


def test_labels_are_drawn_after_the_shapes_they_sit_on():
    scene = Scene("one")
    scene.box("hello", 0, 0)
    svg = to_svg(scene)
    assert svg.index('<rect x="0.0"') < svg.index(">hello<")


def test_a_band_is_filled_and_closed():
    scene = Scene("one")
    band = scene.band([(0, 0), (10, 0), (20, 40), (0, 40)], fill="#ff0000")
    assert band.data["points"][0] == band.data["points"][-1]
    svg = to_svg(scene)
    assert 'fill="#ff0000"' in svg


def test_a_plain_line_is_not_filled():
    scene = Scene("one")
    scene.line([(0, 0), (10, 10)])
    assert 'fill="none"' in to_svg(scene)


def test_markup_in_a_label_is_escaped():
    scene = Scene("one")
    scene.text("a < b & c", 0, 0)
    svg = to_svg(scene)
    assert "&lt;" in svg
    assert "&amp;" in svg


@pytest.mark.parametrize("shape", ["rectangle", "ellipse", "diamond"])
def test_every_shape_renders(shape):
    scene = Scene("one")
    scene.box("a", 0, 0, shape=shape)
    assert to_svg(scene).count("<") > 3


def test_a_label_keeps_the_line_breaks_it_was_written_with():
    # A code listing in a box is laid out by whoever wrote it, and reflowing it would put
    # the indentation somewhere it was never meant to be.
    assert wrap("def f():\n    return 1", 400, 16, mono=True) == ["def f():", "    return 1"]


def test_each_line_of_a_label_is_wrapped_on_its_own():
    lines = wrap("short\nthis line is much too long to fit anywhere", 60, 16)
    assert lines[0] == "short"
    assert len(lines) > 2


def test_a_block_of_text_is_as_wide_as_its_widest_line():
    # Measuring the raw string would run the lines together and make the box far too wide.
    assert text_width("ab\nabcd", 16, mono=True) == text_width("abcd", 16, mono=True)


def test_a_box_is_tall_enough_for_a_label_with_line_breaks():
    scene = Scene("t")
    one = scene.box("one", 0, 0, width=300, height=10)
    many = Scene("t").box("one\ntwo\nthree", 0, 0, width=300, height=10)
    assert many.box[3] > one.box[3]


def test_a_panel_puts_its_name_in_the_top_left_rather_than_the_middle():
    scene = Scene("t")
    panel = scene.panel("outer's frame", 0, 0, 400, 300)
    label = next(element for element in scene.elements if element.data["type"] == "text")
    assert label.box[1] < panel.centre()[1]
    assert label.box[0] < panel.centre()[0]


def test_a_panel_label_is_not_bound_to_the_panel():
    # Bound text in Excalidraw is always centred vertically, which is wrong for a shape whose
    # job is to be the background behind other shapes.
    scene = Scene("t")
    scene.panel("outer", 0, 0, 400, 300)
    label = next(element for element in scene.elements if element.data["type"] == "text")
    assert label.data["containerId"] is None


def test_a_label_on_a_downward_arrow_sits_beside_it_not_above_it():
    # Above the top of a downward arrow is inside the box the arrow leaves, so the label
    # would be printed over the contents of that box.
    scene = Scene("t")
    scene.arrow((100, 100), (100, 300), label="becomes")
    label = next(element for element in scene.elements if element.data["type"] == "text")
    assert 100 < label.box[1] < 300
    assert label.box[0] > 100


def test_a_label_on_a_sideways_arrow_still_sits_above_it():
    scene = Scene("t")
    scene.arrow((100, 100), (400, 100), label="becomes")
    label = next(element for element in scene.elements if element.data["type"] == "text")
    assert label.box[3] <= 100
