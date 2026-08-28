"""Turning a citation into something a reader can click.

The lessons cite CPython source constantly. In a notebook that citation has to become a
link, and the link has to be right, which means the same parser CI uses builds it. If a
notebook built its own URLs there would be two implementations of the format and only one
of them would be checked.
"""

from __future__ import annotations

from refcheck.citation import Citation

__all__ = ["Citation", "link", "markdown", "url"]


def url(citation: str) -> str:
    """The GitHub permalink for a citation."""
    return Citation.parse(citation).github_url()


def markdown(citation: str, label: str | None = None) -> str:
    """A markdown link, for building a cell's text from code."""
    return Citation.parse(citation).markdown_link(label)


class link:
    """A clickable citation, for returning as the value of a notebook cell.

    Renders as a link in a notebook and as the plain citation in a terminal, so the same
    object works in Colab, in marimo and in a plain REPL.
    """

    def __init__(self, citation: str, label: str | None = None) -> None:
        self.citation = Citation.parse(citation)
        self.label = label

    def __repr__(self) -> str:
        return f"{self.label or self.citation.short()}  {self.citation.github_url()}"

    def _repr_html_(self) -> str:
        text = self.label or self.citation.short()
        symbol = f" <em>{self.citation.symbol}</em>" if self.citation.symbol else ""
        return (
            f'<a href="{self.citation.github_url()}" target="_blank">'
            f"<code>{text}</code></a>{symbol}"
        )

    def _repr_markdown_(self) -> str:
        return self.citation.markdown_link(self.label)
