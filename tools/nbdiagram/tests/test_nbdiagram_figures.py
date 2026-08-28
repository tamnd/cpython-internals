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
