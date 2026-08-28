# bpcheck

Structural checks for the documents in [blueprints/](../../blueprints). Run with `just blueprints`, and it runs as part of `just check`.

```
uv run bpcheck lint
uv run bpcheck lint blueprints/BP-PIPELINE.md
```

A lesson that is wrong in a small way is annoying. A blueprint that is wrong in a small way is worse, because the reader is typing code against it and will read a missing section as a subsystem with nothing to say rather than as an omission. Each rule below is a way a specification quietly stops being one.

## The rules

**title.** The file is `BP-NAME.md` and the first line is `# BP-NAME: what it covers`. The two names have to agree, because the invariant identifiers are derived from the file name and a reader who follows a link expects to land on what the link said.

**header.** The four fields `Covers`, `Lesson`, `Status` and `Compatibility tier`, in that order, directly under the title. `Status` is `complete`, `partial` or `stub`. `Compatibility tier` is `A`, `B`, `C` or `D`.

**sections.** The nine sections, with these exact titles, in this order, and nothing else at the `##` level: purpose and scope, data structures, algorithms, invariants, observable behaviour, edge cases and error paths, interactions, conformance, port notes. The order is part of the format. Somebody who has read one blueprint knows where the invariants are in all of them, and that only holds if nothing is ever moved.

**empty-section.** A section with a heading and no body is worse than one that says "nothing here yet", because a reader cannot tell the difference between "no interactions" and "nobody got to it".

**invariant-slug**, **invariant-numbering**, **unknown-invariant.** Invariants are stated in section 4 as `**INV-NAME-001.**` and up, they run from 001 with no gaps and no repeats, the name matches the file, and anything referred to elsewhere in the document as `INV-NAME-NNN` is actually stated. The numbering rule exists so that an invariant can be cited from a test or from another blueprint and stay citable.

**untagged-citation.** A citation without its `@tag`, like `Python/ceval.c:1213` with nothing after it, is invisible to [refcheck](../refcheck) and is therefore never resolved and never noticed going stale. That is worse than having no citation at all, because it looks checked.

**deferral.** A blueprint may not send the reader to a lesson for a fact. If something is needed to implement the subsystem it goes in the blueprint, even where that repeats a lesson word for word. Section 8 is exempt, since naming the lesson that holds a claim up is exactly what that section is for.

**punctuation** and **page-break.** No em dashes, no en dashes, no horizontal rules, the same as everywhere else in the project. Table separators like `|---|` are not horizontal rules and are fine.

**index.** Every `BP-*.md` in the directory is linked from `blueprints/README.md`. This is the rule that stops the directory and its index from drifting apart, which is the failure that makes a reader assume a blueprint that exists was never written.

## What it does not check

It does not resolve citations, since [refcheck](../refcheck) does that against the pinned tree for every root in the repository including this one. It does not check the pseudocode, because the notation in [NOTATION.md](../../blueprints/NOTATION.md) has no parser and does not need one. It does not check that a blueprint is correct, which is what section 8 of each blueprint is for.
