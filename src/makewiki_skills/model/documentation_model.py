"""LLM-authored DocumentationModel validation models.

The DocumentationModel answers *which people, for which goals, need to understand
which concepts, perform which tasks, and query which references* (the SemanticModel
answers *what the software is*). Every field here is **authored by the Documentation
Architect LLM**; Python only performs schema validation and serialization.

Python MUST NOT infer personas, capabilities, journeys, concepts, references, or
documentation gaps from source, filenames, or patterns — any such cognitive judgment
is the LLM's, and unproven fields stay empty / ``None`` rather than being guessed.
See ``references/v3/DOCUMENTATION_MODEL.md``.

This module (Phase G) implements the DocumentationModel: ``Persona``,
``Capability``, ``Journey``, ``Concept``, ``ReferenceItem``, ``DocumentationGap``,
the container ``DocumentationModel`` (task G1), and the interface models
``InterfaceReference`` / ``HttpOperationReference`` with their parameter /
request / response supporting structures (task G2).

Interface references are *part of the DocumentationModel* — they are NOT
Python-generated OpenAPI. Every unproven field stays ``None`` / omitted / the
string ``"unknown"``; Python never builds a plausible-but-fake response schema.
See ``references/v3/API_REFERENCE.md``.

All models use ``extra="forbid"`` so a hand-authored artifact with a typo'd or
unexpected key fails loudly at load time instead of being silently dropped.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

#: Forbid unknown keys so a hand-authored model with a typo'd or unexpected key
#: fails loudly at validation time instead of being silently dropped.
_MODEL_CONFIG = ConfigDict(extra="forbid")

_Confidence = Literal["high", "medium", "low", "unknown"]


class Persona(BaseModel):
    """A distinct audience with stable goals.

    Not a fixed mandatory list (``DOCUMENTATION_MODEL`` §2) — only personas with
    evidence exist. Authored by the Documentation Architect LLM.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    name: str = ""
    goals: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class Capability(BaseModel):
    """A stable product ability one or more personas can use or depend on."""

    model_config = _MODEL_CONFIG

    id: str = ""
    name: str = ""
    personas: list[str] = Field(default_factory=list)
    goal: str = ""
    operations: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    # LLM-authored visibility judgment — Python does not classify it.
    visibility: str = ""
    confidence: _Confidence = "medium"


class Journey(BaseModel):
    """The semantic steps of a user / operator goal.

    UI coordinates and button labels are not required; steps must be provable from
    source. A step that cannot be proven is downgraded in confidence or removed,
    never padded (``DOCUMENTATION_MODEL`` §4).
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    persona: str = ""
    goal: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    expected_result: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class Concept(BaseModel):
    """A concept serving explanation / mental model."""

    model_config = _MODEL_CONFIG

    id: str = ""
    definition: str = ""
    why_it_matters: str = ""
    related: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class ReferenceItem(BaseModel):
    """A stable-lookup reference (config keys, env vars, CLI commands, model
    fields, file formats, compatibility, etc.)."""

    model_config = _MODEL_CONFIG

    id: str = ""
    name: str = ""
    # LLM-authored kind — Python does not infer it.
    kind: str = ""
    description: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class DocumentationGap(BaseModel):
    """An important capability that cannot be fully documented.

    Gaps are recorded, not hidden (``DOCUMENTATION_MODEL`` §8). ``severity`` /
    ``reason`` are LLM-authored; Python only validates.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    severity: str = ""
    reason: str = ""
    affected_pages: list[str] = Field(default_factory=list)


class AuthSpec(BaseModel):
    """Authentication for an interface operation.

    All fields are optional so unproven auth remains ``None``/``unknown`` rather
    than guessed (``API_REFERENCE`` §3). ``required`` is a true tri-state:
    ``True`` / ``False`` / ``None`` (none means unknown / not provable).
    """

    model_config = _MODEL_CONFIG

    scheme: str = ""
    required: bool | None = None
    permissions: list[str] = Field(default_factory=list)


class ApiParameter(BaseModel):
    """A path / query / header parameter of an HTTP operation."""

    model_config = _MODEL_CONFIG

    name: str = ""
    # where it appears: path | query | header (LLM-authored, not enforced here).
    location: str = ""
    required: bool | None = None
    description: str = ""


class SchemaField(BaseModel):
    """One structural field of a request / response schema.

    ``name`` / ``type`` identify the field; ``required`` is a tri-state bool
    (``None`` = unknown); ``default`` / ``constraints`` carry proven constraints.
    Every field stays ``""`` / ``None`` when unproven. Python does NOT parse a
    JSON Schema — the Documentation Architect LLM populates these from source
    evidence (``API_REFERENCE`` §3).
    """

    model_config = _MODEL_CONFIG

    name: str = ""
    type: str = ""
    required: bool | None = None
    description: str = ""
    default: Any | None = None
    constraints: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class RequestBodySpec(BaseModel):
    """Request body of an HTTP operation.

    ``required`` / ``schema_items`` (the operation's ``schema`` list) stay
    unproven as ``None``/empty; ``example`` is ``None`` when the repository does
    not establish one. ``required`` is a tri-state bool (``None`` = unknown).
    ``schema_items`` is a list of ``SchemaField`` models (never a free
    ``list[Any]``), keeping the structure stable. The attribute is named
    ``schema_items`` to avoid shadowing the pydantic ``BaseModel.schema`` member.
    """

    model_config = _MODEL_CONFIG

    required: bool | None = None
    content_types: list[str] = Field(default_factory=list)
    schema_items: list[SchemaField] = Field(default_factory=list)
    example: Any | None = None


class HttpResponseSpec(BaseModel):
    """A known response of an HTTP operation.

    ``schema_items`` corresponds to the response's ``schema`` list; named to avoid
    shadowing the pydantic ``BaseModel.schema`` member. It is a list of
    ``SchemaField`` models, never ``list[Any]``.
    """

    model_config = _MODEL_CONFIG

    status: str | None = None
    meaning: str = ""
    schema_items: list[SchemaField] = Field(default_factory=list)
    example: Any | None = None


class ApiErrorSpec(BaseModel):
    """One documented error condition of an HTTP operation.

    ``status`` is an int when a mapper / error type / test / spec / handler
    proves the specific HTTP code; ``None`` means the condition is real but the
    code is not established (``API_REFERENCE`` §11) — Python never maps an
    exception to a status. ``schema_items`` corresponds to the error's ``schema``
    list (``SchemaField`` models, never free-``Any``); named to avoid shadowing
    the pydantic ``BaseModel.schema`` member. ``condition`` / ``meaning`` /
    ``confidence`` are LLM-authored.
    """

    model_config = _MODEL_CONFIG

    status: int | None = None
    code: str | None = None
    condition: str = ""
    meaning: str = ""
    schema_items: list[SchemaField] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class PaginationSpec(BaseModel):
    """How an HTTP operation paginates its response.

    ``style`` (e.g. ``offset`` / ``cursor``) and the parameter / response field
    names are LLM-authored from source evidence; every field stays ``None`` /
    empty / unknown when unproven. Python does NOT detect pagination — it only
    validates and serializes the structure (``API_REFERENCE`` §3).
    """

    model_config = _MODEL_CONFIG

    style: str = ""
    page_parameter: str = ""
    size_parameter: str = ""
    cursor_parameter: str = ""
    default_size: int | None = None
    max_size: int | None = None
    response_fields: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class HttpOperationReference(BaseModel):
    """One documented HTTP operation (``API_REFERENCE`` §3).

    Every unproven field stays ``None`` / omitted / ``"unknown"`` — Python never
    fabricates a response schema or an error status. All judgment fields are
    LLM-authored.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    method: str = ""
    path: str = ""
    purpose: str = ""
    audience: list[str] = Field(default_factory=list)
    auth: AuthSpec | None = None
    path_parameters: list[ApiParameter] = Field(default_factory=list)
    query_parameters: list[ApiParameter] = Field(default_factory=list)
    headers: list[ApiParameter] = Field(default_factory=list)
    request_body: RequestBodySpec | None = None
    responses: list[HttpResponseSpec] = Field(default_factory=list)
    errors: list[ApiErrorSpec] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    idempotency: str | None = None
    pagination: PaginationSpec | None = None
    filtering: list[str] = Field(default_factory=list)
    sorting: list[str] = Field(default_factory=list)
    rate_limits: str | None = None
    operational_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class InterfaceReference(BaseModel):
    """An interface-class reference (HTTP / admin / management API, RPC, webhook,
    event, health / metrics endpoint, CLI, config interface; ``DOCUMENTATION_MODEL`` §7).

    ``kind`` is an LLM-authored judgment (Python does not infer it). ``http_operations``
    is only populated for HTTP-style kinds; other interface kinds carry their own
    ``description`` / details and leave it empty. ``cli_commands`` holds
    first-class ``CliCommandReference`` entries for CLI-style kinds.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    kind: str = ""
    name: str = ""
    description: str = ""
    http_operations: list[HttpOperationReference] = Field(default_factory=list)
    cli_commands: list[CliCommandReference] = Field(default_factory=list)
    config_items: list[ConfigReference] = Field(default_factory=list)
    operational_endpoints: list[OperationalEndpointReference] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class OperationalEndpointReference(BaseModel):
    """A health / readiness / metrics / diagnostics / maintenance endpoint as a
    first-class operator reference (``API_REFERENCE`` §9).

    ``kind`` is an LLM-authored judgment (Python does not infer it — e.g. it
    never assumes a path named ``/health`` is a health endpoint). ``healthy_semantics``
    / ``failure_semantics`` / ``operator_implications`` are authored; operator
    action notes must be evidence-backed or clearly advisory, never a fake
    software contract.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    kind: str = ""  # health | readiness | metrics | diagnostics | maintenance | other
    method: str = ""
    path: str = ""
    purpose: str = ""
    audience: list[str] = Field(default_factory=list)
    auth: AuthSpec | None = None
    healthy_semantics: str = ""
    failure_semantics: str = ""
    fields: list[SchemaField] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    operator_implications: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class ConfigReference(BaseModel):
    """One operator-facing configuration key / surface as a first-class reference
    (``API_REFERENCE`` §2 "configuration interface").

    ``type`` / ``default`` / ``precedence`` / ``runtime_effect`` etc. are
    LLM-authored from source evidence (``COGNITIVE_BOUNDARY``). Python does NOT
    read config files to auto-generate these objects; every unproven field stays
    ``""`` / ``None``.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    key: str = ""
    audience: list[str] = Field(default_factory=list)
    purpose: str = ""
    type: str = ""
    required: bool | None = None
    default: Any | None = None
    source: str = ""
    sensitive: bool | None = None
    precedence: str = ""
    runtime_effect: str = ""
    reload_required: bool | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class CliCommandReference(BaseModel):
    """One operator/developer CLI command as a first-class interface reference
    (``API_REFERENCE`` §10).

    ``arguments`` / ``options`` / ``inputs`` / ``outputs`` / ``examples`` are
    LLM-authored from source evidence; every unproven field stays ``""``/empty.
    Python does NOT parse the CLI or infer semantics — it only validates the
    authored structure.
    """

    model_config = _MODEL_CONFIG

    id: str = ""
    command: str = ""
    audience: list[str] = Field(default_factory=list)
    purpose: str = ""
    arguments: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    exit_behavior: str = ""
    examples: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: _Confidence = "medium"


class DocumentationModel(BaseModel):
    """The Documentation Architect's audience / goal model.

    All fields are LLM-authored; Python only validates the schema and serializes —
    it never infers an entry. ``interface_references`` holds ``InterfaceReference``
    models (HTTP operations per ``API_REFERENCE``)."""

    model_config = _MODEL_CONFIG

    personas: list[Persona] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    journeys: list[Journey] = Field(default_factory=list)
    concepts: list[Concept] = Field(default_factory=list)
    references: list[ReferenceItem] = Field(default_factory=list)
    interface_references: list[InterfaceReference] = Field(default_factory=list)
    documentation_gaps: list[DocumentationGap] = Field(default_factory=list)
