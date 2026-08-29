"""L2 Interface Verifier: Validate CLI parameter flags, choices, defaults, and types."""

from __future__ import annotations

import ast
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.toolkit.markdown_tools import MarkdownTool
from makewiki_skills.verification.report import LayerReport, VerificationCheck


@dataclass
class CLIParameterSpec:
    """Declared CLI parameter specification extracted from source."""

    param_name: str
    flags: list[str] = field(default_factory=list)  # e.g. ["--format", "-f"]
    is_option: bool = True
    param_type: str = "str"
    default_value: Any = None
    required: bool = False
    choices: list[str] = field(default_factory=list)
    help_text: str | None = None
    source_file: str | None = None
    line_number: int = 1


@dataclass
class CLICommandSpec:
    """Declared CLI command interface extracted from source."""

    command_name: str  # e.g. "scan" or "generate" or "makewiki scan"
    parameters: list[CLIParameterSpec] = field(default_factory=list)
    source_file: str | None = None
    line_number: int = 1

    def find_param_by_flag(self, flag: str) -> CLIParameterSpec | None:
        for p in self.parameters:
            if flag in p.flags or flag == p.param_name or flag.lstrip("-") == p.param_name.replace("_", "-"):
                return p
        return None


class L2InterfaceVerifier:
    """Inspect CLI argument names, flags, defaults, and choices against AST / source definitions."""

    def __init__(self, project_dir: Path) -> None:
        self._root = Path(project_dir).resolve()
        self._md = MarkdownTool()
        self._command_specs: dict[str, CLICommandSpec] | None = None

    def verify_documents(
        self,
        documents: dict[str, list[GeneratedDocument]],
    ) -> LayerReport:
        specs = self._get_all_command_specs()
        checks: list[VerificationCheck] = []

        for lang, docs in documents.items():
            for doc in docs:
                facts = self._md.extract_facts(doc.content, lang, doc.filename)
                for cmd_str in facts.commands:
                    cmd_checks = self._verify_command_invocation(doc, cmd_str, specs)
                    checks.extend(cmd_checks)

        return LayerReport(
            layer="L2",
            name="Interface",
            checks=checks,
        )

    def _verify_command_invocation(
        self,
        doc: GeneratedDocument,
        cmd_str: str,
        specs: dict[str, CLICommandSpec],
    ) -> list[VerificationCheck]:
        stripped = cmd_str.strip()
        if not stripped:
            return []

        # Parse command tokens safely
        try:
            tokens = shlex.split(stripped)
        except ValueError:
            tokens = stripped.split()

        if not tokens:
            return []

        # Find matching command spec in project
        matched_spec: CLICommandSpec | None = None
        for name, spec in specs.items():
            # Match subcommand (e.g. "scan" or "makewiki scan")
            name_parts = name.split()
            if len(name_parts) == 1 and name_parts[0] in tokens:
                matched_spec = spec
                break
            elif len(name_parts) > 1 and all(p in tokens for p in name_parts):
                matched_spec = spec
                break

        if not matched_spec:
            # If no AST spec found (e.g. Makefile target or shell command), return generic L2 check
            return []

        results: list[VerificationCheck] = []
        parsed_flags = self._extract_flags_from_tokens(tokens)

        for flag, val in parsed_flags:
            param = matched_spec.find_param_by_flag(flag)
            if param is None:
                results.append(
                    VerificationCheck(
                        layer="L2",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="interface",
                        claim_text=f"{stripped} -> {flag}",
                        verified=False,
                        status="failed",
                        verification_source="ast_declaration",
                        detail=f"Flag '{flag}' is not declared in command '{matched_spec.command_name}' specification",
                        suggested_fix=f"Check declared options in {param.source_file if param else 'CLI definition'}",
                    )
                )
            else:
                # 1. Check choice validity if parameter restricts choices
                if param.choices and val is not None:
                    clean_val = val.strip("\"'")
                    if clean_val not in param.choices:
                        results.append(
                            VerificationCheck(
                                layer="L2",
                                target=doc.filename,
                                language_code=doc.language_code,
                                claim_type="interface",
                                claim_text=f"{flag}={val}",
                                verified=False,
                                status="failed",
                                verification_source="ast_declaration",
                                detail=(
                                    f"Value '{clean_val}' for '{flag}' is invalid. "
                                    f"Allowed choices: {', '.join(param.choices)}"
                                ),
                                suggested_fix=f"Use one of allowed choices: {', '.join(param.choices)}",
                            )
                        )
                        continue

                results.append(
                    VerificationCheck(
                        layer="L2",
                        target=doc.filename,
                        language_code=doc.language_code,
                        claim_type="interface",
                        claim_text=f"{flag}={val}" if val else flag,
                        verified=True,
                        status="passed",
                        verification_source="ast_declaration",
                        detail=f"Flag '{flag}' verified against declared parameter '{param.param_name}'",
                    )
                )

        return results

    def _extract_flags_from_tokens(self, tokens: list[str]) -> list[tuple[str, str | None]]:
        flags: list[tuple[str, str | None]] = []
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t.startswith("-"):
                if "=" in t:
                    flag_name, val = t.split("=", 1)
                    flags.append((flag_name, val))
                else:
                    if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                        flags.append((t, tokens[i + 1]))
                        i += 1
                    else:
                        flags.append((t, None))
            i += 1
        return flags

    def _get_all_command_specs(self) -> dict[str, CLICommandSpec]:
        if self._command_specs is not None:
            return self._command_specs

        specs: dict[str, CLICommandSpec] = {}

        for py_file in self._root.rglob("*.py"):
            rel = str(py_file.relative_to(self._root)).replace("\\", "/")
            if any(part in rel for part in (".venv", "venv", "site-packages", "__pycache__", "node_modules")):
                continue

            extracted = self._extract_python_cli_specs(py_file)
            for spec in extracted:
                specs[spec.command_name] = spec

        self._command_specs = specs
        return specs

    def _extract_python_cli_specs(self, path: Path) -> list[CLICommandSpec]:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content, filename=str(path))
        except (OSError, SyntaxError):
            return []

        specs: list[CLICommandSpec] = []
        rel_path = str(path.relative_to(self._root)).replace("\\", "/")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for @app.command() decorator (Typer / Click)
                is_command = False
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec) if hasattr(ast, "unparse") else ""
                    if "command" in dec_str or "click." in dec_str:
                        is_command = True
                        break

                if is_command or "cli" in rel_path.lower():
                    cmd_spec = CLICommandSpec(
                        command_name=node.name,
                        source_file=rel_path,
                        line_number=node.lineno,
                    )

                    # Extract parameter specs from function arguments
                    for arg in node.args.args:
                        p_name = arg.arg
                        if p_name in ("self", "cls"):
                            continue

                        # Inspect default value or typer.Option / typer.Argument
                        flags = [f"--{p_name.replace('_', '-')}"]
                        choices: list[str] = []
                        param_type = "str"

                        # Try to extract typer.Option / Argument arguments
                        for default_node in node.args.defaults:
                            def_str = ast.unparse(default_node) if hasattr(ast, "unparse") else ""
                            if "typer.Option" in def_str or "click.option" in def_str or "typer.Argument" in def_str:
                                # Extract explicit flag names from call args
                                for flag_match in re.finditer(r"[\"'](--[a-zA-Z0-9_\-]+|-{1}[a-zA-Z0-9])[\"']", def_str):
                                    flag = flag_match.group(1)
                                    if flag not in flags:
                                        flags.append(flag)

                                # Extract choices from default or help
                                choice_match = re.search(r"(?:format|choice|theme):\s*([a-zA-Z0-9_\-\s|]+)", def_str, re.IGNORECASE)
                                if choice_match:
                                    choices = [c.strip() for c in choice_match.group(1).split("|") if c.strip()]

                        cmd_spec.parameters.append(
                            CLIParameterSpec(
                                param_name=p_name,
                                flags=flags,
                                choices=choices,
                                source_file=rel_path,
                                line_number=node.lineno,
                            )
                        )

                    specs.append(cmd_spec)

        return specs
