"""The nine blocks and the word caps, checked on notebooks built for the purpose.

Every test here builds the smallest notebook that shows the thing being tested, rather than
reaching for a real lesson. A real lesson would pass everything, which makes it useless for
proving a check fires, and it would also mean these tests fail the day somebody edits it.
"""

from __future__ import annotations

from pathlib import Path

from notebook_fixtures import code, markdown, write

from nbcheck.blocks import (
    HOOK,
    LESSON,
    TOUR,
    VERSIONS,
    measurements,
    problems,
    sections,
    shape,
    words,
)
from nbcheck.notebook import load


def prose(count: int) -> str:
    """A paragraph of exactly `count` words, for pushing a section over a cap on purpose."""
    return " ".join(["word"] * count)


def lesson_cells(
    *,
    hook: str = "A short hook with a question in it.",
    tour: str = "Some tour prose.",
    picture: bool = True,
    fight: bool = False,
    closing: tuple[str, str, str] = (
        "Try it yourself",
        "What just happened",
        "Where this goes next",
    ),
) -> list[dict]:
    """A notebook with all nine blocks in the right order, for tests that break one of them."""
    image = "\n\n![a diagram](figures/one.svg)" if picture else ""
    cells = [
        markdown(f"# A lesson\n\n{hook}\n"),
        markdown("## About the source references\n\nGenerated front matter.\n"),
        markdown("## Setup\n\nGenerated too.\n"),
        code("%pip install -q pyxray\n"),
        markdown("## Which Python is this\n\nThe version prose.\n"),
        code("import pyxray\n\npyxray.show()\n"),
        markdown(f"## The middle of it\n\n{tour}{image}\n"),
        code("print(6 * 7)\n"),
        markdown(f"## {closing[0]}\n\nThree exercises.\n"),
    ]
    if fight:
        cells.append(markdown("## Boss fight\n\nGo and write the thing.\n"))
    cells.append(markdown(f"## {closing[1]}\n\nThe recap.\n"))
    cells.append(markdown(f"## {closing[2]}\n\nThe next lesson.\n"))
    return cells


def built(tmp_path: Path, cells: list[dict], *, grader: bool = False) -> tuple:
    """Write a notebook where a lesson lives, and hand back what the checks want."""
    path = tmp_path / "lessons" / "t00-a-lesson" / "t00.ipynb"
    write(path, cells)
    if grader:
        (path.parent / "grade.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    return load(path), path


def test_a_lesson_with_every_block_in_order_has_nothing_wrong_with_it(tmp_path):
    book, path = built(tmp_path, lesson_cells())
    assert problems(book, path) == []


def test_code_fences_are_not_prose_because_nobody_reads_them_as_sentences():
    assert words("one two three\n\n```\nnot counted at all here\n```\n") == 3


def test_an_image_buys_no_room_because_a_picture_is_not_words():
    assert words("one two ![a very long piece of alt text](figures/one.svg) three") == 3


def test_a_link_counts_as_its_text_and_not_its_address():
    assert words("go and read [the tokenizer](https://github.com/python/cpython/blob/x/y.c)") == 5


def test_html_is_dropped_so_a_table_does_not_count_as_prose():
    assert words("<table><tr><td>one</td></tr></table> two three") == 3


def test_sections_split_on_the_heading_and_not_on_the_cell_it_arrived_in(tmp_path):
    book, _ = built(
        tmp_path,
        [
            markdown("# A lesson\n\nThe hook.\n"),
            markdown("Trailing prose.\n\n## A heading\n\nAnd the section under it.\n"),
        ],
    )
    found = sections(book)
    assert [one.name for one in found] == ["", "A heading"]
    assert "Trailing prose." in "\n".join(found[0].prose)


def test_the_generated_front_matter_is_not_charged_to_the_lesson(tmp_path):
    plain, _ = built(tmp_path, lesson_cells())
    heavy = lesson_cells()
    heavy[1] = markdown(f"## About the source references\n\n{prose(500)}\n")
    padded, _ = built(tmp_path, heavy)
    assert measurements(padded)["lesson"] == measurements(plain)["lesson"]


def test_the_version_section_counts_towards_the_lesson_but_not_the_tour(tmp_path):
    cells = lesson_cells()
    cells[4] = markdown(f"## Which Python is this\n\n{prose(400)}\n")
    book, _ = built(tmp_path, cells)
    sizes = measurements(book)
    assert sizes["tour"] < 400
    assert sizes["lesson"] > 400


def test_the_tour_stops_at_the_exercises_so_the_ending_is_not_part_of_it(tmp_path):
    cells = lesson_cells()
    cells[8] = markdown(f"## Try it yourself\n\n{prose(400)}\n")
    book, _ = built(tmp_path, cells)
    assert measurements(book)["tour"] < 400


def test_a_long_hook_is_named_along_with_the_cap_it_went_over(tmp_path):
    book, path = built(tmp_path, lesson_cells(hook=prose(HOOK + 1)))
    assert any(f"the cap is {HOOK}" in one for one in problems(book, path))


def test_a_long_tour_is_reported_as_two_lessons_rather_than_one(tmp_path):
    book, path = built(tmp_path, lesson_cells(tour=prose(TOUR + 1)))
    said = problems(book, path)
    assert any("usually two lessons" in one for one in said)


def test_a_long_lesson_is_reported_even_when_no_single_section_is_long(tmp_path):
    cells = lesson_cells()
    cells[4] = markdown(f"## Which Python is this\n\n{prose(LESSON - TOUR + 100)}\n")
    cells[6] = markdown(f"## The middle of it\n\n{prose(TOUR)}\n\n![a diagram](figures/one.svg)\n")
    book, path = built(tmp_path, cells)
    said = problems(book, path)
    assert any("words of prose" in one for one in said)
    assert not any("the tour is" in one for one in said)


def test_a_lesson_that_opens_on_a_heading_has_no_hook(tmp_path):
    book, path = built(tmp_path, lesson_cells()[1:])
    assert any("no hook" in one or "title cell" in one for one in problems(book, path))


def test_a_tour_with_no_picture_is_a_problem_because_every_lesson_gets_one(tmp_path):
    book, path = built(tmp_path, lesson_cells(picture=False))
    assert any("no picture" in one for one in problems(book, path))


def test_an_animation_counts_as_the_picture_because_it_is_written_the_same_way(tmp_path):
    cells = lesson_cells(picture=False)
    cells[6] = markdown("## The middle of it\n\nProse.\n\n![the animation](media/one.gif)\n")
    book, path = built(tmp_path, cells)
    assert problems(book, path) == []


def test_a_missing_ending_is_named_by_the_heading_somebody_has_to_add(tmp_path):
    cells = [one for one in lesson_cells() if "What just happened" not in str(one["source"])]
    book, path = built(tmp_path, cells)
    assert any("What just happened" in one for one in problems(book, path))


def test_the_older_names_for_the_closing_sections_still_pass(tmp_path):
    older = ("Exercises", "What you now know", "What is next")
    book, path = built(tmp_path, lesson_cells(closing=older))
    assert problems(book, path) == []


def test_a_recap_before_the_exercises_is_out_of_order(tmp_path):
    cells = lesson_cells()
    cells[8], cells[9] = cells[9], cells[8]
    book, path = built(tmp_path, cells)
    assert any("out of order" in one for one in problems(book, path))


def test_a_grader_nobody_links_to_is_a_boss_fight_the_reader_never_finds(tmp_path):
    book, path = built(tmp_path, lesson_cells(), grader=True)
    assert any("grade.py" in one for one in problems(book, path))


def test_a_boss_fight_between_the_exercises_and_the_recap_is_where_it_belongs(tmp_path):
    book, path = built(tmp_path, lesson_cells(fight=True), grader=True)
    assert problems(book, path) == []


def test_a_boss_fight_after_the_recap_is_in_the_wrong_place(tmp_path):
    cells = lesson_cells(fight=True)
    cells[9], cells[10] = cells[10], cells[9]
    book, path = built(tmp_path, cells, grader=True)
    assert any("wrong place" in one for one in problems(book, path))


def test_the_shape_of_a_real_lesson_is_the_shape_the_checks_expect():
    book = load(Path("lessons/t01-one-line-seven-stages/t01.ipynb"))
    one = shape(book)
    assert one.title.name == ""
    assert one.index(VERSIONS) is not None
    assert len(one.tour) > 1
