"""Combine discovered models into a single type for validation or schema generation."""

from functools import reduce
from operator import or_
from typing import Annotated, Any, cast

from pydantic import BaseModel, Field, Tag

from overture.schema.system.discovery.keys import ModelKey
from overture.schema.system.discovery.types import ModelDict
from overture.schema.system.feature import Feature
from overture.schema.system.typing_util import single_literal_value


def model_union(models: ModelDict) -> Any:  # noqa: ANN401
    """Combine models into one type suitable for a Pydantic `TypeAdapter`.

    Models tagged `overture` whose `type` field is a single string literal are
    combined into a union discriminated on `type`, which validates faster and
    reports errors against the one matching model. Every other model joins as a
    plain union member after it.

    Parameters
    ----------
    models : ModelDict
        Models to combine, as returned by `discover_models` or `filter_models`

    Returns
    -------
    Any
        A single model class, or a union type expression over the models

    Raises
    ------
    ValueError
        If `models` is empty
    """
    if not models:
        raise ValueError("No models provided")

    discriminated: list[type[BaseModel]] = []
    others: list[Any] = []
    for key, model_class in models.items():
        if _can_discriminate(model_class, key):
            discriminated.append(model_class)
        else:
            others.append(model_class)

    members = others
    if discriminated:
        members = [_discriminated_union(tuple(discriminated)), *others]
    return reduce(or_, members)


def _can_discriminate(model_class: object, key: ModelKey) -> bool:
    """Check if a model can participate in a discriminated union.

    Returns True if the model is a model class tagged `overture` with a single literal
    'type' value. The class check is separate from the tag: `segment` is tagged
    `overture` but is an `Annotated` union, not a model class.
    """
    return (
        isinstance(model_class, type)
        and issubclass(model_class, BaseModel)
        and "overture" in key.tags
        and _type_literal(model_class) is not None
    )


def _type_literal(feature_class: type[BaseModel]) -> str | None:
    """Extract the literal value from a feature model's 'type' field.

    Returns the literal type value, or None if not a single string literal.
    """
    if "type" not in feature_class.model_fields:
        return None
    value = single_literal_value(feature_class.model_fields["type"].annotation)
    return value if isinstance(value, str) else None


def _discriminated_union(feature_classes: tuple[type[BaseModel], ...]) -> Any:  # noqa: ANN401
    """Create a discriminated union of feature models on the 'type' field."""
    if len(feature_classes) == 1:
        # Single model doesn't need a discriminated union
        return feature_classes[0]

    return Annotated[
        reduce(
            or_,
            (Annotated[f, Tag(cast(str, _type_literal(f)))] for f in feature_classes),
        ),
        Field(discriminator=Feature.field_discriminator("type", *feature_classes)),
    ]
