from typing import cast

from pydantic import BaseModel, TypeAdapter

from overture.schema.system.discovery import discover_models, model_union


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

    return TypeAdapter(model_union(models))
