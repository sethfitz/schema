"""Build feature dictionaries for validate-command tests.

Lives outside `conftest.py` so tests in both -validation and -cli import it
by a name no other test directory on the pytest path shares.
"""

from typing import Any


def build_feature(
    id: str | None = "test",
    theme: str | None = "buildings",
    type: str = "building",
    geometry_type: str = "Polygon",
    coordinates: list | None = None,
    version: int | None = 0,
    geojson_format: bool = True,
    **properties: Any,
) -> dict[str, Any]:
    """Build a feature dictionary with the specified parameters.

    Args:
        id: Feature ID (None to omit)
        theme: Theme name (None to omit)
        type: Feature type
        geometry_type: Geometry type (Point, Polygon, etc.)
        coordinates: Custom coordinates (None for sensible defaults)
        version: Feature version (None to omit)
        geojson_format: If True, use GeoJSON format; if False, use flat format
        **properties: Additional properties to include

    Returns:
        Feature dictionary in the requested format
    """
    # Default coordinates based on geometry type
    if coordinates is None:
        if geometry_type == "Point":
            coordinates = [0.0, 0.0]
        elif geometry_type == "Polygon":
            coordinates = [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        elif geometry_type == "LineString":
            coordinates = [[0, 0], [1, 1]]
        elif geometry_type == "MultiPolygon":
            coordinates = [[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]]
        else:
            coordinates = []

    geometry = {"type": geometry_type, "coordinates": coordinates}

    if geojson_format:
        # GeoJSON format: properties nested under "properties" key
        props: dict[str, Any] = {
            "type": type,
            **properties,
        }
        if theme is not None:
            props["theme"] = theme
        if version is not None:
            props["version"] = version

        feature: dict[str, Any] = {
            "type": "Feature",
            "geometry": geometry,
            "properties": props,
        }
        if id is not None:
            feature["id"] = id
    else:
        # Flat format: properties at top level
        # Build in the expected order: geometry, theme, type, version, id, properties
        feature = {"geometry": geometry}
        if theme is not None:
            feature["theme"] = theme
        feature["type"] = type
        if version is not None:
            feature["version"] = version
        feature.update(properties)
        if id is not None:
            feature["id"] = id

    return feature
