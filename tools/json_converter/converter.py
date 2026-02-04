"""Core data conversion logic."""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import jmespath
import toml
import yaml

from shared.logger import get_logger

logger = get_logger(__name__)


class ConversionFormat(str, Enum):
    """Supported conversion formats."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


class DataConverter:
    """
    Convert between JSON, YAML, and TOML formats.

    Supports validation, querying, and formatting.
    """

    def __init__(self):
        """Initialize data converter."""
        logger.debug("Initialized DataConverter")

    def load_file(self, filepath: Path, format: Optional[ConversionFormat] = None) -> Any:
        """
        Load data from file.

        Args:
            filepath: Path to file
            format: Format to parse (auto-detect if None)

        Returns:
            Parsed data

        Raises:
            ValueError: If format is unsupported or parsing fails
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        # Auto-detect format from extension
        if format is None:
            suffix = filepath.suffix.lower()
            if suffix == ".json":
                format = ConversionFormat.JSON
            elif suffix in [".yaml", ".yml"]:
                format = ConversionFormat.YAML
            elif suffix == ".toml":
                format = ConversionFormat.TOML
            else:
                raise ValueError(f"Cannot auto-detect format for: {filepath}")

        logger.info(f"Loading {format.value} from {filepath}")

        try:
            with open(filepath, "r") as f:
                content = f.read()
                return self.parse(content, format)

        except Exception as e:
            logger.error(f"Failed to load file: {e}")
            raise ValueError(f"Failed to parse {format.value}: {e}")

    def parse(self, data: str, format: ConversionFormat) -> Any:
        """
        Parse data string.

        Args:
            data: Data string
            format: Input format

        Returns:
            Parsed data

        Raises:
            ValueError: If parsing fails
        """
        try:
            if format == ConversionFormat.JSON:
                return json.loads(data)
            elif format == ConversionFormat.YAML:
                return yaml.safe_load(data)
            elif format == ConversionFormat.TOML:
                return toml.loads(data)
            else:
                raise ValueError(f"Unsupported format: {format}")

        except Exception as e:
            logger.error(f"Failed to parse {format.value}: {e}")
            raise ValueError(f"Failed to parse {format.value}: {e}")

    def convert(
        self,
        data: Any,
        to_format: ConversionFormat,
        pretty: bool = True,
        indent: int = 2,
    ) -> str:
        """
        Convert data to specified format.

        Args:
            data: Data to convert (dict or list)
            to_format: Target format
            pretty: Whether to pretty-print (JSON only)
            indent: Indentation level

        Returns:
            Formatted string

        Raises:
            ValueError: If conversion fails
        """
        try:
            if to_format == ConversionFormat.JSON:
                if pretty:
                    return json.dumps(data, indent=indent, ensure_ascii=False)
                else:
                    return json.dumps(data, ensure_ascii=False)

            elif to_format == ConversionFormat.YAML:
                return yaml.dump(data, default_flow_style=False, allow_unicode=True, indent=indent)

            elif to_format == ConversionFormat.TOML:
                return toml.dumps(data)

            else:
                raise ValueError(f"Unsupported format: {to_format}")

        except Exception as e:
            logger.error(f"Failed to convert to {to_format.value}: {e}")
            raise ValueError(f"Failed to convert to {to_format.value}: {e}")

    def convert_file(
        self,
        input_path: Path,
        output_path: Path,
        to_format: ConversionFormat,
        from_format: Optional[ConversionFormat] = None,
        pretty: bool = True,
    ) -> None:
        """
        Convert file from one format to another.

        Args:
            input_path: Input file path
            output_path: Output file path
            to_format: Target format
            from_format: Source format (auto-detect if None)
            pretty: Whether to pretty-print
        """
        # Load input
        data = self.load_file(input_path, format=from_format)

        # Convert
        output_data = self.convert(data, to_format, pretty=pretty)

        # Write output
        with open(output_path, "w") as f:
            f.write(output_data)

        logger.info(f"Converted {input_path} to {output_path}")

    def query(self, data: Any, query_str: str) -> Any:
        """
        Query data using JMESPath.

        Args:
            data: Data to query
            query_str: JMESPath query string

        Returns:
            Query result

        Raises:
            ValueError: If query fails
        """
        try:
            result = jmespath.search(query_str, data)
            return result

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise ValueError(f"Query failed: {e}")

    def validate_json_schema(self, data: Any, schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate data against JSON Schema.

        Args:
            data: Data to validate
            schema: JSON Schema

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            import jsonschema

            jsonschema.validate(instance=data, schema=schema)
            return (True, None)

        except jsonschema.ValidationError as e:
            return (False, str(e))

        except Exception as e:
            return (False, f"Validation error: {e}")

    def minify_json(self, data: Any) -> str:
        """
        Minify JSON data (remove whitespace).

        Args:
            data: Data to minify

        Returns:
            Minified JSON string
        """
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    def pretty_print(self, data: Any, format: ConversionFormat, indent: int = 2) -> str:
        """
        Pretty-print data.

        Args:
            data: Data to print
            format: Output format
            indent: Indentation level

        Returns:
            Pretty-printed string
        """
        return self.convert(data, format, pretty=True, indent=indent)

    def batch_convert(
        self,
        input_dir: Path,
        output_dir: Path,
        to_format: ConversionFormat,
        pattern: str = "*",
    ) -> int:
        """
        Batch convert files in a directory.

        Args:
            input_dir: Input directory
            output_dir: Output directory
            to_format: Target format
            pattern: Glob pattern for input files

        Returns:
            Number of files converted
        """
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        output_dir.mkdir(parents=True, exist_ok=True)

        converted_count = 0

        # Find all matching files
        for input_file in input_dir.glob(pattern):
            if input_file.is_file():
                try:
                    # Determine output filename
                    output_file = output_dir / f"{input_file.stem}.{to_format.value}"

                    # Convert
                    self.convert_file(input_file, output_file, to_format)
                    converted_count += 1
                    logger.info(f"Converted: {input_file.name} → {output_file.name}")

                except Exception as e:
                    logger.warning(f"Failed to convert {input_file.name}: {e}")

        return converted_count
