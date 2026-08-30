"""L3 Behavior Verifier: Trace command handlers, exit codes, and error conditions.

Python must collect behavior *evidence*, never adjudicate semantics. A documented
exit code is only ``passed`` when a real call site in the repository actually
returns that code (``sys.exit(N)`` / ``SystemExit(N)`` / ``raise SystemExit(N)``);
otherwise Python cannot prove the behavior and the check stays ``pending`` for
the LLM Auditor. Error-symptom text is likewise only ``passed`` when it matches a
known source handler; unmatched symptoms stay ``pending``.
"""

from __future__ import annotations

import re
from pathlib import Path

from makewiki_skills.model.document_artifact import DocumentArtifact
from makewiki_skills.toolkit.error_extractor import ErrorStringExtractor
from makewiki_skills.verification.report import LayerReport, VerificationCheck

# Common process exit codes are NOT auto-passed: their semantic meaning (does the
# tool really terminate with this code in this situation?) is LLM-judged, since
# Python cannot trace the behavior that produces them without a call site.
_COMMON_EXIT_CODES = frozenset({0, 1, 2, 127, 130})


def _stable_slug(text: str) -> str:
    """Deterministic whitespace-collapsed identity slug for a semantic item.

    Collapses all runs of whitespace (including newlines) to a single space so
    the same underlying claim always yields the same ``review_item_id`` across
    re-runs.
    """
    return " ".join(text.split())


class L3BehaviorVerifier:
    """Validate documented exit codes, error conditions, and handlers against source code."""

    def __init__(self, project_dir: Path) -> None:
        self._root = Path(project_dir).resolve()
        self._error_extractor = ErrorStringExtractor()
        self._error_messages: set[str] | None = None

    def verify_documents(
        self,
        documents: dict[str, list[DocumentArtifact]],
    ) -> LayerReport:
        known_errors = self._get_known_error_messages()
        checks: list[VerificationCheck] = []

        for lang, docs in documents.items():
            for doc in docs:
                # Look for documented error messages or troubleshooting symptoms
                lines = doc.content.splitlines()
                for i, line in enumerate(lines, 1):
                    # Check documented exit codes
                    exit_match = re.search(r"exit\s+code\s+(\d+)", line, re.IGNORECASE)
                    if exit_match:
                        code = int(exit_match.group(1))
                        checks.append(self._exit_code_check(doc, lang, line, code))

                    # Check documented error quotes or symptoms
                    quote_match = re.search(r"[`\"']([^`\"']{5,})[`\"']", line)
                    if quote_match and any(
                        kw in line.lower() for kw in ("error", "exception", "failed", "symptom", "cannot", "invalid", "troubleshoot")
                    ):
                        err_text = quote_match.group(1).strip()
                        # Check if any known project error contains parts of this text
                        matched = any(
                            err_text.lower() in ke.lower() or ke.lower() in err_text.lower()
                            for ke in known_errors
                        )
                        dest = "ast_declaration" if matched else "heuristic"
                        detail = (
                            "Documented error symptom verified against source handlers"
                            if matched
                            else "Documented error symptom not found in source; asserted without mechanical proof"
                        )
                        checks.append(
                            VerificationCheck(
                                layer="L3",
                                target=doc.filename,
                                language_code=lang,
                                claim_type="behavior",
                                claim_text=err_text[:60],
                                verified=matched,
                                status="passed" if matched else "pending",
                                verification_source=dest,
                                detail=detail,
                                review_item_id=(
                                    f"L3:{doc.filename}:{_stable_slug(err_text[:60])}"
                                ),
                            )
                        )

        if not checks:
            # No L3 checks were performed (e.g. no error/exit-code content in any
            # document). Emit an honest pending check rather than a vacuous pass,
            # so the layer is reported as pending LLM judgment - never "passed".
            checks.append(
                VerificationCheck(
                    layer="L3",
                    target="all",
                    language_code="all",
                    claim_type="behavior",
                    claim_text="No behavioral claims to verify",
                    verified=False,
                    status="pending",
                    verification_source="not_executed",
                    detail="No L3 checks were performed; layer is pending LLM judgment",
                    review_item_id="L3:all:no-behavioral-claims",
                )
            )

        return LayerReport(
            layer="L3",
            name="Behavior",
            checks=checks,
        )

    def _exit_code_check(
        self,
        doc: DocumentArtifact,
        lang: str,
        line: str,
        code: int,
    ) -> VerificationCheck:
        """Build a check for a documented exit code, honoring evidence only.

        Python never auto-passes a common exit code: a documented ``exit code N``
        is only ``passed`` when a real call site returning exactly ``N`` is traced
        in the repository. Otherwise it stays ``pending`` for LLM review.
        """
        if self._find_exit_code_evidence(code):
            return VerificationCheck(
                layer="L3",
                target=doc.filename,
                language_code=lang,
                claim_type="behavior",
                claim_text=f"Exit code {code}",
                verified=True,
                status="passed",
                verification_source="verified_from_repository",
                detail=f"Documented exit code {code} traced to a real call site in repository source",
                review_item_id=f"L3:{doc.filename}:exitcode-{code}",
            )
        return VerificationCheck(
            layer="L3",
            target=doc.filename,
            language_code=lang,
            claim_type="behavior",
            claim_text=f"Exit code {code}",
            verified=False,
            status="pending",
            verification_source="heuristic",
            detail=f"Behavior for exit code {code} not traced in source; pending LLM Auditor review",
            review_item_id=f"L3:{doc.filename}:exitcode-{code}",
        )

    def _find_exit_code_evidence(self, code: int) -> bool:
        """Return True only if the repository really returns ``code``.

        Greps ``.py`` files for ``sys.exit(code)`` / ``SystemExit(code)`` /
        ``raise SystemExit(code)`` at the exact integer. Merely documenting a
        common exit code is never enough.
        """
        if self._root is None or not self._root.is_dir():
            return False
        patterns = (
            rf"sys\.exit\(\s*{code}\s*\)",
            rf"raise\s+SystemExit\(\s*{code}\s*\)",
            rf"\bSystemExit\(\s*{code}\s*\)",
        )
        for py_file in self._root.rglob("*.py"):
            rel = str(py_file.relative_to(self._root)).replace("\\", "/")
            if any(part in rel for part in (".venv", "venv", "__pycache__", "node_modules", "site-packages")):
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat in patterns:
                if re.search(pat, text):
                    return True
        return False

    def _get_known_error_messages(self) -> set[str]:
        if self._error_messages is not None:
            return self._error_messages

        messages: set[str] = set()
        for py_file in self._root.rglob("*.py"):
            rel = str(py_file.relative_to(self._root)).replace("\\", "/")
            if any(part in rel for part in (".venv", "venv", "__pycache__", "node_modules")):
                continue
            facts = self._error_extractor.extract_from_file(py_file)
            for f in facts:
                messages.add(f.message)

        self._error_messages = messages
        return messages
