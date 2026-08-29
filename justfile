# Every CI job is runnable here under the same name it has in the workflow. If a check
# only exists in CI, contributors find out it failed after they pushed, which is the
# slowest possible feedback loop and the reason the two drift apart.

pinned_tag := "v3.15.0rc1"
cpython_src := env("CPYTHON_SRC", "vendor/cpython")

default:
    @just --list

# Install the workspace and its dev tools.
setup:
    uv sync --all-packages

# Fetch the pinned CPython source. Shallow and blobless, so it is about 200 MB rather
# than several gigabytes, and it is the only thing every citation is checked against.
vendor:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ -d "{{cpython_src}}/.git" ]; then
        echo "already have a checkout at {{cpython_src}}"
    else
        git clone --depth 1 --branch {{pinned_tag}} --filter=blob:none \
            https://github.com/python/cpython.git "{{cpython_src}}"
    fi
    git -C "{{cpython_src}}" rev-parse HEAD

# The full local check, in the order that fails fastest.
check: lint test citations blueprints diagrams lessons notebooks animations

lint:
    uv run ruff check .
    uv run ruff format --check .

fmt:
    uv run ruff format .
    uv run ruff check --fix .

test:
    uv run pytest

# The same suite on the version the browser tier runs. Everything here is written against
# 3.15, and the reader in a Colab or Pyodide tab is on 3.14, so the tests that encode a
# version difference have to be exercised from both sides or they only prove one of them.
#
# The install is editable on purpose. With a plain `--with ./pyxray` uv reuses a wheel it
# built earlier, so edits made since then are silently not tested, and the run passes for
# the wrong reason. That is worse than no second interpreter at all.
test-3-14:
    uv run --python 3.14 --isolated --with pytest --with ./tools/refcheck --with-editable ./pyxray \
        pytest pyxray/tests -q -p no:cacheprovider

# Resolve every citation in the project against the pinned tree.
citations:
    uv run refcheck verify

# Check the blueprints have the shape somebody can implement from: the nine sections in
# order, the header block, the invariant numbering, and no fact deferred to a lesson.
blueprints:
    uv run bpcheck lint

# Confirm every committed diagram still matches the script that draws it. Same deal as the
# notebooks below: the `.excalidraw` and the `.svg` are both generated and both committed,
# because GitHub and Colab render an image from the repository and cannot run a build first.
diagrams:
    uv run nbdiagram check

# Redraw the diagrams after editing a lesson's diagrams.py.
build-diagrams:
    uv run nbdiagram build

# Confirm every committed notebook still matches the builder that produced it. Notebooks
# are generated and also committed, because a reader clicking a Colab badge cannot run a
# build step first, and anything generated and committed drifts unless something checks.
lessons:
    uv run nbbuild check

# Rewrite GLOSSARY.md after editing the terms. There is no separate checker recipe for it,
# because the test suite already compares the committed file against the module, and one
# check that runs everywhere beats two that disagree.
build-glossary:
    uv run pyxray-glossary

# Regenerate the notebooks after editing a builder.
build-lessons:
    uv run nbbuild build

# Check every lesson notebook has the shape a reader needs, then actually run it. The run
# is the slow half, and it is the half that matters: a lesson whose fourth cell raises is
# worse than no lesson, because the reader assumes they broke it.
notebooks:
    uv run nbcheck lint
    uv run nbcheck run

# The structural checks on their own, with no kernel, for while you are still writing.
notebooks-lint:
    uv run nbcheck lint

# Check the animations without a renderer: every storyboard is inside the ninety second
# cap, every shape it draws is in the visual system, and the scene file, the committed GIF
# and the index page all still agree with the plan. Milliseconds, and no manim needed.
animations:
    uv run xraymanim check

# Re-render every animation. Needs `uv sync --extra anim` first, and ffmpeg on PATH. This is
# minutes rather than seconds, which is why it is not part of `check`.
build-animations:
    uv run --extra anim xraymanim render

# Rewrite the citation lockfile after a human has read the diff. This is deliberately
# not part of `check`, because a checker that silently repairs itself checks nothing.
recheck:
    uv run refcheck verify --update
    @echo "read the diff to citations.lock.json before committing it"

# Print the GitHub permalink for a citation, for pasting into prose or a review.
url citation:
    uv run refcheck url "{{citation}}"

# Print the cited lines, so you can confirm a citation says what you think it says.
show citation:
    uv run refcheck show "{{citation}}"
