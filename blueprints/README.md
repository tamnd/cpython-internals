# Blueprints

A lesson teaches. A blueprint specifies. They cover the same subsystem, they are written together, and they are checked together.

The reason both exist is that prose good enough for a beginner is too loose to implement from. A lesson can say "the compiler folds constant expressions" and be useful. Somebody writing a Python in Go needs to know which expressions, what the size limit is, what happens at the limit, and what the resulting code object looks like. That is a different document with different rules.

## The rules

A blueprint contains no motivation, no analogies, no history and no pictures. It is written for somebody who already understands the subsystem and is now typing.

A blueprint may not point at a lesson for a fact. If something is needed to implement the subsystem it goes in the blueprint, even where that repeats a lesson word for word. A specification that says "see T05 for details" is not a specification.

Every claim about CPython carries a citation into the pinned tree, in the same format the lessons use, and `just citations` resolves all of them. A blueprint that goes stale fails the build rather than misleading somebody who trusted it.

## The nine sections

Every blueprint has these headings, in this order, and `just blueprints` fails if one is missing or out of place.

1. **Purpose and scope.** What this subsystem is responsible for and what it is not. Boundaries with adjacent blueprints, named.
2. **Data structures.** Every struct and field, with its C type and its meaning.
3. **Algorithms.** Pseudocode in the dialect defined in [NOTATION.md](NOTATION.md), with preconditions, postconditions, complexity, and the CPython function each one corresponds to.
4. **Invariants.** Numbered and testable, in the form `INV-PIPELINE-004`.
5. **Observable behaviour.** What a Python program can detect about this subsystem. This is the section that decides the compatibility tier.
6. **Edge cases and error paths.** Empty, one element, maximum size, recursion, reentrancy, allocation failure, shutdown. Including the cases where CPython's behaviour is accidental rather than designed, marked as such.
7. **Interactions.** Which other subsystems depend on this one behaving exactly as described.
8. **Conformance.** The tests that hold each claim up.
9. **Port notes.** What maps directly to Go and Rust, what fights, and what can be generated from upstream rather than typed.

Sections 5, 6 and 7 are the ones that make a blueprint more than a rewrite of the header file. They are also where most of the research goes.

## The header block

Every blueprint opens with the same four fields.

```
**Covers:** the files it specifies, at the pinned tag
**Lesson:** the lesson that teaches the same subsystem
**Status:** complete, partial or stub
**Compatibility tier:** A, B, C or D
```

`Status` is honest rather than aspirational. A stub that says stub is useful. A stub that claims to be complete is a trap.

## The tiers

The tier says how closely a reimplementation has to match this subsystem for a program to stop being able to tell the difference.

**Tier A** means a Python program can observe the exact behaviour and depends on it. Ordinary code breaks if you get it wrong.

**Tier B** means a Python program can observe it, but only code that went looking. Introspection, `sys.getsizeof`, `dis` output.

**Tier C** means it is observable only through timing or memory use.

**Tier D** means it is not observable from Python at all, and a reimplementation is free to do something else entirely.

## What is here

| Blueprint | Covers | Lesson | Status |
|---|---|---|---|
| [BP-MAP](BP-MAP.md) | the architecture every other blueprint hangs off | T10 | complete |
| [BP-PIPELINE](BP-PIPELINE.md) | source text to a running frame, as a contract | T01 | complete |

Thirty more are planned, one per subsystem, listed in the milestone issues. The two here are the ones the rest depend on: `BP-MAP` names the boundaries so that two blueprints cannot both claim the same code, and `BP-PIPELINE` fixes the stage list and what crosses between the stages.

## Checking them

```
just blueprints    # the nine sections, the header block, the invariant IDs
just citations     # every citation resolves against the pinned tree
```
