"""L4 Cross-Language Verifier: Validate 100% code block and claim parity across languages."""

from __future__ import annotations

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer
from makewiki_skills.verification.report import LayerReport, VerificationCheck


class L4CrossLanguageVerifier:
    """Verify factual parity across all multilingual documentation versions."""

    def __init__(self) -> None:
        self._reviewer = CrossLanguageReviewer()

    def verify_documents(
        self,
        documents: dict[str, list[GeneratedDocument]],
    ) -> LayerReport:
        languages = list(documents.keys())
        if len(languages) < 2:
            # With a single language there is nothing to compare for parity, so
            # cross-language verification is genuinely not applicable. It must
            # never be reported as "passed" - no parity check actually ran.
            return LayerReport(
                layer="L4",
                name="Cross-Language",
                checks=[
                    VerificationCheck(
                        layer="L4",
                        target="all",
                        language_code="all",
                        claim_type="cross_language",
                        claim_text="Single language generation",
                        verified=False,
                        status="not_applicable",
                        verification_source="not_executed",
                        detail="Single language generated; cross-language parity is not applicable",
                    )
                ],
            )

        review = self._reviewer.review(documents)
        checks: list[VerificationCheck] = []

        # Check critical deltas (commands & config keys)
        for delta in review.fact_deltas:
            is_critical = delta.severity == "critical"
            checks.append(
                VerificationCheck(
                    layer="L4",
                    target=f"{delta.fact_type}:{delta.value}",
                    language_code=",".join(delta.missing_from),
                    claim_type="cross_language",
                    claim_text=f"{delta.fact_type} '{delta.value}' missing from {delta.missing_from}",
                    verified=not is_critical,
                    status="failed" if is_critical else "warning",
                    verification_source="cross_language_analyzer",
                    detail=f"Present in {delta.present_in} but missing from {delta.missing_from}",
                    suggested_fix=f"Add missing {delta.fact_type} to {', '.join(delta.missing_from)}",
                )
            )

        if not checks:
            # No parity deltas or comparisons were produced. Emit an honest
            # pending check so the layer reports pending, never a vacuous pass.
            checks.append(
                VerificationCheck(
                    layer="L4",
                    target="all",
                    language_code="all",
                    claim_type="cross_language",
                    claim_text="Cross-language parity",
                    verified=False,
                    status="pending",
                    verification_source="not_executed",
                    detail="No L4 parity checks were performed; layer is pending LLM judgment",
                )
            )

        return LayerReport(
            layer="L4",
            name="Cross-Language",
            checks=checks,
        )
