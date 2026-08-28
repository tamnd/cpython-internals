"""Tests for the figure library, the gallery and the command.

The figure tests are mostly about layout invariants that a reader would notice and a type
checker would not: labels that must not collide, a stack whose top is drawn at the top.
"""

from __future__ import annotations

import json
from itertools import pairwise

import pytest

from nbdiagram import figures
from nbdiagram.cli import main, scripts, write
from nbdiagram.gallery import RAW, Gallery
from nbdiagram.link import Diagrams
from nbdiagram.scene import Scene


def test_a_pipeline_gives_every_stage_the_same_width():
    scene = figures.pipeline("p", [("a", ""), ("a much longer stage name", "")])
    boxes = [e for e in scene.elements if e.data["type"] == "rectangle"]
    assert len({box.data["width"] for box in boxes}) == 1


def test_a_pipeline_has_one_arrow_between_each_pair():
    scene = figures.pipeline("p", [("a", ""), ("b", ""), ("c", "")])
    arrows = [e for e in scene.elements if e.data["type"] == "arrow"]
    assert len(arrows) == 2


def test_a_highlighted_stage_is_the_only_one_in_the_focus_tone():
    scene = figures.pipeline("p", [("a", ""), ("b", ""), ("c", "")], highlight=1)
    boxes = [e for e in scene.elements if e.data["type"] == "rectangle"]
    assert boxes[1].data["backgroundColor"] != boxes[2].data["backgroundColor"]


def test_a_stage_with_no_source_line_gets_no_caption():
    with_source = figures.pipeline("p", [("a", "Parser/lexer/lexer.c")])
    without = figures.pipeline("p", [("a", "")])
    assert len(with_source.elements) == len(without.elements) + 1


def test_a_flow_runs_down_the_page():
    scene = figures.flow("f", ["a", "b", "c"])
    boxes = [e for e in scene.elements if e.data["type"] == "rectangle"]
    tops = [box.data["y"] for box in boxes]
    assert tops == sorted(tops)


def test_a_stack_draws_the_top_of_the_stack_at_the_top():
    # Half the stack diagrams in circulation are upside down relative to the prose next to
    # them, and readers lose an hour to it.
    scene = figures.stack("s", ["bottom", "middle", "top"])
    labels = [e for e in scene.elements if e.data["type"] == "text"]
    assert labels[0].data["text"] == "top"


def test_span_labels_never_overlap():
    scene = figures.spans(
        "s", "    return x + 1", [(0, 4, "INDENT"), (4, 10, "NAME"), (11, 12, "NAME")]
    )
    chips = [e for e in scene.elements if e.data["type"] == "rectangle"]
    for before, after in pairwise(chips):
        assert before.box[2] <= after.box[0]


def test_every_span_gets_a_ribbon_down_to_its_label():
    marks = [(0, 4, "INDENT"), (4, 10, "NAME")]
    scene = figures.spans("s", "    return", marks)
    bands = [e for e in scene.elements if e.data.get("polygon")]
    assert len(bands) == len(marks)


def test_ribbons_are_in_the_same_order_at_both_ends():
    # This is the property that makes them impossible to cross, so it is worth asserting
    # rather than trusting.
    marks = [(0, 4, "INDENT"), (4, 10, "NAME"), (11, 12, "NAME"), (13, 14, "OP")]
    scene = figures.spans("s", "    return x + 1", marks)
    bands = [e for e in scene.elements if e.data.get("polygon")]
    tops = [band.data["x"] for band in bands]
    assert tops == sorted(tops)


def test_a_comparison_has_the_same_number_of_rows_on_each_side():
    scene = figures.compare("c", ("left", ["a", "b"]), ("right", ["c", "d"]))
    boxes = [e for e in scene.elements if e.data["type"] == "rectangle"]
    assert len(boxes) == 4


def test_a_verdict_spans_both_columns():
    scene = figures.compare("c", ("left", ["a"]), ("right", ["b"]), verdict="so they differ")
    boxes = [e for e in scene.elements if e.data["type"] == "rectangle"]
    assert boxes[-1].data["width"] > boxes[0].data["width"]


def test_a_verdict_long_enough_to_wrap_still_fits_inside_its_box():
    scene = figures.compare(
        "c",
        ("left", ["a"]),
        ("right", ["b"]),
        verdict="a verdict long enough that it has to run onto a second line to fit",
    )
    box = [e for e in scene.elements if e.data["type"] == "rectangle"][-1]
    label = next(e for e in scene.elements if e.data.get("containerId") == box.id)
    assert label.box[3] <= box.box[3]


def test_a_gallery_refuses_two_diagrams_with_one_name(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    gallery.add(Scene("same"))
    with pytest.raises(ValueError, match="same"):
        gallery.add(Scene("same"))


def test_an_image_link_is_absolute_so_that_colab_can_load_it(tmp_path):
    # Colab has no idea which repository a notebook came from, so a relative path is a
    # broken image for every reader who clicks the badge.
    gallery = Gallery("t99", root=tmp_path)
    gallery.add(Scene("one"))
    link = gallery.image("one", "a picture")
    assert link == f"![a picture]({RAW}/lessons/t99/diagrams/one.svg)"


def test_asking_for_a_diagram_that_does_not_exist_is_an_error(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    with pytest.raises(KeyError):
        gallery.image("missing", "a picture")


def test_saving_writes_both_files(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    scene = Scene("one")
    scene.box("a", 0, 0)
    gallery.add(scene)
    assert gallery.save([]) == 0
    assert (gallery.directory / "one.excalidraw").exists()
    assert (gallery.directory / "one.svg").exists()


def test_checking_a_diagram_that_was_never_built_fails(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    gallery.add(Scene("one"))
    assert gallery.save(["--check"]) == 1


def test_checking_a_diagram_that_has_drifted_fails(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    scene = Scene("one")
    scene.box("a", 0, 0)
    gallery.add(scene)
    gallery.save([])
    (gallery.directory / "one.svg").write_text("<svg/>")
    assert gallery.save(["--check"]) == 1


def test_a_freshly_built_diagram_checks_clean(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    scene = Scene("one")
    scene.box("a", 0, 0)
    gallery.add(scene)
    gallery.save([])
    assert gallery.save(["--check"]) == 0


def test_write_reports_the_recipe_that_fixes_it(tmp_path):
    scene = Scene("one")
    scene.box("a", 0, 0)
    write(scene, tmp_path)
    (tmp_path / "one.svg").write_text("<svg/>")
    assert "just diagrams" in write(scene, tmp_path, check=True)[0]


def test_the_written_excalidraw_is_json(tmp_path):
    scene = Scene("one")
    scene.box("a", 0, 0)
    write(scene, tmp_path)
    json.loads((tmp_path / "one.excalidraw").read_text())


def test_a_lesson_links_a_diagram_it_has_actually_built(tmp_path):
    (tmp_path / "lessons" / "t99" / "diagrams").mkdir(parents=True)
    (tmp_path / "lessons" / "t99" / "diagrams" / "one.svg").write_text("<svg/>")
    link = Diagrams("t99", root=tmp_path).figure("one", "a picture")
    assert link == f"![a picture]({RAW}/lessons/t99/diagrams/one.svg)"


def test_a_lesson_linking_a_diagram_that_was_never_drawn_fails_at_build_time(tmp_path):
    # Better here than in the notebook, where it would be a broken image nobody notices
    # until a reader opens the lesson in Colab.
    with pytest.raises(KeyError, match="missing"):
        Diagrams("t99", root=tmp_path).figure("missing", "a picture")


def test_the_lesson_side_and_the_gallery_side_agree_on_the_url(tmp_path):
    gallery = Gallery("t99", root=tmp_path)
    gallery.add(Scene("one"))
    (tmp_path / "lessons" / "t99" / "diagrams").mkdir(parents=True)
    (tmp_path / "lessons" / "t99" / "diagrams" / "one.svg").write_text("<svg/>")
    assert gallery.image("one", "a picture") == Diagrams("t99", root=tmp_path).figure(
        "one", "a picture"
    )


def test_scripts_are_found_in_lesson_order(tmp_path):
    for slug in ["t03", "t01", "t02"]:
        (tmp_path / slug).mkdir()
        (tmp_path / slug / "diagrams.py").write_text("")
    assert [path.parent.name for path in scripts(tmp_path)] == ["t01", "t02", "t03"]


def test_a_tree_with_no_diagram_scripts_is_not_a_failure(tmp_path, capsys):
    assert main(["build", "--root", str(tmp_path)]) == 0
    assert "no diagrams.py" in capsys.readouterr().err


def test_a_failing_script_fails_the_command(tmp_path):
    (tmp_path / "t01").mkdir()
    (tmp_path / "t01" / "diagrams.py").write_text("raise SystemExit(1)\n")
    assert main(["build", "--root", str(tmp_path)]) == 1


def test_a_command_with_no_subcommand_is_a_misuse(capsys):
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
