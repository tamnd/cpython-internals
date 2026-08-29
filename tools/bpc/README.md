# bpc

The blueprint compiler. It writes the mechanical parts of a blueprint from CPython's own inputs, so that nobody types out 113 node kinds by hand and nobody has to notice when upstream adds a field. Run with `just build-blueprints`, and `just blueprints` checks that what is committed still matches.

```
uv run bpc list
uv run bpc build
uv run bpc check
```

## Why this exists

A blueprint is two kinds of writing in one file. Sections 3, 4, 6, 7 and 9 are somebody's understanding of a subsystem, and there is no generating those. Sections 1, 2 and 5 of [BP-AST](../../blueprints/BP-AST.md) are a table of every type, every constructor and every field in `Parser/Python.asdl`, and that is transcription. Transcription is right on the day it is typed and wrong the first time the grammar changes, which for the AST is most releases.

So the prose lives in `blueprints/sources/BP-AST.md` with a one line directive where each generated block belongs, and `bpc build` swaps each directive for the block and writes `blueprints/BP-AST.md`. Both files are committed. The output is what people read and what refcheck and bpcheck lint, and the source is what people edit.

## The directives

A directive is an HTML comment on a line of its own:

```
<!-- bpc: overview -->
```

There are four blocks. `overview` is section 1: the counts, and a row per type with a citation to the line it is declared on. `nodes` is section 2: a subsection per type, with a row per field of every constructor. `observable` is section 5: what the `ast` module shows of all this, with `_fields` and `_attributes` for every class. `conformance` is section 8: the table of claims and the tests that hold them up, with the counts filled in from the grammar.

The expanded file keeps the boundary visible:

```
<!-- bpc:begin overview -->
...generated...
<!-- bpc:end overview -->
```

That is what makes "no hand written content in a generated section" something a reader can check rather than something everybody has to remember. Editing between the markers is safe in the sense that nothing breaks immediately, and pointless in the sense that `bpc check` fails on the next run and the next build throws the edit away.

## Where the line numbers come from

CPython ships an ASDL parser at `Parser/asdl.py`, and `bpc` imports it from the pinned checkout rather than parsing the grammar itself. A second parser would be a second opinion about what the grammar means, and the reason to generate this material at all is that there should be one.

What `asdl.py` does not give back is where anything was written. It parses to a tree of `Module`, `Type`, `Constructor` and `Field` with no line numbers anywhere. So `model.py` runs `asdl.py`'s own tokenizer a second time, which does carry line numbers, and walks the two in step. A definition is found by looking for a type name followed by `=`, which is what separates `arg` being declared on line 119 from `arg` being used as a field type on line 116. Anything the walk cannot follow raises rather than guessing, because a citation that points at the wrong line is worse than no citation.

The result is that every citation in sections 1 and 2 points at a single line, and the name being cited is on it. If upstream moves a definition, the symbol is no longer where the citation says and `just citations` fails, instead of quietly pointing at whatever moved into that slot.

## Layout

```
src/bpc/
  model.py     the grammar as plain data, with line numbers attached
  render.py    grammar in, markdown out, no state and no file access
  template.py  swapping directives for blocks, and the errors when that goes wrong
  cli.py       build, check and list
tests/
  test_bpc_conformance.py   the grammar against the running interpreter's ast module
```

`render.py` is pure, which is what makes the output deterministic: run it twice on the same pin and the bytes are identical, so a diff means the pin moved and nothing else.

## The conformance tests

`tests/test_bpc_conformance.py` is the half that checks the generated material is true rather than merely consistent. It reads the grammar from the pinned tree and compares it against the `ast` module of the interpreter running the tests: every type and constructor is a class, `_fields` and `_attributes` are the grammar's names in the grammar's order, and leaving a field out does what section 5 says.

Those tests skip when the running interpreter's version does not match the pinned tag. A difference between `v3.15.0rc1` and whatever else is installed is a fact about the two versions, not a failure of the document, and failing the build for it would mean nobody could run the suite on anything but one interpreter.

## What it does not do

It does not lint. [bpcheck](../bpcheck) checks the structure of the output, and it lints `blueprints/BP-AST.md` without knowing it was generated, which is the point. It does not resolve citations, which [refcheck](../refcheck) does for every root in the repository. It does not repair drift on its own: `bpc check` reports and exits non zero, because a checker that silently fixes what it finds checks nothing, and the diff is the thing somebody is supposed to read before the pin moves.
