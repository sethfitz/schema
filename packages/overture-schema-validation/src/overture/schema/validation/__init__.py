from functools import reduce
from operator import or_
from types import UnionType
from typing import Annotated, Any, cast

from pydantic import BaseModel, Field, Tag, TypeAdapter

from overture.schema.system.discovery import ModelKey, discover_models
from overture.schema.system.feature import Feature
from overture.schema.system.typing_util import single_literal_value


def validate(data: object) -> BaseModel:
    """
    Validate a Python object, which can be a dictionary or model instance, using the union of all
    discovered Overture models.

    Parameters
    ----------
    data : object
        Python object to validate against the model.

    Returns
    -------
    BaseModel
        Validated model class

    Raises
    ------
    ValidationError
        If `data` is not valid according to one of the discovered Overture models
    """
    tap = _union_type_adapter()

    return cast(BaseModel, tap.validate_python(data))


def validate_json(json_data: str | bytes | bytearray) -> BaseModel:
    """
    Validate JSON data using the union of all discovered Overture models.

    Parameters
    ----------
    json_data : str | bytes | bytearray
        JSON data to validate

    Returns
    -------
    BaseModel
        Validated model class

    Raises
    ------
    ValidationError
        If `json_data` is not valid according to one of the discovered Overture models
    """
    tap = _union_type_adapter()

    return cast(BaseModel, tap.validate_json(json_data))


__all__ = [
    "validate",
    "validate_json",
]


def _union_type_adapter() -> TypeAdapter:
    """
    Return a Pydantic type adapter that can validate the union of all models discovered using entry
    points.
    """
    models = discover_models()
    if not models:
        raise RuntimeError("no registered models found via entry points")

    discriminated_models: tuple[type[BaseModel], ...] = tuple(
        m for key, m in models.items() if _can_discriminate(m, key)
    )
    discriminated_union: UnionType | None = _discriminated_union(discriminated_models)

    non_discriminated_models: tuple[type[BaseModel], ...] = tuple(
        m for key, m in models.items() if not _can_discriminate(m, key)
    )
    non_discriminated_union: type[BaseModel] | UnionType | None = (
        reduce(or_, non_discriminated_models) if non_discriminated_models else None
    )

    model_union: type[BaseModel] | UnionType
    if discriminated_union and non_discriminated_union:
        model_union = discriminated_union | non_discriminated_union
    elif discriminated_union:
        model_union = discriminated_union
    elif non_discriminated_union:
        model_union = non_discriminated_union
    else:
        raise RuntimeError("logic error: unreachable code")

    return TypeAdapter(model_union)


def _discriminated_union(
    feature_classes: tuple[type[BaseModel], ...],
) -> Any:  # noqa: ANN401
    """
    Create a discriminated union of the feature models since they can be discriminated on the
    `type` field. This is just a performance optimization, and the union will work even if no models
    are discriminated.
    """
    if not feature_classes:
        return None
    else:
        return Annotated[
            reduce(
                or_,
                (
                    Annotated[f, Tag(cast(str, _type_literal(f)))]
                    for f in feature_classes
                ),
            ),
            Field(discriminator=Feature.field_discriminator("type", *feature_classes)),
        ]


def _can_discriminate(model_class: object, key: ModelKey) -> bool:
    """
    Return true if given value can participate in a discriminated union on the `type` field because
    it is a model class tagged `overture` where the `type` field has a single literal value.

    The class check is separate from the tag: `segment` is tagged `overture` but is an `Annotated`
    union, not a model class.
    """
    return (
        isinstance(model_class, type)
        and issubclass(model_class, BaseModel)
        and "overture" in key.tags
        and _type_literal(model_class) is not None
    )


def _type_literal(feature_class: type[BaseModel]) -> object:
    """
    Return the literal value of the feature model's `type` field, if it has one, or `None`
    if it does not.

    Parameters
    ----------
    feature_class : type[BaseModel]
        Feature model class

    Returns
    -------
    object
        The literal constrained value of the model class' `type` field, or `None` if the `type`
        field does not have a single literal value (an absurd `Literal[None]` collapses to `None`
        too -- the model then simply doesn't participate in the discriminated fast path).
    """
    if "type" not in feature_class.model_fields:
        return None
    return single_literal_value(feature_class.model_fields["type"].annotation)
