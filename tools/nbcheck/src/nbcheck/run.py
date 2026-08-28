"""Executing a notebook and reporting the first cell that failed.

The point of this is not that the notebook produces the right answer, it is that every
cell a reader will run still runs at all. A lesson whose fourth cell raises is worse than
no lesson, because the reader assumes they broke it.

Nothing is written back to the file. Outputs are not committed, so an execution that
succeeded leaves no trace except an exit code, which is exactly what CI wants.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Failure:
    """A cell that raised, with enough context to find it without opening the notebook."""

    path: Path
    cell: int | None
    error: str
    source: str = ""

    def __str__(self) -> str:
        where = f"{self.path}" if self.cell is None else f"{self.path}:cell {self.cell}"
        first = self.source.strip().splitlines()[0] if self.source.strip() else ""
        opening = f"\n    running: {first}" if first else ""
        return f"{where}: {self.error}{opening}"


def execute(path: Path, *, timeout: int = 300) -> Failure | None:
    """Run every cell in order. Returns the first failure, or None if the whole file ran.

    The kernel starts in the notebook's own directory, the same as it would in Colab and
    in Jupyter, so a relative path that works for the reader works here too.
    """
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    book = nbformat.read(path, as_version=4)
    client = NotebookClient(
        book,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
        allow_errors=False,
    )
    try:
        client.execute()
    except CellExecutionError as error:
        number, source = _locate(book)
        return Failure(path=path, cell=number, error=_readable(str(error)), source=source)
    except Exception as error:  # a dead kernel, a missing dependency, a timeout
        return Failure(path=path, cell=None, error=f"{type(error).__name__}: {error}")
    return None


def _locate(book) -> tuple[int | None, str]:
    """Find the cell that failed by looking for the one that produced an error output.

    nbclient raises with the traceback but not with the cell index, and the index is the
    thing an author needs first. The executed copy in memory has the error attached to the
    cell that produced it, so the answer is in there.
    """
    for number, cell in enumerate(book.cells, start=1):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                return number, cell.get("source", "")
    return None, ""


def _readable(message: str) -> str:
    """Keep the exception line, drop the frames the reader did not write.

    A full nbclient traceback is thirty lines of nbclient's own stack with the actual
    error at the bottom. The last non empty line is almost always the one that matters.
    """
    lines = [line for line in message.splitlines() if line.strip()]
    if not lines:
        return "the cell failed with no message"
    return lines[-1].strip()
