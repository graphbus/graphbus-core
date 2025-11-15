"""
Schema primitives for method contracts
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Schema:
    """
    Schema describing input/output contracts.
    """
    fields: dict[str, type]  # field_name -> type
    description: str | None = None

    def validate(self, data: dict) -> bool:
        """
        Simple validation: check that all required fields are present and have correct types.
        """
        for field_name, field_type in self.fields.items():
            if field_name not in data:
                return False
            if not isinstance(data[field_name], field_type):
                return False
        return True

    def to_dict(self) -> dict:
        """
        Serialize to dict for JSON artifacts.
        """
        return {
            "fields": {name: typ.__name__ for name, typ in self.fields.items()},
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schema":
        """
        Deserialize from dict.
        """
        # Convert type names back to types
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        fields = {name: type_map.get(typ, str) for name, typ in data.get("fields", {}).items()}
        return cls(fields=fields, description=data.get("description"))


@dataclass
class SchemaMethod:
    """
    Method with input/output schema contracts.
    """
    name: str
    input_schema: Schema
    output_schema: Schema
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "input_schema": self.input_schema.to_dict(),
            "output_schema": self.output_schema.to_dict(),
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SchemaMethod":
        return cls(
            name=data["name"],
            input_schema=Schema.from_dict(data["input_schema"]),
            output_schema=Schema.from_dict(data["output_schema"]),
            description=data.get("description")
        )
