from __future__ import annotations

import dis
import opcode
import sys

from pyxray import _opcodes


def test_every_real_opcode_number_has_a_name():
    for number, name in enumerate(opcode.opname):
        if name.startswith("<"):
            continue
        assert _opcodes.opcode_name(number) == name


def test_pseudo_instructions_are_named_too():
    """`opcode.opname` stops at 255 and the compiler's own sequences go past it."""
    pseudo = {name: number for name, number in opcode.opmap.items() if number > 255}
    assert pseudo, "this release has no pseudo instructions, which would be a real change"
    for name, number in pseudo.items():
        assert _opcodes.opcode_name(number) == name
        assert _opcodes.is_pseudo(number)


def test_a_number_that_is_not_an_opcode_says_so_rather_than_raising():
    assert _opcodes.opcode_name(9999) == "<9999>"


def test_real_opcodes_are_not_pseudo():
    assert not _opcodes.is_pseudo(opcode.opmap["NOP"])
    assert not _opcodes.is_pseudo(255)
    assert _opcodes.is_pseudo(256)


def test_specialized_forms_point_back_at_what_the_compiler_emitted():
    from _opcode_metadata import _specializations

    assert _specializations, "no specialization table, so the interpreter cannot specialize"
    for base, specials in _specializations.items():
        for special in specials:
            assert _opcodes.is_specialized(special)
            assert _opcodes.base_name(special) == base


def test_an_unspecialized_name_is_its_own_base():
    assert not _opcodes.is_specialized("NOP")
    assert _opcodes.base_name("NOP") == "NOP"
    assert _opcodes.base_name("NOT_AN_OPCODE") == "NOT_AN_OPCODE"


def test_the_family_of_an_opcode_is_reachable_from_any_member():
    from _opcode_metadata import _specializations

    base, specials = next(iter(_specializations.items()))
    assert _opcodes.family(base) == tuple(specials)
    assert _opcodes.family(specials[0]) == tuple(specials)


def test_an_opcode_with_no_family_reports_an_empty_one():
    assert _opcodes.family("NOP") == ()
    assert _opcodes.family("NOT_AN_OPCODE") == ()


def test_cache_counts_come_from_the_table_dis_uses():
    for name, count in dis._inline_cache_entries.items():
        assert _opcodes.cache_entries(name) == count


def test_the_instructions_that_learn_are_the_ones_that_carry_a_cache():
    """Caches are where the interpreter keeps what it learned about this call site."""
    assert _opcodes.cache_entries("BINARY_OP") > 0
    assert _opcodes.cache_entries("LOAD_ATTR") > 0
    assert _opcodes.cache_entries("NOP") == 0
    assert _opcodes.cache_entries("NOT_AN_OPCODE") == 0


def test_resume_grew_a_cache_entry_in_3_15():
    """A version delta that would silently shift every offset in a hand counted lesson.

    RESUME is the first instruction of almost every code object. In 3.14 it occupied two
    bytes, in 3.15 it occupies four, so any prose that walks offsets by hand from a 3.14
    disassembly is off by two from its second instruction onward.
    """
    expected = 1 if sys.version_info >= (3, 15) else 0
    assert _opcodes.cache_entries("RESUME") == expected


def test_has_argument_agrees_with_the_interpreter():
    import _opcode

    for number in range(256):
        if opcode.opname[number].startswith("<"):
            continue
        assert _opcodes.has_argument(number) == bool(_opcode.has_arg(number))


def test_load_small_int_takes_its_value_as_the_argument():
    """The instruction that made LOAD_CONST unnecessary for small integers."""
    assert "LOAD_SMALL_INT" in opcode.opmap
    assert _opcodes.has_argument(opcode.opmap["LOAD_SMALL_INT"])
