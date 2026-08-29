"""Contract tests asserting architectural invariants across planes.

These tests are part of the ``contracts`` pytest collection. They cover the
end-to-end contract between the documentation Skill (LLM plane), the Python
toolkit (mechanical plane), and the public surface (``config.yaml`` /
``SKILL.md`` / CLI / output). Each test is intentionally fast, deterministic,
and free of external network access.
"""
