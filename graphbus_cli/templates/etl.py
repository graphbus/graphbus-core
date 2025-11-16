"""
ETL project template - Data pipeline
"""

from pathlib import Path
from .base import Template


class ETLTemplate(Template):
    """Data pipeline with extractors, transformers, loaders"""

    @property
    def name(self) -> str:
        return "etl"

    @property
    def description(self) -> str:
        return "Data pipeline with extractors, transformers, loaders"

    def create_project(self, project_path: Path, project_name: str) -> None:
        """Create ETL project structure"""
        self._create_directory_structure(project_path)

        agents_dir = project_path / "agents"

        # Extractor agent
        extractor = '''"""
Data Extractor - Extracts data from source systems
"""

from graphbus_core import GraphBusNode, schema_method


class DataExtractor(GraphBusNode):
    """Agent that extracts data from source systems"""

    SYSTEM_PROMPT = """
    You extract data from source systems and initiate the ETL pipeline.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about extraction schedules, data formats, error handling, and performance optimizations.
    """

    def __init__(self):
        super().__init__()
        self.extraction_count = 0

    @schema_method(
        input_schema={"source": str},
        output_schema={"records": list, "count": int}
    )
    def start_extraction(self, source: str = "default") -> dict:
        """Start data extraction from source"""
        self.extraction_count += 1

        # Simple demo data (would connect to real source in production)
        data = {
            "records": [
                {"id": 1, "value": "test"},
                {"id": 2, "value": "demo"},
                {"id": 3, "value": "data"}
            ],
            "count": 3
        }

        # Publish to topic to trigger pipeline
        self.publish("/etl/extracted", data)
        return data

    @schema_method(
        input_schema={},
        output_schema={"total_extractions": int}
    )
    def get_stats(self) -> dict:
        """Get extraction statistics"""
        return {"total_extractions": self.extraction_count}
'''

        # Transformer agent
        transformer = '''"""
Data Transformer - Transforms extracted data
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class DataTransformer(GraphBusNode):
    """Agent that transforms data in the ETL pipeline"""

    SYSTEM_PROMPT = """
    You transform data between extraction and loading stages.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about transformation rules, data quality checks, and processing strategies.
    """

    def __init__(self):
        super().__init__()
        self.transformation_count = 0

    @subscribe("/etl/extracted")
    def on_data_extracted(self, event: dict):
        """Handle extracted data and transform it"""
        records = event.get("records", [])

        # Transform data (uppercase values in this demo)
        transformed = [
            {"id": r["id"], "value": r["value"].upper()}
            for r in records
        ]

        self.transformation_count += 1

        self.publish("/etl/transformed", {
            "records": transformed,
            "count": len(transformed)
        })

    @schema_method(
        input_schema={"records": list},
        output_schema={"records": list, "count": int}
    )
    def transform(self, records: list) -> dict:
        """Transform a batch of records manually"""
        transformed = [
            {"id": r.get("id"), "value": str(r.get("value", "")).upper()}
            for r in records
        ]
        return {"records": transformed, "count": len(transformed)}

    @schema_method(
        input_schema={},
        output_schema={"total_transformations": int}
    )
    def get_stats(self) -> dict:
        """Get transformation statistics"""
        return {"total_transformations": self.transformation_count}
'''

        # Loader agent
        loader = '''"""
Data Loader - Loads transformed data to destination
"""

from graphbus_core import GraphBusNode, subscribe, schema_method


class DataLoader(GraphBusNode):
    """Agent that loads transformed data to destination systems"""

    SYSTEM_PROMPT = """
    You load transformed data to destination systems.
    In Build Mode with agent orchestration enabled, you can negotiate with other
    agents about loading strategies, batch sizes, error recovery, and data validation.
    """

    def __init__(self):
        super().__init__()
        self.loaded_count = 0
        self.total_records = 0

    @subscribe("/etl/transformed")
    def on_data_transformed(self, event: dict):
        """Handle transformed data and load to destination"""
        records = event.get("records", [])

        # Load data (would write to real destination in production)
        record_count = len(records)
        self.loaded_count += 1
        self.total_records += record_count

        print(f"[DataLoader] Loaded {record_count} records (batch #{self.loaded_count})")

        self.publish("/etl/loaded", {
            "count": record_count,
            "batch_id": self.loaded_count
        })

    @schema_method(
        input_schema={},
        output_schema={"batches_loaded": int, "total_records": int}
    )
    def get_stats(self) -> dict:
        """Get loading statistics"""
        return {
            "batches_loaded": self.loaded_count,
            "total_records": self.total_records
        }
'''

        self._write_file(agents_dir / "extractor.py", extractor)
        self._write_file(agents_dir / "transformer.py", transformer)
        self._write_file(agents_dir / "loader.py", loader)

        readme = f'''# {project_name}

ETL data pipeline using GraphBus.

## Pipeline
1. Extractor - Reads data from source
2. Transformer - Transforms data
3. Loader - Writes data to destination

## Getting Started
```bash
pip install -r requirements.txt
graphbus build agents/
graphbus run .graphbus
```
'''

        self._write_file(project_path / "README.md", readme)
        self._write_file(project_path / "requirements.txt", "graphbus-core>=0.1.0\ngraphbus-cli>=0.1.0\n")
