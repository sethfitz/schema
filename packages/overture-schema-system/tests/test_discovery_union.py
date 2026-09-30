"""Tests for `model_union`, which combines discovered models into one type."""

import json
from typing import Annotated, Any, Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, Field, Tag, TypeAdapter

from overture.schema.system.discovery import ModelKey, model_union
from overture.schema.system.feature import Feature


class Alpha(Feature):
    type: Literal["alpha"]


class Beta(Feature):
    type: Literal["beta"]


class Gamma(Feature):
    type: Literal["gamma", "delta"]


class Plain(BaseModel):
    name: str


# A segment-shaped entry: a discriminated union registered under one key.
AlphaOrBeta = Annotated[
    Annotated[Alpha, Tag("alpha")] | Annotated[Beta, Tag("beta")],
    Field(discriminator=Feature.field_discriminator("type", Alpha, Beta)),
]


def _key(name: str, *tags: str) -> ModelKey:
    return ModelKey(name=name, entry_point=f"mock:{name}", tags=frozenset(tags))


def _members(union: Any) -> tuple[Any, ...]:  # noqa: ANN401
    return get_args(union)


def _is_discriminated(tp: Any) -> bool:  # noqa: ANN401
    return get_origin(tp) is Annotated and any(
        getattr(m, "discriminator", None) is not None for m in get_args(tp)[1:]
    )


def test_empty_raises() -> None:
    with pytest.raises(ValueError, match="No models provided"):
        model_union({})


def test_single_model_is_returned_as_is() -> None:
    assert model_union({_key("alpha", "overture"): Alpha}) is Alpha


def test_tagged_models_form_a_discriminated_union() -> None:
    union = model_union(
        {_key("alpha", "overture"): Alpha, _key("beta", "overture"): Beta}
    )

    assert _is_discriminated(union)
    adapter = TypeAdapter(union)
    feature = {
        "type": "Feature",
        "id": "b",
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "properties": {"type": "beta"},
    }
    assert isinstance(adapter.validate_json(json.dumps(feature)), Beta)


def test_untagged_models_are_plain_members_after_the_discriminated_union() -> None:
    union = model_union(
        {
            _key("plain"): Plain,
            _key("alpha", "overture"): Alpha,
            _key("beta", "overture"): Beta,
        }
    )

    first, *rest = _members(union)
    assert _is_discriminated(first)
    assert rest == [Plain]


@pytest.mark.parametrize(
    "key, model",
    [
        pytest.param(_key("alpha"), Alpha, id="feature-without-overture-tag"),
        pytest.param(_key("gamma", "overture"), Gamma, id="multi-value-literal"),
        pytest.param(_key("plain", "overture"), Plain, id="no-type-field"),
        pytest.param(_key("segment", "overture"), AlphaOrBeta, id="annotated-union"),
    ],
)
def test_models_that_cannot_discriminate_stay_plain_members(
    key: ModelKey,
    model: Any,  # noqa: ANN401
) -> None:
    union = model_union({key: model, _key("beta", "overture"): Beta})

    # One discriminable model is not wrapped, so the union is Beta | model.
    assert _members(union) == (Beta, model)
