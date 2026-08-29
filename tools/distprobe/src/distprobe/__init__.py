"""Asks every Python a reader might have whether it ships the compiler hooks the lessons use.

The lessons run the CPython compiler one stage at a time, and that rests on
`_testinternalcapi`, which is a private test module with no compatibility guarantee. Whether
it is there is a packaging decision, made separately by every channel a Python arrives
through, and it is not a decision anybody announces.

So this asks. One question, a dozen channels, a committed answer, and a report a reader who
just hit an ImportError can look their own situation up in.
"""

from .question import Answer, Survey

__all__ = ["Answer", "Survey"]
