# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pre-publication gate's shape, checked statically (feature 017, FR-070–FR-075, SC-013).

The gate's green *run* happens after hand-off, on the post-merge ``feat/xml-refactor`` head
(``specs/017-release-line-reconciliation/evidence/ci-gate.md``). What this file pins is that the
workflow it runs is the one ``contracts/ci-workflow.md`` describes: the triggers and the
``siblings_ref`` input, the job graph, the bookworm container, the one informational job, the
blocking set that can fail ``gate-summary``, and the ``main``-push-only deploy and upload.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

#: Q11: 3.11 and the bookworm package build block; 3.12/3.13 inform.
BLOCKING = {"lint", "unit", "integration", "packaging", "coverage"}
INFORMATIONAL = {"matrix-info"}
NEEDS = {
    "lint": set(),
    "unit": {"lint"},
    "integration": {"lint"},
    "packaging": {"lint"},
    "coverage": {"unit", "integration"},
    "matrix-info": {"lint"},
    "gate-summary": BLOCKING | INFORMATIONAL,
}
SIBLING_REPOS = {"cuems-common", "cuems-nodeconf", "cuems-power-bridge",
            "cuems-engine", "cuems-editor", "cuems-frontend"}
SIBLING_ACTION = "./cuems-utils/.github/actions/checkout-siblings"
MAIN_PUSH = "github.event_name == 'push' && github.ref == 'refs/heads/main'"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    """PyYAML reads the bare key ``on`` as the boolean ``True``."""
    return workflow.get("on", workflow.get(True)) or {}


def _needs(job: dict) -> set[str]:
    needs = job.get("needs", [])
    return {needs} if isinstance(needs, str) else set(needs)


def _condition(text: object) -> str:
    """An ``if:`` with any ``${{ }}`` wrapper and extra whitespace removed."""
    s = str(text).strip()
    if s.startswith("${{") and s.endswith("}}"):
        s = s[3:-2]
    return " ".join(s.split())


@pytest.fixture(scope="module")
def tests_yml() -> dict:
    return _load("tests.yml")


# --- 1. triggers ---------------------------------------------------------------------

def test_1_triggers_and_the_siblings_ref_input(tests_yml):
    on = _triggers(tests_yml)
    assert set(on) >= {"push", "pull_request", "workflow_dispatch"}, sorted(on)
    assert set(on["push"]["branches"]) == {"main", "feat/xml-refactor"}  # FR-072
    inputs = (on["workflow_dispatch"] or {}).get("inputs", {})
    assert "siblings_ref" in inputs, "no siblings_ref dispatch input (FR-071)"
    assert inputs["siblings_ref"].get("default") == "xml-refactor-merge-candidate"


# --- 2. the job set and the needs graph ----------------------------------------------

def test_2_the_job_set_and_needs_graph(tests_yml):
    jobs = tests_yml["jobs"]
    assert set(jobs) == set(NEEDS), sorted(jobs)
    graph = {name: _needs(job) for name, job in jobs.items()}
    assert graph == NEEDS


@pytest.mark.parametrize("job", ["unit", "integration", "packaging"])
def test_2_each_sibling_reading_job_checks_the_siblings_out_at_siblings_ref(tests_yml, job):
    """FR-071, where the tests that read siblings actually run.

    No ``tests/integration`` module reads a sibling: the ``reads_siblings`` tests are contract
    and packaging tests. So all three test jobs use the checkout action, at the dispatched ref,
    with this repository beside the siblings (``path: cuems-utils``) and its history.
    """
    steps = tests_yml["jobs"][job]["steps"]
    own = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert [s["with"].get("path") for s in own] == ["cuems-utils"], job
    assert own[0]["with"].get("fetch-depth") == 0, job
    action = [s for s in steps if s.get("uses") == SIBLING_ACTION]
    assert len(action) == 1, f"{job} does not use {SIBLING_ACTION}"
    assert "inputs.siblings_ref" in str(action[0]["with"]["ref"]), action[0]["with"]
    assert str(action[0]["with"]["ref"]).count("xml-refactor-merge-candidate") == 1  # push/PR default


def test_2_the_checkout_action_places_each_sibling_beside_this_repository():
    action = yaml.safe_load((WORKFLOWS.parent / "actions" / "checkout-siblings" / "action.yml")
                            .read_text(encoding="utf-8"))
    checkouts = [s["with"] for s in action["runs"]["steps"]
                 if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert {w["path"] for w in checkouts} == SIBLING_REPOS
    for with_ in checkouts:
        assert with_["repository"].startswith("stagesoft/"), with_
        assert with_["ref"] == "${{ inputs.ref }}", with_
        assert with_["fetch-depth"] == 0, with_  # the tests resolve tags and read branches


def test_2_the_summary_counts_the_reads_siblings_marker():
    """The marker reaches the JUnit XML only as a test property (``tests/conftest.py``)."""
    script = (WORKFLOWS.parent / "scripts" / "gate_summary.py").read_text(encoding="utf-8")
    conftest = (WORKFLOWS.parents[1] / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert '"reads_siblings"' in script
    assert 'user_properties.append(("reads_siblings", "true"))' in conftest


# --- 3. the package build runs on bookworm --------------------------------------------

def test_3_packaging_runs_in_debian_bookworm(tests_yml):
    container = tests_yml["jobs"]["packaging"].get("container")
    image = container.get("image") if isinstance(container, dict) else container
    assert image == "debian:bookworm", container


# --- 4. only matrix-info is informational ---------------------------------------------

def test_4_only_matrix_info_continues_on_error(tests_yml):
    lenient = {name for name, job in tests_yml["jobs"].items() if job.get("continue-on-error")}
    assert lenient == INFORMATIONAL, sorted(lenient)
    versions = tests_yml["jobs"]["matrix-info"]["strategy"]["matrix"]["python"]
    assert {str(v) for v in versions} == {"3.12", "3.13"}


# --- 5. exactly the blocking set can fail gate-summary --------------------------------

def test_5_gate_summary_fails_on_exactly_the_blocking_set(tests_yml):
    job = tests_yml["jobs"]["gate-summary"]
    assert "always()" in _condition(job.get("if", "")), "gate-summary must run if: always()"
    failing = [s for s in job["steps"] if "exit 1" in str(s.get("run", ""))]
    assert len(failing) == 1, "exactly one step may fail gate-summary"
    named = set(re.findall(r"needs\.([\w-]+)\.result", _condition(failing[0].get("if", ""))))
    assert named == BLOCKING, sorted(named)


# --- 6. deploy and upload only from a push to main ------------------------------------

def _steps(workflow: dict):
    for job in workflow["jobs"].values():
        yield from job.get("steps", [])


def test_6_codecov_and_the_site_deploy_only_on_a_push_to_main(tests_yml):
    codecov = [s for s in _steps(tests_yml) if str(s.get("uses", "")).startswith("codecov/")]
    deploy = [s for s in _steps(_load("gh-pages.yml")) if "gh-deploy" in str(s.get("run", ""))]
    assert codecov, "no Codecov step"
    assert deploy, "no gh-deploy step"
    unguarded = [s.get("name", s.get("uses", s.get("run"))) for s in codecov + deploy
                 if _condition(s.get("if", "")) != MAIN_PUSH]
    assert not unguarded, f"not conditioned on {MAIN_PUSH!r}: {unguarded}"
