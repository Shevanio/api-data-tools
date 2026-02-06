"""Core CSV to SQL conversion logic."""

import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from shared.logger import get_logger

logger = get_logger(__name__)


class ColumnType(str, Enum):
    """SQL column types."""

    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    DECIMAL = "DECIMAL"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    DATE = "DATE"
    DATETIME = "DATETIME"
    BOOLEAN = "BOOLEAN"


class SQLDialect(str, Enum):
    """SQL database dialects."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MSSQL = "mssql"


@dataclass
class ColumnDefinition:
    """Definition of a table column."""

    name: str
    type: ColumnType
    length: Optional[int] = None
    nullable: bool = True
    is_primary_key: bool = False


class CSVToSQL:
    """
    Convert CSV files to SQL statements.

    Supports schema inference and multiple SQL dialects.
    """

    def __init__(self, dialect: SQLDialect = SQLDialect.POSTGRESQL):
        """
        Initialize CSV to SQL converter.

        Args:
            dialect: SQL dialect to use
        """
        self.dialect = dialect
        logger.debug(f"Initialized CSVToSQL with dialect: {dialect}")

    def infer_schema(
        self,
        filepath: Path,
        sample_size: int = 1000,
        has_header: bool = True,
    ) -> List[ColumnDefinition]:
        """
        Infer schema from CSV file.

        Args:
            filepath: Path to CSV file
            sample_size: Number of rows to sample for type inference
            has_header: Whether CSV has header row

        Returns:
            List of ColumnDefinition objects
        """
        logger.info(f"Inferring schema from {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            # Read header
            if has_header:
                header = next(reader)
            else:
                # Use column indices as names
                first_row = next(reader)
                header = [f"column_{i}" for i in range(len(first_row))]
                # Reset to read data
                f.seek(0)
                reader = csv.reader(f)

            # Sample data
            samples = []
            for i, row in enumerate(reader):
                if i >= sample_size:
                    break
                if has_header and i == 0:
                    continue
                samples.append(row)

        # Infer types
        columns = []
        num_cols = len(header)

        for col_idx in range(num_cols):
            col_name = self._sanitize_name(header[col_idx])
            col_values = [row[col_idx] if col_idx < len(row) else "" for row in samples]

            # Detect type
            col_type, max_length = self._infer_column_type(col_values)

            columns.append(
                ColumnDefinition(
                    name=col_name,
                    type=col_type,
                    length=max_length if col_type == ColumnType.VARCHAR else None,
                    nullable=any(v == "" or v is None for v in col_values),
                )
            )

        logger.info(f"Inferred {len(columns)} columns")
        return columns

    def _infer_column_type(self, values: List[str]) -> tuple[ColumnType, Optional[int]]:
        """
        Infer column type from sample values.

        Args:
            values: Sample column values

        Returns:
            Tuple of (ColumnType, max_length)
        """
        # Remove empty/null values for type detection
        non_empty = [v for v in values if v and v.strip()]

        if not non_empty:
            return (ColumnType.VARCHAR, 255)

        # Try INTEGER
        if all(self._is_integer(v) for v in non_empty):
            max_val = max(abs(int(v)) for v in non_empty)
            if max_val > 2147483647:  # INT max
                return (ColumnType.BIGINT, None)
            return (ColumnType.INTEGER, None)

        # Try DECIMAL
        if all(self._is_decimal(v) for v in non_empty):
            return (ColumnType.DECIMAL, None)

        # Try BOOLEAN
        if all(v.lower() in ["true", "false", "1", "0", "yes", "no"] for v in non_empty):
            return (ColumnType.BOOLEAN, None)

        # Try DATE
        if all(self._is_date(v) for v in non_empty):
            return (ColumnType.DATE, None)

        # Try DATETIME
        if all(self._is_datetime(v) for v in non_empty):
            return (ColumnType.DATETIME, None)

        # Default to VARCHAR/TEXT
        max_length = max(len(v) for v in values)

        if max_length > 255:
            return (ColumnType.TEXT, None)
        else:
            # Round up to nearest 50
            varchar_length = ((max_length // 50) + 1) * 50
            return (ColumnType.VARCHAR, varchar_length)

    def _is_integer(self, value: str) -> bool:
        """Check if value is an integer."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_decimal(self, value: str) -> bool:
        """Check if value is a decimal number."""
        try:
            float(value)
            return "." in value  # Must have decimal point
        except ValueError:
            return False

    def _is_date(self, value: str) -> bool:
        """Check if value is a date."""
        import re

        # Common date formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY
        patterns = [
            r"^\d{4}-\d{2}-\d{2}$",
            r"^\d{2}/\d{2}/\d{4}$",
            r"^\d{2}-\d{2}-\d{4}$",
        ]
        return any(re.match(p, value) for p in patterns)

    def _is_datetime(self, value: str) -> bool:
        """Check if value is a datetime."""
        import re

        # ISO format or common datetime formats
        patterns = [
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
        ]
        return any(re.match(p, value) for p in patterns)

    def _sanitize_name(self, name: str) -> str:
        """Sanitize column/table name for SQL."""
        # Replace spaces and special chars with underscore
        import re

        sanitized = re.sub(r"[^\w]", "_", name.lower())
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Ensure doesn't start with number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        return sanitized or "column"

    def generate_create_table(
        self,
        table_name: str,
        columns: List[ColumnDefinition],
        primary_key: Optional[str] = None,
    ) -> str:
        """
        Generate CREATE TABLE statement.

        Args:
            table_name: Table name
            columns: List of column definitions
            primary_key: Primary key column name

        Returns:
            SQL CREATE TABLE statement
        """
        sanitized_table = self._sanitize_name(table_name)

        lines = [f"CREATE TABLE {sanitized_table} ("]

        col_defs = []
        for col in columns:
            col_def = f"    {col.name} {self._format_type(col)}"

            if primary_key and col.name == primary_key:
                col_def += " PRIMARY KEY"
            elif not col.nullable:
                col_def += " NOT NULL"

            col_defs.append(col_def)

        lines.append(",\n".join(col_defs))
        lines.append(");")

        return "\n".join(lines)

    def _format_type(self, col: ColumnDefinition) -> str:
        """Format column type for SQL dialect."""
        if col.type == ColumnType.VARCHAR and col.length:
            return f"VARCHAR({col.length})"

        if self.dialect == SQLDialect.POSTGRESQL:
            type_map = {
                ColumnType.INTEGER: "INTEGER",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.TEXT: "TEXT",
                ColumnType.DATE: "DATE",
                ColumnType.DATETIME: "TIMESTAMP",
                ColumnType.BOOLEAN: "BOOLEAN",
            }
        elif self.dialect == SQLDialect.MYSQL:
            type_map = {
                ColumnType.INTEGER: "INT",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.TEXT: "TEXT",
                ColumnType.DATE: "DATE",
                ColumnType.DATETIME: "DATETIME",
                ColumnType.BOOLEAN: "TINYINT(1)",
            }
        elif self.dialect == SQLDialect.SQLITE:
            type_map = {
                ColumnType.INTEGER: "INTEGER",
                ColumnType.BIGINT: "INTEGER",
                ColumnType.DECIMAL: "REAL",
                ColumnType.TEXT: "TEXT",
                ColumnType.DATE: "TEXT",
                ColumnType.DATETIME: "TEXT",
                ColumnType.BOOLEAN: "INTEGER",
            }
        else:  # MSSQL
            type_map = {
                ColumnType.INTEGER: "INT",
                ColumnType.BIGINT: "BIGINT",
                ColumnType.DECIMAL: "DECIMAL(10,2)",
                ColumnType.TEXT: "TEXT",
                ColumnType.DATE: "DATE",
                ColumnType.DATETIME: "DATETIME2",
                ColumnType.BOOLEAN: "BIT",
            }

        return type_map.get(col.type, "TEXT")

    def generate_insert_statements(
        self,
        filepath: Path,
        table_name: str,
        columns: List[ColumnDefinition],
        batch_size: int = 1000,
        has_header: bool = True,
    ) -> List[str]:
        """
        Generate INSERT statements from CSV.

        Args:
            filepath: Path to CSV file
            table_name: Table name
            columns: Column definitions
            batch_size: Number of rows per INSERT
            has_header: Whether CSV has header

        Returns:
            List of INSERT statements
        """
        logger.info(f"Generating INSERT statements (batch size: {batch_size})")

        sanitized_table = self._sanitize_name(table_name)
        column_names = ", ".join(col.name for col in columns)

        statements = []
        current_batch = []

        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f)

            if has_header:
                next(reader)  # Skip header

            for row in reader:
                # Format values
                formatted_values = []
                for i, value in enumerate(row):
                    if i >= len(columns):
                        break

                    col = columns[i]

                    if not value or value.strip() == "":
                        formatted_values.append("NULL")
                    elif col.type in [ColumnType.INTEGER, ColumnType.BIGINT, ColumnType.DECIMAL]:
                        formatted_values.append(value)
                    elif col.type == ColumnType.BOOLEAN:
                        bool_val = value.lower() in ["true", "1", "yes"]
                        if self.dialect == SQLDialect.POSTGRESQL:
                            formatted_values.append("TRUE" if bool_val else "FALSE")
                        else:
                            formatted_values.append("1" if bool_val else "0")
                    else:
                        # String types - escape quotes
                        escaped = value.replace("'", "''")
                        formatted_values.append(f"'{escaped}'")

                current_batch.append(f"({', '.join(formatted_values)})")

                # Flush batch
                if len(current_batch) >= batch_size:
                    stmt = f"INSERT INTO {sanitized_table} ({column_names}) VALUES\n"
                    stmt += ",\n".join(current_batch) + ";"
                    statements.append(stmt)
                    current_batch = []

            # Final batch
            if current_batch:
                stmt = f"INSERT INTO {sanitized_table} ({column_names}) VALUES\n"
                stmt += ",\n".join(current_batch) + ";"
                statements.append(stmt)

        logger.info(f"Generated {len(statements)} INSERT statement(s)")
        return statements

    def convert(
        self,
        csv_path: Path,
        table_name: str,
        output_path: Optional[Path] = None,
        batch_size: int = 1000,
        schema_only: bool = False,
        primary_key: Optional[str] = None,
    ) -> str:
        """
        Convert CSV to SQL.

        Args:
            csv_path: Path to CSV file
            table_name: Table name
            output_path: Output SQL file path (optional)
            batch_size: Rows per INSERT statement
            schema_only: Generate only CREATE TABLE
            primary_key: Primary key column name

        Returns:
            Generated SQL
        """
        # Infer schema
        columns = self.infer_schema(csv_path)

        # Generate CREATE TABLE
        create_stmt = self.generate_create_table(table_name, columns, primary_key)

        sql_parts = [create_stmt]

        # Generate INSERTs
        if not schema_only:
            insert_stmts = self.generate_insert_statements(
                csv_path, table_name, columns, batch_size
            )
            sql_parts.extend(insert_stmts)

        full_sql = "\n\n".join(sql_parts)

        # Write to file if specified
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_sql)
            logger.info(f"Wrote SQL to {output_path}")

        return full_sql
