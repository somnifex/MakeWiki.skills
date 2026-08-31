"""Tests for LLM-authored DocumentationModel validation models.

These artifacts are LLM-authored; Python only validates the schema and serializes.
Tests confirm validation strictness (``extra="forbid"``), serialization round-trips,
and that Python never infers cognitive fields (personas, capabilities, journeys,
visibility, etc.).
"""

from makewiki_skills.model.documentation_model import (
    ApiParameter,
    AuthSpec,
    Capability,
    Concept,
    DocumentationGap,
    DocumentationModel,
    HttpOperationReference,
    HttpResponseSpec,
    InterfaceReference,
    Journey,
    Persona,
    ReferenceItem,
    RequestBodySpec,
)

import pytest
from pydantic import ValidationError


def _sample_model() -> DocumentationModel:
    return DocumentationModel(
        personas=[
            Persona(
                id="operator",
                name="Operator",
                goals=["deploy safely", "monitor health"],
                permissions=[],
                evidence_refs=["docs/ops.md"],
                confidence="high",
            )
        ],
        capabilities=[
            Capability(
                id="channel.manage",
                name="Manage channels",
                personas=["admin", "operator"],
                goal="Configure upstream provider connectivity.",
                operations=["create", "edit", "test", "disable", "delete"],
                constraints=[],
                evidence_refs=["src/channels/"],
                visibility="admin",
            )
        ],
        journeys=[
            Journey(
                id="channel.add",
                persona="admin",
                goal="Add an upstream provider channel.",
                prerequisites=["provider credentials"],
                steps=["choose provider/channel type", "provide credentials"],
                expected_result=["channel becomes available to routing"],
                failure_conditions=[],
                evidence_refs=["src/channels/"],
            )
        ],
        concepts=[
            Concept(
                id="channel",
                definition="A provider connectivity endpoint.",
                why_it_matters="Channels are what routing uses.",
                related=["model", "group", "routing"],
                evidence_refs=["concepts.md"],
            )
        ],
        references=[
            ReferenceItem(
                id="env.API_PORT",
                name="API_PORT",
                kind="environment variable",
                description="Listener port.",
                evidence_refs=["src/server.py"],
            )
        ],
        documentation_gaps=[
            DocumentationGap(
                id="gap.admin-api.error-schema",
                severity="major",
                reason="Error response schema is not established by evidence.",
                affected_pages=["admin-api/channel-create"],
            )
        ],
    )


def test_documentation_model_serialization_round_trip():
    model = _sample_model()
    payload = model.model_dump_json()
    rebuilt = DocumentationModel.model_validate_json(payload)
    assert rebuilt == model


def test_documentation_model_defaults_are_empty():
    model = DocumentationModel()
    payload = model.model_dump_json()
    rebuilt = DocumentationModel.model_validate_json(payload)
    assert rebuilt == model
    assert rebuilt.personas == []
    assert rebuilt.capabilities == []
    assert rebuilt.journeys == []
    assert rebuilt.concepts == []
    assert rebuilt.references == []
    assert rebuilt.interface_references == []
    assert rebuilt.documentation_gaps == []


def test_documentation_model_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        DocumentationModel.model_validate({"inferred_personas": []})


def test_inner_models_reject_unknown_keys():
    with pytest.raises(ValidationError):
        Persona.model_validate({"role_map": "inferred"})
    with pytest.raises(ValidationError):
        Capability.model_validate({"fabricated_operation": True})
    with pytest.raises(ValidationError):
        Journey.model_validate({"ui_coordinates": "x=1,y=2"})


def test_visibility_is_an_opaque_llm_string():
    """Python must not constrain visibility to a fixed vocabulary."""
    cap = Capability(id="c", visibility="some_llm_judgment")
    assert cap.visibility == "some_llm_judgment"


def _sample_interface_model() -> DocumentationModel:
    return DocumentationModel(
        personas=[Persona(id="operator", name="Operator")],
        interface_references=[
            InterfaceReference(
                id="iface.management-api",
                kind="HTTP API",
                name="Management API",
                description="Operator-facing management HTTP API.",
                http_operations=[
                    HttpOperationReference(
                        id="channel.create",
                        method="POST",
                        path="/admin/channels",
                        purpose="Create a provider channel.",
                        audience=["admin", "operator"],
                        auth=AuthSpec(
                            scheme="Bearer", required="unknown", permissions=[]
                        ),
                        path_parameters=[],
                        query_parameters=[],
                        headers=[],
                        request_body=RequestBodySpec(
                            required="unknown",
                            content_types=["application/json"],
                            schema_items=[],
                            example=None,
                        ),
                        responses=[
                            HttpResponseSpec(
                                status="200", meaning="Channel created.", example=None
                            )
                        ],
                        errors=[],
                        side_effects=["Channel becomes available to routing."],
                        idempotency="unknown",
                        pagination=None,
                        evidence_refs=["src/admin/channels.py"],
                        confidence="medium",
                    )
                ],
                evidence_refs=["src/admin/"],
            )
        ],
    )


def test_interface_reference_serialization_round_trip():
    model = _sample_interface_model()
    payload = model.model_dump_json()
    rebuilt = DocumentationModel.model_validate_json(payload)
    assert rebuilt == model
    ref = rebuilt.interface_references[0]
    op = ref.http_operations[0]
    assert op.method == "POST"
    assert op.path == "/admin/channels"
    assert op.auth.required == "unknown"
    assert op.request_body.example is None
    assert op.responses[0].status == "200"


def test_interface_operation_allows_unknown_null():
    """Unproven fields are optional (None / empty / 'unknown') — no fake Swagger
    is required, and no plausible-but-invented schema is forced in."""
    op = HttpOperationReference(id="op.x", method="GET", path="/x")
    assert op.auth is None
    assert op.request_body is None
    assert op.responses == []
    assert op.errors == []
    assert op.idempotency is None
    assert op.pagination is None
    assert op.rate_limits is None
    # A fully unproven operation still models cleanly (unknown/null allowed).
    rebuilt = HttpOperationReference.model_validate_json(
        HttpOperationReference(id="op.x", method="GET", path="/x").model_dump_json()
    )
    assert rebuilt == op


def test_interface_reference_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        InterfaceReference.model_validate({"swagger_spec": {...}})


def test_interface_reference_kind_is_opaque_llm_string():
    ref = InterfaceReference(id="iface.cli", kind="CLI", name="acme")
    assert ref.kind == "CLI"
    ref2 = InterfaceReference(id="iface.o", kind="some_new_interface_kind")
    assert ref2.kind == "some_new_interface_kind"
