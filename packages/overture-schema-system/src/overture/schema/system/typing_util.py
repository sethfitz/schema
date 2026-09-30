"""Typing utilities for the Overture schema system."""

import types
from typing import Annotated, Any, Literal, NewType, Union, get_args, get_origin

import typing_extensions
from typing_extensions import Sentinel


def collect_types(tp: Any) -> set[type]:  # noqa: ANN401
    """Collect concrete classes referenced by a type annotation.

    Unwraps `Annotated[X, ...]` and `Union[X, Y]` (including `X | Y`) to
    find concrete `type` objects. Used by tag providers to walk
    discriminated-union features (e.g. `Segment`) into their member
    classes.

    Only handles the cases the discovery system encounters today.
    `overture-schema-codegen` has a more capable
    `analyze_type` (`extraction/type_analyzer.py`) that also unwraps
    `NewType`, `Literal`, `list[...]`, `dict[K, V]`, and accumulates
    constraints. A future work item is to consolidate this and the
    similar logic in `overture-schema-cli` against that implementation.

    Parameters
    ----------
    tp
        A type annotation. Typically a class, an `Annotated[...]`
        wrapper, or a discriminated union of classes.

    Returns
    -------
    set[type]
        Concrete classes reachable through `Annotated` and `Union`
        unwrapping. Other type expressions yield an empty set.

    """
    result: set[type] = set()

    def _visit(t: Any) -> None:
        origin = get_origin(t)
        if origin is Annotated:
            _visit(get_args(t)[0])
        elif origin is Union or origin is types.UnionType:
            for arg in get_args(t):
                _visit(arg)
        elif isinstance(t, type):
            result.add(t)

    _visit(tp)
    return result


def is_newtype(annotation: object) -> bool:
    """Whether *annotation* is a `NewType` -- `typing`'s or `typing_extensions`'s.

    `typing_extensions.NewType` is a distinct class from `typing.NewType` on
    Python 3.10/3.11, so a plain `isinstance(x, typing.NewType)` misses
    aliases created through it -- a form third-party schema packages
    legitimately use for cross-version compatibility.
    """
    return isinstance(annotation, (NewType, typing_extensions.NewType))


def literal_values(tp: object) -> tuple[object, ...] | None:
    """Return the values of a `Literal[...]` type expression, or None when not one.

    Recognizes field-level literal expressions only: `Annotated`, `NewType`,
    and transparent union frames (`Literal["x"] | None`) peel on the way, but
    containers deliberately do not -- callers pass arbitrary field annotations
    (`list[...]`, `dict[...]`), and those yield None rather than digging out
    element-level literals. Values are returned raw, so an `Enum` member comes
    back as the member, not its `.value`; garbage never raises.
    """
    while True:
        origin = get_origin(tp)
        if origin is Annotated:
            tp = get_args(tp)[0]
        elif origin is Union or origin is types.UnionType:
            effective_args = [
                arg
                for arg in get_args(tp)
                if arg is not types.NoneType and not isinstance(arg, Sentinel)
            ]
            if len(effective_args) != 1:
                return None
            tp = effective_args[0]
        elif is_newtype(tp):
            tp = tp.__supertype__  # type: ignore[attr-defined]
        else:
            break
    if get_origin(tp) is Literal:
        values: tuple[object, ...] = get_args(tp)
        return values
    return None


def single_literal_value(tp: object) -> object | None:
    """Return the sole value of a `Literal[...]` type expression, or None.

    `literal_values` with an exactly-one requirement: multi-value literals and
    non-literal expressions yield None. `Literal[None]` deliberately collapses
    to None as well -- callers use the result as a discriminator key or a
    name, where None is invalid anyway.
    """
    values = literal_values(tp)
    if values is not None and len(values) == 1:
        return values[0]
    return None
