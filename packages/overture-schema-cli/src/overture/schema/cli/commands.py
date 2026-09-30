"""Click-based CLI for overture-schema package."""

import json

import click
from rich.console import Console
from rich.text import Text

from overture.schema.system.discovery import (
    ModelKey,
    TagSelector,
    discover_models,
    filter_models,
    model_union,
)
from overture.schema.system.discovery.tag import get_values_for_key
from overture.schema.system.json_schema import json_schema
from overture.schema.validation.command import validate_command
from overture.schema.validation.types import UnionType

from .tag_options import build_selector, tag_selection_options

stdout = Console(highlight=False)


# The CLI's name for the -system union builder, kept as part of its public API.
create_union_type_from_models = model_union


def resolve_types(
    selector: TagSelector = TagSelector(),
    *,
    type_names: tuple[str, ...] = (),
) -> UnionType:
    """Resolve a TagSelector + type-names into a Pydantic union type."""
    models = discover_models()
    models = filter_models(models, selector, type_names=type_names)

    if not models:
        raise ValueError("No models found matching the specified criteria")

    return model_union(models)


# Every `# noqa: D301` below is the same waiver, against `pydocstyle` (see
# the docformat-only target). D301 wants a raw string wherever a docstring
# contains a backslash, but `\b` here is Click's no-rewrap marker: a raw
# string hands Click two literal characters and every example block collapses
# into one paragraph. Any new command with an Examples block needs the waiver
# too. Note the placement is pydocstyle's -- ruff reports D301 at the
# docstring line instead, so selecting ruff's `D` rules would need its own.
@click.group()
@click.version_option(package_name="overture-schema")
def cli() -> None:  # noqa: D301
    """Overture Schema command-line interface.

    Provides validation, schema generation, and type discovery for Overture Maps data.

    \b
    Examples:
      # Validate a file
      $ overture-schema validate data.json
    \b
      # Validate from stdin
      $ overture-schema validate - < data.json
    \b
      # List available types
      $ overture-schema list-types
    \b
      # Generate JSON schema
      $ overture-schema json-schema --tag overture:theme=buildings
    \b
      # Validate specific types
      $ overture-schema validate --tag overture:theme=buildings data.json
    """
    pass


cli.add_command(validate_command)


@cli.command("json-schema")
@tag_selection_options
@click.option(
    "--type",
    "types",
    multiple=True,
    help="Specific type to generate schema for (e.g., building, segment)",
)
def json_schema_command(
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    types: tuple[str, ...],
) -> None:  # noqa: D301
    """Generate JSON schema for Overture Maps types.

    Outputs a JSON Schema document to stdout that can be used for validation
    or documentation purposes.

    \b
    Examples:
      # All types
      $ overture-schema json-schema > schema.json
    \b
      # Buildings theme by tag
      $ overture-schema json-schema --tag overture:theme=buildings
    \b
      # Specific types
      $ overture-schema json-schema --type building
    \b
      # Two themes at once (repeatable; scope is their union)
      $ overture-schema json-schema --tag overture:theme=buildings \\
          --tag overture:theme=places
    \b
      # Only types built on the Overture feature model
      $ overture-schema json-schema --tag overture
    """
    try:
        model_type = resolve_types(
            build_selector(tags, filters, excludes), type_names=types
        )
        schema = json_schema(model_type)
        # Use plain print for JSON output to avoid Rich formatting
        print(json.dumps(schema, indent=2, sort_keys=True))
    except ValueError as e:
        raise click.UsageError(str(e)) from e


@cli.command("list-types")
@tag_selection_options
@click.option(
    "--group-by",
    help="Group types by a key/value tag's key, as in "
    "--group-by overture:theme. "
    "Plain and namespaced tags have no value to group by and are "
    "ignored here.",
)
def list_types(
    tags: tuple[str, ...],
    filters: tuple[str, ...],
    excludes: tuple[str, ...],
    group_by: str | None,
) -> None:  # noqa: D301
    """List all available types.

    Displays all registered models and can be organized by grouping.

    \b
    Examples:
      # List all types
      $ overture-schema list-types
    \b
      # One theme
      $ overture-schema list-types --tag overture:theme=buildings
    \b
      # Group the listing by theme
      $ overture-schema list-types --group-by overture:theme
    """
    try:
        models = discover_models()
        models = filter_models(models, build_selector(tags, filters, excludes))

        if group_by:
            grouped_models: dict[str, set[ModelKey]] = {}

            for key in models.keys():
                if groups := get_values_for_key(key.tags, group_by):
                    for group in groups:
                        grouped_models.setdefault(group, set()).add(key)

            padding = (
                max(
                    (len(key.name) for keys in grouped_models.values() for key in keys),
                    default=0,
                )
                + 2
            )

            for group, keys in sorted(grouped_models.items()):
                stdout.print(
                    f"[green bold]{group_by}={group} ({len(keys)})[/green bold]"
                )
                for key in sorted(keys, key=lambda k: k.name):
                    model = Text()
                    model.append("→ ", style="bright_black")
                    model.append(key.name, style="bold cyan")
                    model.pad_right(max(1, padding - len(key.name)))
                    model.append("  ".join(sorted(key.tags)))
                    stdout.print(model)
                stdout.print()

        else:
            padding = max((len(key.name) for key in models.keys()), default=0) + 2

            for key in sorted(models.keys(), key=lambda k: k.name):
                model = Text()
                model.append(key.name, style="bold cyan")
                model.pad_right(max(1, padding - len(key.name)))
                model.append("  ".join(sorted(key.tags)))
                stdout.print(model)

    except Exception as e:
        click.echo(f"Error listing types: {e}", err=True)


if __name__ == "__main__":
    cli()
