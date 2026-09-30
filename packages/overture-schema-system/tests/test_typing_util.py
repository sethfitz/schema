"""Unit tests for `typing_util`, the shared type-expression helpers."""

from enum import Enum
from typing import Annotated, Literal, NewType

from pydantic import BaseModel

from overture.schema.system.typing_util import is_newtype, single_literal_value


class Target(BaseModel):
    name: str


class OtherTarget(BaseModel):
    label: str


# ---------------------------------------------------------------------------
# single_literal_value
# ---------------------------------------------------------------------------


class _Kind(str, Enum):
    ROAD = "road"


def test_single_literal_value_forms() -> None:
    assert single_literal_value(Literal["x"]) == "x"
    assert single_literal_value(Annotated[Literal["x"], "meta"]) == "x"
    assert single_literal_value(Literal["x"] | None) == "x"
    assert single_literal_value(NewType("N", Literal["x"])) == "x"
    # Raw value: an Enum member comes back as the member, not its .value.
    assert single_literal_value(Literal[_Kind.ROAD]) is _Kind.ROAD


def test_single_literal_value_absent() -> None:
    assert single_literal_value(Literal["x", "y"]) is None
    assert single_literal_value(str) is None
    assert single_literal_value("garbage") is None
    assert single_literal_value(Target | OtherTarget) is None
    # Literal[None] deliberately collapses to "no single literal".
    assert single_literal_value(Literal[None]) is None


def test_typing_extensions_newtype_recognized() -> None:
    import typing_extensions

    assert is_newtype(typing_extensions.NewType("Aliased", Target)) is True
    assert is_newtype(NewType("N", int)) is True
    assert is_newtype(int) is False
    LitAlias = typing_extensions.NewType("LitAlias", Literal["x"])  # type: ignore[valid-newtype]
    assert single_literal_value(LitAlias) == "x"
