"""Tests for LLM-authored DocumentationModel validation models.

These artifacts are LLM-authored; Python only validates the schema and serializes.
Tests confirm validation strictness (``extra="forbid"``), serialization round-trips,
and that Python never infers cognitive fields (personas, capabilities, journeys,
visibility, etc.).
"""

import pytest
from pydantic import ValidationError

from makewiki_skills.model.documentation_model import (
    ApiErrorSpec,
    ApiParameter,
    AuthSpec,
    Capability,
    CliCommandReference,
    Concept,
    ConfigReference,
    DocumentationGap,
    DocumentationModel,
    HttpOperationReference,
    HttpResponseSpec,
    InterfaceDisposition,
    InterfaceReference,
    Journey,
    OperationalEndpointReference,
    PaginationSpec,
    Persona,
    ReferenceItem,
    RequestBodySpec,
    SchemaField,
)


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


def test_cognitive_entities_share_provenance_contract():
    """Persona / Capability / Journey / Concept / ReferenceItem / InterfaceReference
    all expose a uniform ``evidence_refs`` + ``confidence`` contract with a
    backward-compatible default, and confidence accepts the existing
    high/medium/low/unknown convention."""
    entities = [
        Persona(),
        Capability(),
        Journey(),
        Concept(),
        ReferenceItem(),
        InterfaceReference(),
    ]
    for entity in entities:
        assert entity.evidence_refs == []
        assert entity.confidence == "medium"

    # 'unknown' is an allowed LLM-authored confidence value (existing convention).
    assert Capability(confidence="unknown").confidence == "unknown"
    assert Journey(confidence="unknown").confidence == "unknown"
    assert InterfaceReference(confidence="unknown").confidence == "unknown"


def test_cognitive_confidence_rejects_fabricated_value():
    """Confidence stays within the LLM-authored convention; Python never scores it."""
    with pytest.raises(ValidationError):
        Capability(confidence="certain")


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
                            scheme="Bearer", required=None, permissions=[]
                        ),
                        path_parameters=[],
                        query_parameters=[],
                        headers=[],
                        request_body=RequestBodySpec(
                            required=None,
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
    assert op.auth.required is None
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


def test_required_is_a_tri_state_bool():
    """AuthSpec / ApiParameter / RequestBodySpec.required is true/false/unknown
    (None) — never a free-form string, so weak models cannot fake a value."""
    # None == unknown (backward-compatible default).
    assert AuthSpec().required is None
    assert ApiParameter().required is None
    assert RequestBodySpec().required is None
    # Explicit true / false persist (string "true" coerces to bool via
    # pydantic's standard bool parsing, keeping JSON/YAML serialization clean).
    assert AuthSpec(required=True).required is True
    assert AuthSpec(required=False).required is False
    assert RequestBodySpec(required=False).required is False
    assert ApiParameter(required="true").required is True
    # A non-boolean string like "unknown" must be rejected — required is now
    # strictly bool|None, so a weak model cannot smuggle an unverifiable value.
    with pytest.raises(ValidationError):
        AuthSpec(required="unknown")
    with pytest.raises(ValidationError):
        ApiParameter(required="maybe")


def test_schema_field_is_a_structured_model():
    """Request / response ``schema`` items are typed SchemaField models, never
    free ``list[Any]`` — an unstable free-dict schema cannot be smuggled in."""
    field = SchemaField(
        name="priority",
        type="integer",
        required=True,
        description="Routing priority.",
        default=0,
        constraints=["min=0"],
        evidence_refs=["src/schema.py:10"],
    )
    assert field.name == "priority"
    assert field.type == "integer"
    assert field.required is True
    assert field.default == 0
    assert field.constraints == ["min=0"]
    assert field.evidence_refs == ["src/schema.py:10"]
    # Round-trip through a request body.
    body = RequestBodySpec(
        required=False,
        content_types=["application/json"],
        schema_items=[field],
        example={"priority": 3},
    )
    payload = body.model_dump_json()
    rebuilt = RequestBodySpec.model_validate_json(payload)
    assert rebuilt == body
    assert rebuilt.schema_items[0].name == "priority"
    # A free-form, non-SchemaField dict entry must be rejected — an unknown key
    # (``extra="forbid"``) proves schema_items is no longer a free list[Any].
    with pytest.raises(ValidationError):
        RequestBodySpec.model_validate({"schema_items": [{"free_form": True}]})
    with pytest.raises(ValidationError):
        HttpResponseSpec.model_validate({"schema_items": [{"x-extra": "y"}]})


def test_api_error_spec_is_a_structured_model():
    """Errors are typed ApiErrorSpec models — status is an int only when proven,
    and stays None (never auto-mapped from an exception)."""
    op = HttpOperationReference(
        id="channel.create",
        method="POST",
        path="/admin/channels",
        errors=[
            ApiErrorSpec(
                status=400,
                code="invalid_channel",
                condition="At least one provider field is invalid.",
                meaning="The request could not create the channel.",
                schema_items=[SchemaField(name="detail", type="string")],
                evidence_refs=["src/admin/channels.py:88"],
                confidence="high",
            ),
            ApiErrorSpec(
                status=None,
                condition="Upstream provider is unreachable.",
                meaning="Failed to connect to the configured provider.",
                confidence="medium",
            ),
        ],
    )
    assert op.errors[0].status == 400
    assert op.errors[0].code == "invalid_channel"
    assert op.errors[0].schema_items[0].name == "detail"
    # Unproven HTTP code stays None — Python never fabricates a status.
    assert op.errors[1].status is None
    # Round-trip.
    rebuilt = HttpOperationReference.model_validate_json(op.model_dump_json())
    assert rebuilt == op
    # A free-form dict error entry is rejected (no list[Any]).
    with pytest.raises(ValidationError):
        HttpOperationReference.model_validate({"errors": [{"http_status": 500}]})


def test_pagination_spec_is_a_structured_model():
    """Pagination is a typed PaginationSpec (or None) — not a free Any dict, and
    never auto-detected by Python."""
    op = HttpOperationReference(
        id="channel.list",
        method="GET",
        path="/admin/channels",
        pagination=PaginationSpec(
            style="cursor",
            cursor_parameter="cursor",
            size_parameter="limit",
            default_size=50,
            max_size=500,
            response_fields=["next_cursor", "items"],
            evidence_refs=["src/admin/channels.py:120"],
            confidence="high",
        ),
    )
    assert op.pagination.style == "cursor"
    assert op.pagination.default_size == 50
    assert op.pagination.response_fields == ["next_cursor", "items"]
    # Round-trip.
    rebuilt = HttpOperationReference.model_validate_json(op.model_dump_json())
    assert rebuilt == op
    # Unproven pagination stays None; a free-Any dict is rejected (extra=forbid).
    assert HttpOperationReference(id="op", method="GET", path="/x").pagination is None
    with pytest.raises(ValidationError):
        HttpOperationReference.model_validate(
            {"pagination": {"next_page_token_only": True}}
        )


def test_cli_command_reference_is_first_class_in_interface():
    """An operator CLI is a typed CliCommandReference inside InterfaceReference —
    not a loose description blob, and not parsed by Python."""
    ref = InterfaceReference(
        id="iface.cli",
        kind="CLI",
        name="acme-admin",
        description="Operator maintenance CLI.",
        cli_commands=[
            CliCommandReference(
                id="cli.channel.add",
                command="acme-admin channel add --provider <id>",
                audience=["operator"],
                purpose="Create a provider channel from the CLI.",
                arguments=["provider", "name"],
                options=["--region", "--dry-run"],
                inputs=["provider credentials file"],
                outputs=["channel id and summary"],
                side_effects=["Channel becomes available to routing."],
                exit_behavior="exit 0 on success, non-zero on failure.",
                examples=["acme-admin channel add --provider up1"],
                evidence_refs=["cmd/channel.go:40"],
                confidence="high",
            )
        ],
    )
    assert ref.kind == "CLI"
    cmd = ref.cli_commands[0]
    assert cmd.command == "acme-admin channel add --provider <id>"
    assert cmd.arguments == ["provider", "name"]
    assert cmd.exit_behavior != ""
    # Round-trip.
    rebuilt = InterfaceReference.model_validate_json(ref.model_dump_json())
    assert rebuilt == ref
    assert rebuilt.cli_commands[0].id == "cli.channel.add"
    # A free-form command dict is rejected (typed model, extra=forbid).
    with pytest.raises(ValidationError):
        InterfaceReference.model_validate(
            {"cli_commands": [{"subcommand_auto_inferred": True}]}
        )


def test_config_reference_is_a_structured_model():
    """Operator config is a typed ConfigReference in InterfaceReference — never
    auto-read from config files; unprovable fields stay None/empty."""
    ref = InterfaceReference(
        id="iface.config",
        kind="configuration interface",
        name="acme-admin config",
        config_items=[
            ConfigReference(
                id="cfg.api.port",
                key="API_PORT",
                audience=["operator"],
                purpose="Listener port for the management API.",
                type="integer",
                required=True,
                default=8080,
                source="src/config.py",
                sensitive=False,
                precedence="env overrides default",
                runtime_effect="Changes the bound port on restart.",
                reload_required=False,
                evidence_refs=["src/config.py:15"],
                confidence="high",
            ),
            ConfigReference(
                id="cfg.api.token",
                key="API_TOKEN",
                purpose="Admin API bearer token.",
                sensitive=True,
                confidence="medium",
            ),
        ],
    )
    cfg = ref.config_items[0]
    assert cfg.key == "API_PORT"
    assert cfg.required is True
    assert cfg.default == 8080
    assert cfg.sensitive is False
    # Unproven fields stay None (reload not established for the token).
    assert ref.config_items[1].reload_required is None
    # Round-trip.
    rebuilt = InterfaceReference.model_validate_json(ref.model_dump_json())
    assert rebuilt == ref
    # A free-form config dict is rejected.
    with pytest.raises(ValidationError):
        InterfaceReference.model_validate(
            {"config_items": [{"auto_scanned": True}]}
        )


def test_operational_endpoint_reference_structured_and_kind_opaque():
    """Health / readiness / metrics endpoints are typed OperationalEndpointReference;
    ``kind`` is an opaque LLM string Python never infers from a path."""
    ref = InterfaceReference(
        id="iface.ops",
        kind="health & metrics",
        name="Observability surface",
        operational_endpoints=[
            OperationalEndpointReference(
                id="ops.health",
                kind="health",
                method="GET",
                path="/healthz",
                purpose="Report process health.",
                audience=["operator"],
                auth=AuthSpec(scheme="none", required=False),
                healthy_semantics="Returns 200 while the process can serve traffic.",
                failure_semantics="Returns 503 when a backing dependency is down.",
                fields=[SchemaField(name="status", type="string")],
                dependencies=["database", "message broker"],
                operator_implications=[
                    "Advisory: alert if non-200 for >5 minutes."
                ],
                evidence_refs=["src/routes/healthz.py"],
                confidence="high",
            ),
            OperationalEndpointReference(id="ops.x", kind="some_new_kind"),
        ],
    )
    h = ref.operational_endpoints[0]
    assert h.kind == "health"
    assert h.path == "/healthz"
    assert h.auth.required is False
    assert h.dependencies == ["database", "message broker"]
    # ``kind`` stays an opaque LLM judgment — a new value is accepted verbatim.
    assert ref.operational_endpoints[1].kind == "some_new_kind"
    # Round-trip.
    rebuilt = InterfaceReference.model_validate_json(ref.model_dump_json())
    assert rebuilt == ref
    # A free-form endpoint dict is rejected.
    with pytest.raises(ValidationError):
        InterfaceReference.model_validate(
            {"operational_endpoints": [{"path_inferred_kind": True}]}
        )




def test_interface_reference_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        InterfaceReference.model_validate({"swagger_spec": {...}})


def test_interface_reference_kind_is_opaque_llm_string():
    ref = InterfaceReference(id="iface.cli", kind="CLI", name="acme")
    assert ref.kind == "CLI"
    ref2 = InterfaceReference(id="iface.o", kind="some_new_interface_kind")
    assert ref2.kind == "some_new_interface_kind"


# --- InterfaceDisposition (interface 去向) ---


def _sample_dispositions() -> list[InterfaceDisposition]:
    return [
        InterfaceDisposition(
            operation_id="channel.create",
            disposition="documented",
            page_id="reference/management-api/channels/create",
        ),
        InterfaceDisposition(
            operation_id="channel.list",
            disposition="grouped",
            page_id="reference/management-api/channels/index",
        ),
        InterfaceDisposition(
            operation_id="channel.internal-probe",
            disposition="omitted",
            reason="internal-only, not for the target persona",
        ),
        InterfaceDisposition(
            operation_id="channel.legacy-sync",
            disposition="unresolved",
            gap_id="gap.legacy-sync.disposition",
        ),
    ]


def test_interface_disposition_serialization_round_trip():
    """A documented model with dispositions survives a JSON round-trip."""
    model = DocumentationModel(
        interface_dispositions=_sample_dispositions()
    )
    payload = model.model_dump_json()
    rebuilt = DocumentationModel.model_validate_json(payload)
    assert rebuilt == model
    assert len(rebuilt.interface_dispositions) == 4
    assert rebuilt.interface_dispositions[0].operation_id == "channel.create"


def test_interface_disposition_defaults_are_empty():
    """``interface_dispositions`` is an optional, backward-compatible list."""
    model = DocumentationModel()
    assert model.interface_dispositions == []
    payload = model.model_dump_json()
    rebuilt = DocumentationModel.model_validate_json(payload)
    assert rebuilt.interface_dispositions == []


def test_interface_disposition_accepts_all_four_kinds():
    """documented / grouped / omitted / unresolved each validate with their
    required field supplied."""
    for d in _sample_dispositions():
        assert InterfaceDisposition.model_validate_json(d.model_dump_json()) == d


def test_interface_disposition_requires_operation_id():
    """Every disposition must name the operation it disposes of."""
    with pytest.raises(ValidationError):
        InterfaceDisposition(operation_id="", disposition="documented", page_id="p")


def test_documented_and_grouped_require_page_id():
    """documented / grouped must carry a page target (never a silent skip)."""
    with pytest.raises(ValidationError):
        InterfaceDisposition(
            operation_id="channel.create", disposition="documented", page_id=""
        )
    with pytest.raises(ValidationError):
        InterfaceDisposition(
            operation_id="channel.list", disposition="grouped", page_id="   "
        )


def test_omitted_requires_reason():
    """omitted must give a semantic reason (e.g. internal-only), not a silent drop."""
    with pytest.raises(ValidationError):
        InterfaceDisposition(
            operation_id="channel.internal", disposition="omitted", reason=""
        )


def test_unresolved_requires_gap_id():
    """unresolved must point at a documentation_gap — never claim to be covered."""
    with pytest.raises(ValidationError):
        InterfaceDisposition(
            operation_id="channel.x", disposition="unresolved", gap_id=""
        )


def test_interface_disposition_rejects_unknown_disposition():
    """Only the four contract values are allowed; Python never invents a kind."""
    with pytest.raises(ValidationError):
        InterfaceDisposition.model_validate(
            {"operation_id": "x", "disposition": "auto_documented"}
        )


def test_interface_disposition_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        InterfaceDisposition.model_validate(
            {"operation_id": "x", "disposition": "documented", "page_priority": 1}
        )


def test_interface_disposition_does_not_judge_importance():
    """Python validates self-consistency only — it never rejects a disposition on
    semantic grounds (e.g. whether an operation *should* be documented)."""
    d = InterfaceDisposition(
        operation_id="channel.obscure",
        disposition="omitted",
        reason="low value for the documented persona",
    )
    assert d.disposition == "omitted"

