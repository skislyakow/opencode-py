from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class _NotGiven:
    def __repr__(self) -> str:
        return "NOT_GIVEN"

    def __copy__(self) -> _NotGiven:
        return self

    def __reduce__(self) -> str:
        return "NOT_GIVEN"

    @classmethod
    def __class_getitem__(cls, item: Any) -> _NotGiven:
        return cls()


NOT_GIVEN = _NotGiven()
NotGiven = _NotGiven


def is_given(value: T | NotGiven) -> bool:
    return not isinstance(value, _NotGiven)
