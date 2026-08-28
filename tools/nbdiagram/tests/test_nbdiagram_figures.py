"""Tests for the figures and for the stage map every lesson opens with.

Most of a figure is layout, and layout is not worth asserting on: the numbers would change
every time somebody nudged the spacing and the test would say nothing about whether the
picture was right. What is worth asserting on is the part a reader would notice being
wrong. A parent that is not over its children, a highlight on the wrong box, and a stage
map that has quietly changed shape between two lessons are all bugs you cannot see by
reading the diff.
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from nbdiagram import figures, stages
from nbdiagram.scene import Scene


def labels(scene):
    """Every piece of text in the scene, in the order it was added."""
    return [element.data["text"] for element in scene.elements if element.data["type"] == "text"]


def box_named(scene, label):
    """The rectangle a given label is bound to.

    A box is two elements, the rectangle and the text sitting in it, joined by the text's
    `containerId`. Tests want the rectangle, because that is the thing with a position.
    """
    text = next(
        element
        for element in scene.elements
        if element.data["type"] == "text" and element.data["text"] == label
    )
    container = text.data["containerId"]
    return next(element for element in scene.elements if element.id == container)


def test_a_leaf_only_tree_is_one_box():
    scene = figures.tree("t", "Constant")
    assert labels(scene) == ["Constant"]


def test_every_node_in_a_tree_gets_drawn():
    scene = figures.tree("t", ("BinOp", ["Constant 6", "Mult", "Constant 7"]))
    assert set(labels(scene)) == {"BinOp", "Constant 6", "Mult", "Constant 7"}


def test_a_parent_sits_above_its_children():
    scene = figures.tree("t", ("BinOp", ["Constant 6", "Constant 7"]))
    parent = box_named(scene, "BinOp")
    for child in ["Constant 6", "Constant 7"]:
        assert parent.box[3] <= box_named(scene, child).box[1]


def test_a_parent_is_centred_over_its_children():
    scene = figures.tree("t", ("BinOp", ["Constant 6", "Mult", "Constant 7"]))
    parent = box_named(scene, "BinOp")
    left = box_named(scene, "Constant 6").centre()[0]
    right = box_named(scene, "Constant 7").centre()[0]
    assert parent.centre()[0] == pytest.approx((left + right) / 2)


def test_siblings_do_not_overlap():
    scene = figures.tree("t", ("BinOp", ["Constant 6", "Mult", "Constant 7"]))
    boxes = sorted(
        (box_named(scene, name).box for name in ["Constant 6", "Mult", "Constant 7"]),
        key=lambda box: box[0],
    )
    for before, after in pairwise(boxes):
        assert before[2] <= after[0]


def test_a_deeper_subtree_still_leaves_room_for_its_neighbour():
    # The bug this catches is measuring a node by its own label rather than by the width of
    # everything underneath it, which makes a shallow sibling land on top of a deep one.
    scene = figures.tree(
        "t",
        ("Assign", [("Name", ["id 'answer'", "ctx Store"]), "Constant 6"]),
    )
    assert (
        box_named(scene, "Name").box[2] <= box_named(scene, "Constant 6").box[0]
        or box_named(scene, "Constant 6").box[2] <= box_named(scene, "Name").box[0]
    )
    assert box_named(scene, "ctx Store").box[2] <= box_named(scene, "Constant 6").box[0]


def test_the_stage_map_is_the_same_shape_wherever_it_is_asked_for():
    # Two lessons drawing two different maps is the failure this project most wants to
    # avoid, because the reader stops trusting a picture that moves.
    first = stages.map("a")
    second = stages.map("b", highlight=stages.TOKENS)
    assert labels(first) == labels(second)


def test_the_map_names_a_cpython_file_for_every_stage_but_the_first():
    assert all(source for _, source in stages.STAGES)
    assert [source for _, source in stages.STAGES[1:]] == [
        "Parser/lexer/lexer.c",
        "Parser/parser.c",
        "Python/symtable.c",
        "Python/codegen.c",
        "Python/flowgraph.c",
        "Objects/codeobject.c",
        "Python/ceval.c",
    ]


def test_the_seven_in_the_title_is_the_number_of_steps_between_the_boxes():
    assert stages.COUNT == 7


def test_highlighting_a_stage_that_does_not_exist_is_an_error():
    # Off by one in a highlight draws a perfectly good picture of the wrong thing, so it
    # has to fail loudly rather than silently pointing at the neighbouring box.
    with pytest.raises(IndexError, match="no stage"):
        stages.map("a", highlight=len(stages.STAGES))


def test_the_index_constants_match_their_labels():
    assert stages.STAGES[stages.TOKENS][0] == "tokens"
    assert stages.STAGES[stages.ANSWER][0] == "the answer"


def test_a_highlighted_box_is_drawn_differently_from_the_others():
    plain = box_named(stages.map("a"), "tokens")
    lit = box_named(stages.map("b", highlight=stages.TOKENS), "tokens")
    assert plain.data["backgroundColor"] != lit.data["backgroundColor"]


def references(scene):
    """Every id one element holds about another, which all have to resolve."""
    found = []
    for element in scene.elements:
        if element.data.get("containerId"):
            found.append(element.data["containerId"])
        found += [bound["id"] for bound in element.data.get("boundElements") or []]
        for key in ("startBinding", "endBinding"):
            if element.data.get(key):
                found.append(element.data[key]["elementId"])
    return found


def test_absorbing_a_scene_brings_all_of_its_elements():
    panel = figures.tree("p", ("BinOp", ["Constant 1", "Add", "Constant 2"]))
    scene = Scene("merged")
    scene.absorb(panel)
    assert labels(scene) == labels(panel)


def test_absorbing_a_scene_twice_does_not_reuse_a_single_id():
    # Ids are derived from position and index, so two panels drawn by the same call would
    # collide exactly, and Excalidraw would silently drop half the picture.
    panel = figures.tree("p", ("BinOp", ["Constant 1", "Add", "Constant 2"]))
    scene = Scene("merged")
    scene.absorb(panel)
    scene.absorb(panel, dx=400)
    ids = [element.id for element in scene.elements]
    assert len(ids) == len(set(ids))


def test_every_reference_still_resolves_after_a_merge():
    # A label whose containerId was not remapped comes loose from its box, which renders
    # as a picture with the words in the wrong places rather than as an error.
    panel = figures.pipeline("p", [("a", ""), ("b", "")])
    scene = Scene("merged")
    scene.absorb(panel)
    scene.absorb(panel, dy=300)
    known = {element.id for element in scene.elements}
    assert references(scene)
    assert set(references(scene)) <= known


def test_absorbing_moves_everything_by_the_same_offset():
    panel = figures.tree("p", ("BinOp", ["Constant 1", "Add", "Constant 2"]))
    scene = Scene("merged")
    scene.absorb(panel, dx=100, dy=50)
    left, top, right, bottom = panel.bounds()
    assert scene.bounds() == (left + 100, top + 50, right + 100, bottom + 50)


def test_absorbing_leaves_the_original_untouched():
    panel = figures.tree("p", "Constant 1")
    before = panel.bounds()
    Scene("merged").absorb(panel, dx=100, dy=50)
    assert panel.bounds() == before


def test_panels_are_laid_out_left_to_right_without_overlapping():
    left = figures.tree("a", ("BinOp", ["Constant 1", "Add", "Constant 2"]))
    right = figures.tree("b", "Constant 3")
    scene = figures.beside("t", [("first", left), ("second", right)])
    first = box_named(scene, "Constant 2")
    second = box_named(scene, "Constant 3")
    assert first.box[2] < second.box[0]


def test_each_panel_gets_its_own_heading():
    scene = figures.beside(
        "t",
        [("first", figures.tree("a", "Constant 1")), ("second", figures.tree("b", "Constant 2"))],
    )
    assert {"first", "second"} <= set(labels(scene))


def test_panels_start_at_the_same_height_however_tall_they_are():
    short = figures.tree("a", "Constant 1")
    tall = figures.tree("b", ("Assign", [("BinOp", ["Constant 2", "Add", "Constant 3"])]))
    scene = figures.beside("t", [("short", short), ("tall", tall)])
    assert box_named(scene, "Constant 1").box[1] == box_named(scene, "Assign").box[1]


def panel_named(scene, label):
    """The container rectangle drawn immediately before a given free floating label.

    `nest` draws each container as a rectangle and then its name as loose text, so the
    rectangle is the element added just before the text that names it.
    """
    for index, element in enumerate(scene.elements):
        if element.data["type"] == "text" and element.data["text"] == label:
            return scene.elements[index - 1]
    raise AssertionError(f"no panel called {label!r}")


def test_every_container_and_leaf_in_a_nest_gets_drawn():
    scene = figures.nest("n", ("module", ["answer", ("def f():", ["total"])]))
    assert set(labels(scene)) == {"module", "answer", "def f():", "total"}


def test_a_child_is_drawn_inside_its_container():
    scene = figures.nest("n", ("module", [("def f():", ["total"])]))
    outer = panel_named(scene, "module")
    inner = panel_named(scene, "def f():")
    assert outer.box[0] < inner.box[0]
    assert outer.box[2] > inner.box[2]
    assert outer.box[3] > inner.box[3]


def test_a_container_is_drawn_before_the_things_inside_it():
    # SVG has no z index, so a container added after its contents paints over them.
    scene = figures.nest("n", ("module", ["answer"]))
    ids = [element.id for element in scene.elements]
    assert ids.index(panel_named(scene, "module").id) < ids.index(box_named(scene, "answer").id)


def test_siblings_in_a_nest_do_not_overlap():
    scene = figures.nest("n", ("module", ["one", "two", "three"]))
    boxes = sorted(
        (box_named(scene, name).box for name in ["one", "two", "three"]), key=lambda b: b[1]
    )
    for before, after in pairwise(boxes):
        assert before[3] <= after[1]


def test_siblings_in_a_nest_are_all_the_same_width():
    scene = figures.nest("n", ("module", ["a", "a much longer row than the other one"]))
    first = box_named(scene, "a").box
    second = box_named(scene, "a much longer row than the other one").box
    assert first[2] - first[0] == second[2] - second[0]


def test_a_container_grows_to_hold_a_deeper_child():
    shallow = figures.nest("a", ("module", ["one"]))
    deep = figures.nest("b", ("module", [("def f():", [("def g():", ["one"])])]))
    assert panel_named(deep, "module").box[3] > panel_named(shallow, "module").box[3]


def test_nesting_deeper_than_the_palette_reuses_the_last_tone():
    # Four tones and five levels has to give a colour rather than an IndexError.
    scene = figures.nest("n", ("a", [("b", [("c", [("d", ["e"])])])]))
    assert box_named(scene, "e").data["backgroundColor"]
