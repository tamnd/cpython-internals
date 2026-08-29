"""The fight table, and the paths it works out."""

from __future__ import annotations

import pytest

from boss import FIGHTS, Unknown, find
from boss.fights import REPOSITORY


def test_every_fight_has_a_code_that_matches_its_lesson():
    for one in FIGHTS:
        assert one.lesson.startswith(one.code + "-")


def test_codes_are_unique():
    codes = [one.code for one in FIGHTS]
    assert len(codes) == len(set(codes))


def test_find_is_case_insensitive_because_lessons_are_written_as_t05_and_T05():
    assert find("T05") is find("t05")


def test_find_names_the_fights_there_are_when_asked_for_one_there_is_not():
    with pytest.raises(Unknown) as problem:
        find("t99")
    assert "t05" in str(problem.value)


def test_the_repository_root_is_the_one_with_the_lessons_in_it():
    assert (REPOSITORY / "lessons").is_dir()
    assert (REPOSITORY / "justfile").is_file()


def test_paths_land_where_the_files_actually_are():
    fight = find("t05")
    for where in (
        fight.grader(REPOSITORY),
        fight.starter(REPOSITORY),
        fight.builder(REPOSITORY),
        fight.good(REPOSITORY),
        fight.bad(REPOSITORY),
        fight.expected(REPOSITORY),
    ):
        assert where.is_file(), where


def test_wanted_drops_blank_lines_so_a_trailing_newline_is_not_a_requirement(tmp_path):
    fight = find("t05")
    room = tmp_path / "tools" / "boss" / "submissions" / "t05"
    room.mkdir(parents=True)
    (room / "expected.txt").write_text("first line\n\nsecond line\n\n", encoding="utf-8")
    assert fight.wanted(tmp_path) == ["first line", "second line"]
