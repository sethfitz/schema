"""CLI subpackage for overture-schema."""

from overture.schema.validation.command import (
    handle_generic_error,
    handle_validation_error,
    load_input,
    perform_validation,
)
from overture.schema.validation.types import (
    ErrorLocation,
    UnionType,
    ValidationErrorDict,
)

from .commands import (
    cli,
    create_union_type_from_models,
    resolve_types,
)

__all__ = [
    "cli",
    "create_union_type_from_models",
    "handle_generic_error",
    "handle_validation_error",
    "load_input",
    "perform_validation",
    "resolve_types",
    "ErrorLocation",
    "UnionType",
    "ValidationErrorDict",
]
