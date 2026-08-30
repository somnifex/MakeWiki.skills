"""L0 Syntax & Structure Verifier: Markdown AST, heading hierarchy, and link validity."""

from __future__ import annotations

from pathlib import Path

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.toolkit.markdown_tools import MarkdownTool
from makewiki_skills.verification.report import LayerReport, VerificationCheck


class L0SyntaxVerifier:
    """Validate L0 Markdown syntax, heading hierarchy, and internal links."""

    def __init__(self) -> None:
        self._md = MarkdownTool()

    def verify_documents(
        self,
        documents: dict[str, list[DocumentArtifact]],
        base_dir: Path | None = None,
    ) -> LayerReport:
        checks: list[VerificationCheck] = []

        for lang, doc_list in documents.items():
            for doc in doc_list:
                doc_path = (base_dir / doc.filename) if base_dir else Path(doc.filename)

                # 1. Check empty page
                content_stripped = doc.content.strip()
                body_without_headings = "\n".join(
                    line for line in content_stripped.splitlines() if not line.strip().startswith("#")
                ).strip()

                if not content_stripped or not body_without_headings:
                    checks.append(
                        VerificationCheck(
                            layer="L0",
                            target=doc.filename,
                            language_code=lang,
                            claim_type="structure",
                            claim_text="Document has meaningful content",
                            verified=False,
                            status="failed",
                            verification_source="markdown_linter",
                            detail="Document is empty or has only heading",
                            suggested_fix="Generate detailed content for this document",
                        )
                    )
                else:
                    checks.append(
                        VerificationCheck(
                            layer="L0",
                            target=doc.filename,
                            language_code=lang,
                            claim_type="structure",
                            claim_text="Document non-empty",
                            verified=True,
                            status="passed",
                            verification_source="markdown_linter",
                            detail="Document contains substantial content",
                        )
                    )

                # 2. Check heading hierarchy & single H1
                heading_res = self._md.validate_headings(doc.content)
                if not heading_res.success or not heading_res.data.get("valid", True):
                    for issue in heading_res.data.get("issues", []):
                        severity = issue.get("severity", "warning")
                        checks.append(
                            VerificationCheck(
                                layer="L0",
                                target=doc.filename,
                                language_code=lang,
                                claim_type="structure",
                                claim_text=f"Heading on line {issue.get('line', 1)}",
                                verified=severity != "error",
                                status="failed" if severity == "error" else "warning",
                                verification_source="markdown_linter",
                                detail=issue.get("message", "Heading hierarchy error"),
                                suggested_fix="Ensure document has exactly one H1 and sequential heading levels",
                            )
                        )
                else:
                    checks.append(
                        VerificationCheck(
                            layer="L0",
                            target=doc.filename,
                            language_code=lang,
                            claim_type="structure",
                            claim_text="Heading hierarchy",
                            verified=True,
                            status="passed",
                            verification_source="markdown_linter",
                            detail="Single H1 heading and valid hierarchy",
                        )
                    )

                # 3. Check internal links if base_dir exists
                if base_dir and base_dir.is_dir():
                    link_res = self._md.validate_links(doc.content, doc_path)
                    if not link_res.data.get("valid", True):
                        for issue in link_res.data.get("issues", []):
                            checks.append(
                                VerificationCheck(
                                    layer="L0",
                                    target=doc.filename,
                                    language_code=lang,
                                    claim_type="structure",
                                    claim_text=f"Link on line {issue.get('line', 1)}",
                                    verified=False,
                                    status="failed",
                                    verification_source="markdown_linter",
                                    detail=issue.get("message", "Broken relative link"),
                                    suggested_fix="Fix target path for relative link",
                                )
                            )

        return LayerReport(
            layer="L0",
            name="Syntax & Structure",
            checks=checks,
        )
