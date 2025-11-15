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
        extractor = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, method

@agent(name="DataExtractor", description="Extracts data from source")
class DataExtractor(NodeBase):
    @method(description="Extract data", parameters={}, return_type="dict")
    def extract(self) -> dict:
        data = {"records": [{"id": 1, "value": "test"}]}
        self.publish("/data/extracted", data)
        return data
'''

        # Transformer agent
        transformer = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes

@agent(name="DataTransformer", description="Transforms data")
class DataTransformer(NodeBase):
    @subscribes("/data/extracted")
    def on_data_extracted(self, payload):
        records = payload.get("records", [])
        transformed = [{"id": r["id"], "value": r["value"].upper()} for r in records]
        self.publish("/data/transformed", {"records": transformed})
'''

        # Loader agent
        loader = '''from graphbus_core.node_base import NodeBase
from graphbus_core.decorators import agent, subscribes

@agent(name="DataLoader", description="Loads data to destination")
class DataLoader(NodeBase):
    def __init__(self):
        super().__init__()
        self.loaded_count = 0

    @subscribes("/data/transformed")
    def on_data_transformed(self, payload):
        records = payload.get("records", [])
        self.loaded_count += len(records)
        self.publish("/data/loaded", {"count": len(records)})
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
