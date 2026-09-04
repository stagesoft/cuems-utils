"""T008 / FR-PERF-001 — the public path costs what the internal path costs.

Feature 010, US3. This file originally asserted that asking for one schema built
**one** schema, on research R8's premise that the internal descriptor path was
lazy per schema and that a public accessor building all six would therefore be a
regression.

**That premise was wrong, and the correction is recorded rather than quietly
dropped.** ``descriptor._class_type_keys`` and ``descriptor._repairability_map``
are documented global joins over every schema — 008 built them that way because
the repairability fact *is* global: a rule targets a model class name, and the
join between rule names and XSD type names spans all six schemas. So the
internal path builds six too. Measured 2026-09-04, one fresh process per path:

    internal SchemaDescriptor().types("script")   309.6 ms, 6 schemas built
    public   get_schema_descriptor(SCRIPT)        319.0 ms, 6 schemas built

FR-027 forbids changing what the descriptor computes, so making it lazy would be
a redesign of 008's repairability computation, not a fix to this feature's
accessor. What FR-PERF-001 actually requires — and what is worth asserting — is
that **publishing costs nothing measurable**: the public path within 110% of the
internal one for the same schema.

Each measurement runs in a **fresh subprocess**. An in-process comparison is
confounded: ``_repairability_cache`` is a module-level global that
``get_schema.cache_clear()`` does not reset, so whichever path ran second
measured a warm cache and looked ~4x faster than it is.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from cuemsutils.xml.schema import SCHEMA_NAMES

#: Measure **every** schema for one path, in ONE fresh interpreter.
#:
#: One subprocess per path, not one per (path, schema). The parametrised version
#: spawned 12, each paying ~300 ms to import the library, and pushed the whole
#: suite from 20.7 to 23.3 ms/test — through FR-PERF-001's own 22.80 cap. A
#: performance test that breaks the performance budget is not a good trade, and
#: the freshness it needs is per *process*, not per *case*.
_PROBE = """
import sys, time, json
sys.path.insert(0, "src")
which = sys.argv[1]

# BOTH modules are imported before any clock starts, in both probes. Import cost
# is not the operation's cost, and the public path pulls a heavier module tree
# (ConfigManager imports the config classes as well as the descriptor) — timing
# it would charge this accessor for an import the caller pays once per process
# and would have paid anyway.
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema
from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

manager = ConfigManager(load_all=False)
timings = {}
for name in SCHEMA_NAMES:
    start = time.perf_counter()
    if which == "internal":
        SchemaDescriptor().types(name)
    else:
        manager.get_schema_descriptor(SchemaName(name))
    timings[name] = (time.perf_counter() - start) * 1000
print(json.dumps({"timings": timings, "schemas_built": get_schema.cache_info().currsize}))
"""


def _measure(which: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE, which],
        capture_output=True, text=True, cwd=".",
    )
    assert result.returncode == 0, result.stderr[-400:]
    return json.loads(result.stdout.strip())


@pytest.fixture(scope="module")
def measurements() -> dict:
    """Two subprocesses for the whole module, not two per schema."""
    return {which: _measure(which) for which in ("internal", "public")}


#: Below this, a 110% cap is microseconds and measures scheduler noise, not
#: design. Measured 2026-09-04: the **first** schema touched pays the whole
#: ~120 ms global join (008's repairability map spans all six), and every
#: subsequent one costs 0.08–1.0 ms. So the per-schema ratio is meaningful for
#: the schemas that do real work and meaningless for the rest, and the total is
#: what covers them.
_MEANINGFUL_MS = 1.0


def test_the_public_path_costs_what_the_internal_path_costs(measurements):
    """FR-PERF-001 — within 110% overall, measured not assumed.

    Asserted on the **total** across all six schemas, which is the robust
    number: ~121 ms against ~121 ms. An earlier version asserted per schema and
    was flaky in a loaded suite, because five of the six measurements are
    sub-millisecond and a 10% band on 0.08 ms is noise.
    """
    internal = sum(measurements["internal"]["timings"].values())
    public = sum(measurements["public"]["timings"].values())

    assert public <= internal * 1.10, (
        f"public {public:.1f} ms against internal {internal:.1f} ms "
        f"= {public / internal:.2f}x, over the 1.10 cap"
    )


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_no_individual_schema_regresses_where_it_is_measurable(schema_name, measurements):
    """The per-schema check, applied only where there is signal to check."""
    internal = measurements["internal"]["timings"][schema_name]
    public = measurements["public"]["timings"][schema_name]

    if internal < _MEANINGFUL_MS:
        pytest.skip(
            f"{schema_name} costs {internal:.3f} ms; below the noise floor, "
            "covered by the total instead"
        )
    assert public <= internal * 1.10, (
        f"{schema_name}: public {public:.3f} ms against internal {internal:.3f} ms "
        f"= {public / internal:.2f}x"
    )


def test_the_public_path_adds_no_schema_builds(measurements):
    """The part of R8's concern that survives its premise.

    Publishing must not make the descriptor *more* eager than it already is.
    Both paths build all six; what matters is that the public one adds none.
    """
    assert (
        measurements["public"]["schemas_built"]
        == measurements["internal"]["schemas_built"]
    ), {k: v["schemas_built"] for k, v in measurements.items()}
