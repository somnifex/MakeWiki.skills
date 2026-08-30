"""Deterministic, host-agnostic evaluation harness for MakeWiki.

The eval harness lives on the Mechanical Plane. It NEVER judges whether prose
is good, whether a troubleshooting section is plausible, or whether a claim
sounds natural — those are LLM Eval-Judge responsibilities. What this package
provides is the *protocol* that lets any host (or a fake-LLM fixture) drive the
authoritative ``/makewiki`` flow and mechanically score the resulting run
artifacts:

* ``artifact`` — the stable run-artifact contract every eval run writes.
* ``scorer``  — deterministic mechanical scoring over structured fields
  (claim IDs, semantic keys, gate state), with no semantic heuristics.
* ``aggregate`` — N >= 3 aggregation across repeated runs of one trap.
* ``judge``   — the LLM rubric-judge protocol (schema + input loading only;
  the semantic judgment itself is produced by an independent LLM, never by
  this code).
* ``runner``  — the prepare / score / aggregate orchestration, including a
  ``--fixture`` driver that replays a pre-recorded fake-LLM handoff so the
  mechanical harness is fully executable in a host-less CI run.

Execution model (§4 of the final contract): the host runs ``/makewiki`` and
writes run artifacts; Python reads them and does deterministic scoring. This
module does NOT hard-code any model provider, and it does NOT call an LLM.
"""
