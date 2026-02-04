"""CLI interface for JSON/YAML Converter."""

import sys
from pathlib import Path
from typing import Optional

import click

from shared.cli import error, handle_errors, info, success
from shared.logger import setup_logger

from .converter import ConversionFormat, DataConverter


@click.command()
@click.argument("input_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--to",
    "-t",
    "to_format",
    type=click.Choice(["json", "yaml", "toml"], case_sensitive=False),
    required=True,
    help="Target format",
)
@click.option(
    "--from",
    "-f",
    "from_format",
    type=click.Choice(["json", "yaml", "toml"], case_sensitive=False),
    help="Source format (auto-detect if not specified)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file (print to stdout if not specified)",
)
@click.option(
    "--query",
    "-q",
    help="JMESPath query to extract data",
)
@click.option(
    "--minify",
    is_flag=True,
    help="Minify output (JSON only)",
)
@click.option(
    "--indent",
    type=int,
    default=2,
    show_default=True,
    help="Indentation level",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@handle_errors
def main(
    input_file: Path,
    to_format: str,
    from_format: Optional[str],
    output: Optional[Path],
    query: Optional[str],
    minify: bool,
    indent: int,
    verbose: bool,
):
    """
    Data Converter - Convert between JSON, YAML, and TOML formats.

    Examples:

        \b
        # Convert JSON to YAML
        data-convert config.json --to yaml

        \b
        # Convert with output file
        data-convert data.json --to yaml --output data.yaml

        \b
        # Query and convert
        data-convert users.json --to yaml --query 'users[0]'

        \b
        # Minify JSON
        data-convert data.json --to json --minify

        \b
        # Pretty print
        data-convert minified.json --to json --indent 4
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(__name__, level=log_level)

    converter = DataConverter()

    # Parse format enums
    to_fmt = ConversionFormat(to_format.lower())
    from_fmt = ConversionFormat(from_format.lower()) if from_format else None

    try:
        # Load input file
        info(f"Loading {input_file}")
        data = converter.load_file(input_file, format=from_fmt)

        # Apply query if specified
        if query:
            info(f"Applying query: {query}")
            data = converter.query(data, query)

        # Convert
        if minify and to_fmt == ConversionFormat.JSON:
            output_data = converter.minify_json(data)
        else:
            output_data = converter.convert(data, to_fmt, pretty=not minify, indent=indent)

        # Output
        if output:
            with open(output, "w") as f:
                f.write(output_data)
            success(f"Converted to {output}")
        else:
            print(output_data)

        sys.exit(0)

    except FileNotFoundError as e:
        error(str(e))
        sys.exit(1)

    except ValueError as e:
        error(str(e))
        sys.exit(1)

    except Exception as e:
        error(f"Unexpected error: {e}")
        if verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
