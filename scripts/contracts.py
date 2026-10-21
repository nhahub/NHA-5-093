"""Use the canonical schemas directly; never fetch remote schema references."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


class ContractError(ValueError):
    """Invalid or unresolved contract, with no payload contents in the message."""


class Contracts:
    def __init__(self, root: Path = ROOT):
        self.root = root.resolve()
        self.base = self.root / "contracts"
        self.schemas = {}
        self.registry = Registry()
        self.resources = {}
        for path in sorted((self.base / "schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            name = path.name.removesuffix(".schema.json")
            identifier = schema["$id"]
            if identifier in self.resources:
                raise ContractError(f"Duplicate schema identifier: {name}")
            self.schemas[name] = schema
            for uri in (identifier, path.resolve().as_uri()):
                self.resources[uri] = schema
                self.registry = self.registry.with_resource(uri, Resource.from_contents(schema))
        if not self.schemas:
            raise ContractError("No canonical schemas found")

    def fixture(self, name: str):
        return json.loads((self.base / "examples" / f"{name}.json").read_text(encoding="utf-8"))

    def validate(self, name: str, value):
        self.validate_schema(self.schemas[name], value, name)

    def validate_schema(self, schema, value, label="payload"):
        if "$id" not in schema:
            schema = {"$id": (self.base / "openapi.yaml").as_uri(), **schema}
        validator = Draft202012Validator(
            schema, registry=self.registry, format_checker=FormatChecker()
        )
        try:
            error = next(validator.iter_errors(value), None)
        except Exception as exc:
            raise ContractError(f"Unresolved schema for {label}") from exc
        if error:
            location = "/".join(map(str, error.absolute_path)) or "<root>"
            raise ContractError(f"{label}: {error.validator} constraint at {location}")

    def check_references(self, document, base_uri: str):
        if isinstance(document, list):
            for item in document:
                self.check_references(item, base_uri)
        elif isinstance(document, dict):
            base_uri = urljoin(base_uri, document.get("$id", ""))
            if "$ref" in document:
                uri, fragment = urldefrag(urljoin(base_uri, document["$ref"]))
                if uri not in self.resources:
                    raise ContractError(f"Unregistered reference: {document['$ref']}")
                value = self.resources[uri]
                if fragment:
                    if not fragment.startswith("/"):
                        raise ContractError("Only JSON Pointer reference fragments are supported")
                    try:
                        for part in fragment[1:].split("/"):
                            key = part.replace("~1", "/").replace("~0", "~")
                            value = value[int(key)] if isinstance(value, list) else value[key]
                    except (KeyError, ValueError, IndexError, TypeError) as exc:
                        raise ContractError("Unresolved JSON Pointer") from exc
            for key, value in document.items():
                if key != "$ref":
                    self.check_references(value, base_uri)


def local_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ContractError("Integration target must be a loopback HTTP origin")
    return url.rstrip("/")
