"""Tests for the CLI group and its own commands (list-types, json-schema)."""

import json
import re

import pytest
from click.testing import CliRunner

from overture.schema.cli.commands import cli
from overture.schema.system.discovery import discover_models

_HELP_INVOCATIONS = [["--help"]] + [[name, "--help"] for name in sorted(cli.commands)]

# Click renders each option as a line starting with two spaces and the flag,
# its help indented under it.
_OPTION_START = re.compile(r"^  (--[\w-]+)", re.MULTILINE)

# Options whose `(e.g. ...)` illustrations name something other than a tag.
_NOT_TAGS = {"--type", "--show-field"}


def _help_segments(output: str) -> list[tuple[str | None, str]]:
    """Split `--help` output into (option, text), so a citation keeps its option.

    The leading segment -- description and examples, before the first option
    line -- carries `None`.
    """
    bounds = list(_OPTION_START.finditer(output))
    if not bounds:
        return [(None, output)]
    segments: list[tuple[str | None, str]] = [(None, output[: bounds[0].start()])]
    for current, following in zip(bounds, [*bounds[1:], None], strict=True):
        end = following.start() if following else len(output)
        segments.append((current[1], output[current.start() : end]))
    return segments


class TestListTypesCommand:
    """Tests for the list-types command."""

    def test_list_types_command(self, cli_runner: CliRunner) -> None:
        """Test the list-types command."""
        result = cli_runner.invoke(cli, ["list-types"])
        assert result.exit_code == 0
        # Should show theme tag
        assert "overture:theme=buildings" in result.output
        # Should show type names
        assert "building" in result.output

    def test_list_types_command_help(self, cli_runner: CliRunner) -> None:
        """Test list-types command help."""
        result = cli_runner.invoke(cli, ["list-types", "--help"])
        assert result.exit_code == 0
        assert "list-types" in result.output.lower()


class TestHelpFormatting:
    """Tests for `--help` rendering and the tags it cites."""

    @pytest.mark.parametrize("argv", _HELP_INVOCATIONS, ids=lambda a: " ".join(a))
    def test_help_has_no_literal_escape(
        self, cli_runner: CliRunner, argv: list[str]
    ) -> None:
        """Click's no-rewrap marker is interpreted, not printed."""
        result = cli_runner.invoke(cli, argv)
        assert result.exit_code == 0
        assert "\\b" not in result.output

    def test_help_keeps_examples_on_separate_lines(self, cli_runner: CliRunner) -> None:
        """Each example command occupies its own line rather than reflowing."""
        result = cli_runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        commands = [
            line.strip()
            for line in result.output.splitlines()
            if line.strip().startswith("$ overture-schema")
        ]
        assert len(commands) >= 4
        assert "$ overture-schema validate data.json" in commands

    def test_help_cites_only_tags_that_exist(self, cli_runner: CliRunner) -> None:
        """Tags named in `--help` work in the option they are named for.

        Two citation forms, because a phantom has hidden in each: an
        argument (`--tag X`) and an illustration (`(e.g. X)`). Both are
        found wherever they appear in the rendered output, including
        across a terminal wrap.

        Each is checked against the set that option accepts, not a global
        union: `--group-by` takes the *key* half of a `key=value` tag, so
        `--tag overture:theme` selects nothing and `--group-by feature`
        groups nothing, and neither may pass. Attribution is by splitting
        the Options block per option, so an illustration is judged by the
        option whose help it sits in.

        Not checked: a tag named in running prose outside both forms.
        `namespace:predicate` in the `--tag` syntax note is deliberately
        such a placeholder -- describing the grammar without writing
        something that looks runnable is why it is worded that way. Nor are
        options in `_NOT_TAGS`, whose illustrations name something else --
        `--type`'s "(e.g., building, segment)" names types.
        """
        emitted = {tag for key in discover_models() for tag in key.tags}
        keys = {tag.split("=", 1)[0] for tag in emitted if "=" in tag}
        # What each tag-taking option accepts.
        accepts: dict[str | None, set[str]] = {
            "--tag": emitted,
            "--filter": emitted,
            "--exclude": emitted,
            "--group-by": keys,
        }
        argument_form = re.compile(r"--(tag|filter|exclude|group-by) ([\w.:=-]+)")
        illustration_form = re.compile(r"e\.g\. ([^)]+)\)")

        cited: list[tuple[str, str, set[str]]] = []
        for argv in _HELP_INVOCATIONS:
            result = cli_runner.invoke(cli, argv)
            assert result.exit_code == 0, f"{argv}: --help failed"
            where = " ".join(argv)
            for option, segment in _help_segments(result.output):
                # Rejoin words the terminal wrapper split, so a tag broken
                # across lines is still seen whole.
                flowed = " ".join(segment.split())
                cited += [
                    # A citation ending a sentence picks up its period; the
                    # tag grammar allows `.` inside a name, never at the end.
                    (where, value.rstrip(".,"), accepts[f"--{flag}"])
                    for flag, value in argument_form.findall(flowed)
                    if value != "TEXT"  # the option signature's metavar
                ]
                if option in _NOT_TAGS:
                    continue
                # An illustration inside a tag option's help is judged by
                # that option; one in the description, the examples, or the
                # Commands block belongs to no option, so accept either.
                accepted = accepts.get(option, emitted | keys)
                cited += [
                    (where, token.strip("'\"").rstrip(".,"), accepted)
                    for group in illustration_form.findall(flowed)
                    for token in re.split(r",\s*", group.strip())
                ]
        assert cited, "no tag cited anywhere in --help -- the sweep found nothing"
        for where, tag, accepted in cited:
            assert tag in accepted, f"{where}: {tag!r} matches no model"


class TestJsonSchemaCommand:
    """Tests for the json-schema command."""

    def test_json_schema_generates_valid_output(self, cli_runner: CliRunner) -> None:
        """Test that json-schema command generates valid JSON."""
        result = cli_runner.invoke(
            cli, ["json-schema", "--tag", "overture:theme=buildings"]
        )
        assert result.exit_code == 0

        # Should be valid JSON
        schema = json.loads(result.output)
        assert isinstance(schema, dict)

    def test_official_unified_schema_release_artifact(
        self, cli_runner: CliRunner
    ) -> None:
        """Test the exact command the release workflow uses to build `overture-schema.json` as a
        release artifact and sanity-check that the output seems reasonable.
        """
        result = cli_runner.invoke(cli, ["json-schema", "--tag", "overture"])
        assert result.exit_code == 0

        schema = json.loads(result.output)

        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "$defs" in schema and schema["$defs"]
        assert any(k in schema for k in ("anyOf", "oneOf"))


_TAG_COMBINATOR_FLAGS = (
    pytest.param("--filter", "feature", id="filter"),
    pytest.param("--exclude", "overture:theme=places", id="exclude"),
)


@pytest.mark.parametrize(("flag", "value"), _TAG_COMBINATOR_FLAGS)
def test_json_schema_wires_tag_combinator_flag(
    cli_runner: CliRunner,
    flag: str,
    value: str,
) -> None:
    """json-schema wires --filter/--exclude through to the tag selector."""
    result = cli_runner.invoke(cli, ["json-schema", "--tag", "feature", flag, value])
    assert result.exit_code == 0
    assert result.output  # non-empty JSON


@pytest.mark.parametrize(("flag", "value"), _TAG_COMBINATOR_FLAGS)
def test_list_types_wires_tag_combinator_flag(
    cli_runner: CliRunner,
    flag: str,
    value: str,
) -> None:
    """list-types wires --filter/--exclude through to the tag selector."""
    result = cli_runner.invoke(cli, ["list-types", "--tag", "feature", flag, value])
    assert result.exit_code == 0
