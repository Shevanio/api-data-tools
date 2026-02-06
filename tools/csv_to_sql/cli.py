"""CLI interface for CSV to SQL Converter."""

import sys
from pathlib import Path
from typing import Optional

import click

from shared.cli import error, handle_errors, info, success
from shared.logger import setup_logger

from .converter import CSVToSQL, SQLDialect


@click.command()
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
@click.option("--table", "-t", required=True, help="Table name")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output SQL file (print to stdout if not specified)",
)
@click.option(
    "--dialect",
    "-d",
    type=click.Choice(["postgresql", "mysql", "sqlite", "mssql"], case_sensitive=False),
    default="postgresql",
    help="SQL dialect",
)
@click.option(
    "--batch-size",
    "-b",
    type=int,
    default=1000,
    help="Rows per INSERT statement",
)
@click.option(
    "--schema-only",
    "-s",
    is_flag=True,
    help="Generate only CREATE TABLE (no INSERTs)",
)
@click.option(
    "--primary-key",
    "-p",
    help="Primary key column name",
)
@click.option(
    "--no-header",
    is_flag=True,
    help="CSV has no header row",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@handle_errors
def main(
    csv_file: Path,
    table: str,
    output: Optional[Path],
    dialect: str,
    batch_size: int,
    schema_only: bool,
    primary_key: Optional[str],
    no_header: bool,
    verbose: bool,
):
    """
    CSV to SQL Converter - Generate SQL from CSV files.

    Automatically infers schema and generates CREATE TABLE + INSERT statements.

    Examples:

        \b
        # Generate SQL for PostgreSQL
        csv2sql users.csv --table users

        \b
        # Save to file
        csv2sql data.csv --table products --output products.sql

        \b
        # MySQL dialect
        csv2sql data.csv --table customers --dialect mysql

        \b
        # Schema only (no INSERTs)
        csv2sql large.csv --table big_table --schema-only

        \b
        # With primary key
        csv2sql users.csv --table users --primary-key id

        \b
        # Batch inserts
        csv2sql data.csv --table data --batch-size 500 --output data.sql
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(__name__, level=log_level)

    # Initialize converter
    sql_dialect = SQLDialect(dialect.lower())
    converter = CSVToSQL(dialect=sql_dialect)

    info(f"Converting {csv_file} to {dialect.upper()} SQL")

    try:
        # Convert
        sql = converter.convert(
            csv_path=csv_file,
            table_name=table,
            output_path=output,
            batch_size=batch_size,
            schema_only=schema_only,
            primary_key=primary_key,
        )

        # Print to stdout if no output file
        if not output:
            print(sql)

        success(f"Conversion completed!")

        if output:
            info(f"SQL written to: {output}")

        sys.exit(0)

    except Exception as e:
        error(f"Conversion failed: {e}")
        if verbose:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
