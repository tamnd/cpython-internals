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
check: lint test citations

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
test-3-14:
    uv run --python 3.14 --isolated --with pytest --with ./tools/refcheck --with ./pyxray \
        pytest pyxray/tests -q -p no:cacheprovider

# Resolve every citation in the project against the pinned tree.
citations:
    uv run refcheck verify

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
