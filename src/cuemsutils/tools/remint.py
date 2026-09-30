# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The cluster-wide re-mint (feature 012, US2) — ``cuems-init-node --remint``.

A **stop-the-world operation on a live installation**: services stopped, no
shows running. It replaces every node identity by literal 36-character token
substitution, from a substitution table built once on the controller and
persisted before the first write.

Its own module rather than more of ``init_node.py``, because a cluster-wide
operation is not the per-node tool's job and that module is already large
(Principle I). ``init_node`` parses the flags and calls in here.

## Why literal substitution, and not a structural rewrite

The identities are not only in ``<uuid>`` elements. Every video output in every
show script carries ``<identity>_<output>`` — the compound form — inside an
``<output_name>`` that is a ``NameStringType`` and stays one (data-model
§1.1a, research R12). A structural rewrite would update the mappings, leave
every script's output prefix stale, and leave it **schema-valid**, so nothing
would report it and an output would resolve to nothing at show time.

## The two reaches have different scopes (FR-011a)

===================================  ===========================  ===================
Reach                                Rewritten by                 Reaches others by
===================================  ===========================  ===================
the configuration documents          **each node, itself**, from  not at all — each
                                     the distributed table        node's are its own
the project library                  **the controller, once**     the project
                                                                  deployer's existing
                                                                  replication
===================================  ===========================  ===================

A node that is not the controller and has no table **refuses** rather than
minting one: a locally minted table is exactly the divergence the design exists
to prevent. But a table whose ``controller`` is *another* node is the **normal**
case on every node but one — that is what distribution means. The refusal is on
*minting* without authority, never on *using* a table another node built
(contracts/cli-remint.md, "Not a refusal").

## Never restore a modification time

The substitution replaces 36 characters with 36, so every rewritten file is
**exactly the size it was**. The library reaches the nodes by ``rsync -rt``
with no checksum (research R11), so size and time are all it compares, and the
time is the only signal it has. ``os.replace`` gives a fresh one; the trap is
"helpfully" adding ``shutil.copystat`` (FR-011b).

## Everything before the verify step reads with stdlib XML only

Not a technique but a requirement (FR-006a). After the narrowing, every
document this tool exists to repair is one the schema refuses — and the
collision abort must read a map that the new uniqueness rule refuses *at read
time* in order to name the two rows at all. The verify step is the one place
validation is wanted, and it runs only after the rewrite has made validation
possible.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import ids, library_reach

__all__ = [
    "Abort",
    "CompletionRecord",
    "Refused",
    "SubstitutionTable",
    "Survey",
    "THROUGHPUT_FLOOR",
    "Verification",
    "apply_table",
    "build_table",
    "collisions",
    "completion_record_path",
    "estimate_seconds",
    "roll_call",
    "run",
    "survey",
    "table_path",
    "verify",
]

#: FR-PERF-001's **floor**, in bytes per second: the slowest this operation may
#: run before something is wrong.
#:
#: **Re-baselined 2026-09-30 from 500 MB/s to 140 MB/s.** 500 was a value
#: supplied by an analysis pass without measurement, and it was unreachable by
#: construction: a pass that reads every document of the ``remint_200`` fixture
#: and atomically rewrites it with **no substitution at all** measures ~290 MB/s
#: on the reference machine, because 400 documents of ~10 KB each are dominated
#: by per-file syscalls rather than by bytes moved. 140 MB/s is the slowest of
#: ten measured samples (154 MB/s) with 10% allowed for future degradation.
#: ``baseline.md`` §3 carries the samples.
#:
#: It is still the estimate's **fallback only** (:func:`estimate_seconds`) and
#: not its divisor in the normal case. The floor is a constant and the survey
#: measures *this* machine — a node on slower storage, or one under load, is
#: exactly the case where a constant is wrong and the measurement is right.
#: That the two now happen to agree on the reference machine is a property of
#: the reference machine, not an argument for dropping the measurement.
THROUGHPUT_FLOOR = 140 * 1_000_000

#: Below this the survey's own elapsed time is noise rather than a
#: measurement, and the estimate falls back to :data:`THROUGHPUT_FLOOR` — and
#: says that it did, so a pessimistic estimate is never presented as a measured
#: one.
MIN_TIMEABLE_SECONDS = 0.005

#: Where this tool keeps its state, under the directory ``cuems-init-node``
#: already owns.
STATE_SUBDIR = "remint"
TABLE_NAME = "substitution-table.json"

CONFIGURATION, LIBRARY, BOTH = "configuration", "library", "both"


class Abort(Exception):
    """Stopped before anything was written, and deliberately (exit 1).

    Distinct from :class:`Refused` only in what it says: an abort is the
    *cluster's* state refusing the operation (a collision), a refusal is the
    *invocation* being wrong (no table on a plain node).
    """


class Refused(Exception):
    """The invocation is not one this tool will perform (exit 1)."""


# -- the substitution table (data-model §2) --------------------------------------------


def table_path(state_dir) -> Path:
    return Path(state_dir) / STATE_SUBDIR / TABLE_NAME


@dataclass
class SubstitutionTable:
    """The only record linking an old identity to its new one.

    Persisted **before** the first write (FR-007); its loss strands a partly
    rewritten cluster. It travels between nodes because the operator copies it
    — this feature adds no transport (data-model §2.2a), and a node invoked
    without it refuses **by design**.
    """

    #: When the table was minted, ISO 8601, UTC.
    created: str

    #: The identity of the node that built it, as that node carried it at build
    #: time. The table is built **once, centrally** (FR-019c).
    controller: str

    #: ``old -> new``, one entry per **distinct** non-converged old identity.
    entries: dict[str, str] = field(default_factory=dict)

    #: Every file already rewritten, appended as each ``os.replace`` lands.
    #: This is what makes the operation resumable (FR-008).
    applied: list[str] = field(default_factory=list)

    #: Which reach this run performed — the controller does both, a plain node
    #: only its own configuration (FR-011a).
    scope: str = BOTH

    def digest(self) -> str:
        """A stable digest of the mapping, for the completion record.

        Over ``entries`` alone: ``applied`` grows as the run proceeds, so a
        digest including it would name a different table at every step, and the
        question the record answers is *which mapping was applied*.
        """
        payload = json.dumps(self.entries, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()

    def check_invariants(self) -> None:
        """The five invariants of data-model §2.1, checked rather than trusted.

        Raises:
            Abort: any of them broken. A minted collision is vanishingly
                improbable, but the failure would be silent and permanent, so
                it is checked anyway.
        """
        for old, new in self.entries.items():
            if not ids.is_converged(new):
                raise Abort(f"table entry {old} -> {new} is not a converged uuid4")
        new_values = list(self.entries.values())
        if len(set(new_values)) != len(new_values):
            raise Abort("the table mints one value twice; refusing (data-model §2.1 invariant 2)")
        # Invariant 4 is checked **before** invariant 3, and the order is the
        # whole content of the distinction. An ``old == new`` entry is also a
        # chained one — its new value trivially appears as an old one — so the
        # chaining check would always fire first and report the general fault
        # for the specific one. "Mapping to itself" names what actually went
        # wrong: a converged node was given an entry.
        same = [old for old, new in self.entries.items() if old == new]
        if same:
            raise Abort(f"the table records {sorted(same)} mapping to itself; a converged "
                        "node has no entry (data-model §2.1 invariant 4)")
        chained = set(new_values) & set(self.entries)
        if chained:
            raise Abort(
                f"the table would substitute {sorted(chained)} twice — a new value also "
                "appears as an old one (data-model §2.1 invariant 3)"
            )

    def save(self, path) -> None:
        """Write atomically. The table is the operation's only durable record,
        so a half-written one is worse than none."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=".table.", suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(asdict(self), out, indent=2, sort_keys=True)
        os.replace(temporary, str(path))

    @classmethod
    def load(cls, path) -> "SubstitutionTable":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            created=raw["created"],
            controller=raw["controller"],
            entries=dict(raw.get("entries", {})),
            applied=list(raw.get("applied", [])),
            scope=raw.get("scope", BOTH),
        )

    def substituter(self):
        """A **one-pass** substitution function over this table's entries.

        One compiled alternation, not one ``str.replace`` per entry, for two
        separate reasons. Correctness: sequential replaces can chain, so a new
        value that happened to be an old one would be rewritten twice — which
        :meth:`check_invariants` also forbids, belt and braces. Performance: a
        pass per entry is the per-node repeated pass SC-PERF-001 exists to
        catch, and it would make a ten-node run about five times a two-node one
        over identical bytes.
        """
        if not self.entries:
            return lambda text: text
        pattern = re.compile("|".join(re.escape(old) for old in sorted(self.entries)))
        table = self.entries
        return lambda text: pattern.sub(lambda m: table[m.group(0)], text)

    def byte_substituter(self):
        """:meth:`substituter`, over **bytes**.

        What :func:`apply_table` uses, for two reasons that point the same way.

        *Correctness*: the substitution is defined as replacing a 36-character
        ASCII token with another, and it must be **length-preserving in bytes**
        (FR-011b) because the replication compares size. Decoding a document to
        text and re-encoding it is a round trip that has nothing to do with the
        edit and can only lose — a document read with ``surrogateescape`` and
        written back is not guaranteed byte-identical outside the tokens, which
        is precisely what FR-009 promises.

        *Cost*: decode plus encode is measurably the second-largest item in the
        apply loop after the write itself (see ``baseline.md``). Skipping both
        is free.

        Every token is ASCII by construction — a uuid is hex and hyphens — so
        the byte pattern is the text pattern encoded, with no escaping subtlety.
        """
        if not self.entries:
            return lambda data: data
        pattern = re.compile(
            b"|".join(re.escape(old.encode("ascii")) for old in sorted(self.entries))
        )
        table = {old.encode("ascii"): new.encode("ascii")
                 for old, new in self.entries.items()}
        return lambda data: pattern.sub(lambda m: table[m.group(0)], data)


def build_table(identities, controller: str, scope: str = BOTH) -> SubstitutionTable:
    """One new uuid4 per **distinct non-converged** identity (FR-006, FR-014).

    Minted through :class:`cuemsutils.tools.Uuid.Uuid` — the only minter in the
    ecosystem, and one that refuses any shape but uuid4, so the table cannot
    contain a value the tightened pattern will reject.

    An already-converged identity gets **no entry**, which is what makes
    FR-014's "a converged node is untouched" a property of the table rather
    than a special case in the apply loop.
    """
    from .Uuid import Uuid

    table = SubstitutionTable(
        created=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        controller=controller,
        scope=scope,
    )
    for old in sorted(set(identities)):
        if ids.classify(old) == ids.CONVERGED:
            continue
        table.entries[old] = str(Uuid())
    table.check_invariants()
    return table


# -- the survey (step 1) ---------------------------------------------------------------


@dataclass
class Survey:
    """What the survey found, and **how long it took to find it**.

    The elapsed time is not diagnostics: it is the estimate's divisor
    (FR-PERF-003). The survey already reads every byte the apply pass will
    read, so the measurement is free, and it is the only throughput figure
    that describes *this machine*.
    """

    documents: tuple[Path, ...]
    config_documents: tuple[Path, ...]
    library_documents: tuple[Path, ...]

    #: ``value -> classification`` over every identity token seen.
    identities: dict[str, str]

    #: Identities that are node identities according to the configuration —
    #: the keys a table may be built from (FR-010). Cue and media identifiers
    #: are deliberately excluded, which bounds where a replacement can land.
    node_identities: tuple[str, ...]

    bytes_read: int
    elapsed: float
    notes: tuple[str, ...] = ()

    @property
    def observed_throughput(self) -> float | None:
        """Bytes per second, or ``None`` when the run was too short to time."""
        if self.elapsed < MIN_TIMEABLE_SECONDS or not self.bytes_read:
            return None
        return self.bytes_read / self.elapsed

    @property
    def needs_migration(self) -> bool:
        return any(
            ids.classify(value) == ids.NOT_CONVERGED for value in self.node_identities
        )


def _node_identities(conf: Path) -> list[str]:
    """Every identity the configuration documents name as a **node** identity.

    Read with stdlib XML, leniently: a document that will not parse contributes
    nothing and stops nothing. The keys are taken from ``<uuid>`` elements
    only, never from a compound string, because FR-010 bounds the table to node
    identities and a compound value is an *occurrence* of one, not a source of
    one.
    """
    found: list[str] = []
    for name in ("settings.xml", "network_map.xml", "default_mappings.xml"):
        path = conf / name
        if not path.is_file():
            continue
        for occurrence in ids.scan_file(path):
            if not occurrence.embedded and occurrence.element == "uuid":
                found.append(occurrence.value)
    return found


def survey(conf, reach: library_reach.LibraryReach) -> Survey:
    """Classify every identity across the configuration and the library.

    Stdlib XML only, and never through the validating load path (FR-006a).
    Returns the byte volume **and its own elapsed time**, which together are
    the observed throughput the estimate divides by.
    """
    conf = Path(conf)
    started = time.perf_counter()

    config_documents = tuple(
        conf / name
        for name in ("settings.xml", "network_map.xml", "default_mappings.xml")
        if (conf / name).is_file()
    )
    library_documents = tuple(reach.documents)

    identities: dict[str, str] = {}
    notes: list[str] = list(filter(None, [reach.degraded]))
    bytes_read = 0
    for path in config_documents + library_documents:
        try:
            data = path.read_bytes()
        except OSError as exc:
            notes.append(f"{path}: unreadable ({exc}); not surveyed")
            continue
        bytes_read += len(data)
        # The **cheap** scan (``scan_values``), not ``scan_text``. The survey
        # needs to know which identities a document carries, not where each
        # occurrence sat — and this loop's elapsed time is the operator's
        # duration estimate, so work the survey does not need makes the estimate
        # pessimistic rather than merely slow (FR-PERF-003).
        for value in ids.scan_values(data):
            identities.setdefault(value, ids.classify(value))

    node_identities = tuple(sorted(set(_node_identities(conf))))
    elapsed = time.perf_counter() - started
    return Survey(
        documents=config_documents + library_documents,
        config_documents=config_documents,
        library_documents=library_documents,
        identities=identities,
        node_identities=node_identities,
        bytes_read=bytes_read,
        elapsed=elapsed,
        notes=tuple(notes),
    )


# -- the collision check (step 2) ------------------------------------------------------


@dataclass(frozen=True)
class Collision:
    """Two or more rows of the network map carrying one identity."""

    uuid: str
    macs: tuple[str, ...]


def collisions(map_path) -> list[Collision]:
    """Rows sharing an identity, read with **stdlib XML** (FR-006a).

    Stdlib rather than the validating reader, and this is the case that makes
    that a requirement rather than a preference: FR-019a refuses a colliding
    map *at read time*, so the validating path cannot supply the two rows the
    abort message has to name. The tool that reports the fault must be able to
    read the document that has it.
    """
    path = Path(map_path)
    if not path.is_file():
        return []
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return []
    by_uuid: dict[str, list[str]] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "node":
            continue
        uuid = (element.findtext("uuid") or "").strip()
        mac = (element.findtext("mac") or "").strip()
        if uuid:
            by_uuid.setdefault(uuid, []).append(mac or "<no mac>")
    return [
        Collision(uuid, tuple(macs))
        for uuid, macs in sorted(by_uuid.items())
        if len(macs) > 1
    ]


def collision_message(found: list[Collision], documents) -> str:
    """Names both rows **with their MACs** and every script referencing the token.

    The scripts are named because that is where the harm would be: the compound
    ``<identity>_<output>`` prefix is the only record of which node an output
    belongs to, and no discriminator exists there — so splitting a shared
    identity would silently reassign one node's entire output set (data-model
    §4.2). Resolving it is manual and comes first; the migration guide has the
    procedure (FR-036b).
    """
    lines = ["refusing: the network map carries rows that share an identity."]
    for collision in found:
        lines.append(f"  {collision.uuid} is carried by {len(collision.macs)} rows: "
                     + ", ".join(f"mac={mac}" for mac in collision.macs))
        referencing = [
            str(path) for path in documents
            if collision.uuid in _safe_read(path)
        ]
        for path in referencing:
            lines.append(f"    referenced by {path}")
    lines.append(
        "Nothing has been written. Splitting a shared identity is safe in the "
        "configuration documents, where the MAC discriminates, and unsafe in the "
        "library, where the compound <identity>_<output> prefix is the only record "
        "of which node an output belongs to. Resolve it by hand first — see the "
        "migration guide's pre-existing-collision procedure — while the map still loads."
    )
    return "\n".join(lines)


def _safe_read(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="surrogateescape")
    except OSError:
        return ""


# -- the apply loop (step 6) -----------------------------------------------------------


def apply_table(table: SubstitutionTable, documents, table_file=None) -> list[Path]:
    """Rewrite each document in place, atomically, recording as it goes.

    Per file: read, substitute every entry in **one pass**, write to a
    temporary, ``os.replace``, append the path to ``applied``. A file already
    in ``applied`` is skipped, which is what makes a re-run resumable and a
    converged cluster a no-op (FR-008, FR-013).

    ``table_file`` is where to persist ``applied`` after each replace. Passing
    it costs one small write per document and buys the property the whole
    design rests on: an interruption leaves a record of exactly what was done.

    **Modification times are never restored.** The substitution is
    length-preserving, so the time is the only thing that tells the replication
    a file changed (FR-011b, research R11).
    """
    substitute = table.byte_substituter()
    already = set(table.applied)
    rewritten: list[Path] = []
    for path in documents:
        path = Path(path)
        if str(path) in already:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if not data:
            continue
        new_data = substitute(data)
        if new_data == data:
            # Nothing of this node's is in this file. Not recorded as applied:
            # it was not, and a second run reaching the same conclusion costs a
            # read it would have done anyway.
            continue
        _atomic_write(path, new_data)
        table.applied.append(str(path))
        rewritten.append(path)
        if table_file is not None:
            table.save(table_file)
    return rewritten


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` through a temporary and an ``os.replace``.

    Hand-rolled rather than ``tempfile.mkstemp`` + ``os.fdopen`` + ``os.chmod``,
    and measured rather than assumed: the write is the apply loop's dominant
    cost (``baseline.md``), ``mkstemp`` creates at ``0600`` so a ``chmod`` is
    always needed after it, and its name generation is a retry loop this does
    not need. Opening once with the mode the target already has drops two
    syscalls per document.

    ``O_EXCL`` keeps the exclusivity ``mkstemp`` was there for. The name carries
    the pid, so two processes cannot collide on it — the operation is
    stop-the-world, but a temporary file that could be clobbered is not
    something to leave resting on that.

    **The modification time is deliberately not restored.** ``os.replace`` gives
    a fresh one, and that is the only signal the size-and-time replication has
    that the file changed (FR-011b, research R11). Adding ``shutil.copystat``
    here is the trap.
    """
    try:
        mode = path.stat().st_mode & 0o777
    except OSError:
        mode = 0o644
    temporary = f"{path}.remint-{os.getpid()}.tmp"
    try:
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            os.write(handle, data)
        finally:
            os.close(handle)
        os.replace(temporary, str(path))
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# -- the estimate (step 5) -------------------------------------------------------------


def estimate_seconds(survey_result: Survey) -> tuple[float, bool]:
    """``(predicted seconds, used_the_floor)`` — FR-PERF-003.

    Surveyed bytes divided by **the throughput the survey observed on this
    machine**, not by :data:`THROUGHPUT_FLOOR`. The floor is a lower bound an
    implementation is meant to beat, so dividing by it would overstate every
    estimate by exactly the margin of the beating: at a real 1 GB/s the
    estimate would be twice the actual duration, failing SC-PERF-003's ±25%
    while the implementation was entirely correct.

    The second element is ``True`` when the survey was too small to time and
    the floor was used instead. The caller **must say so** in its output, so a
    pessimistic estimate is never presented as a measured one.

    **The measured estimate is itself conservative, by about 2.2x-2.5x**,
    and :func:`render_estimate` says so. The survey scans for *any* uuid shape —
    five character classes at every position — while the apply pass substitutes
    *known literal* tokens, which is the faster search; so the survey's observed
    throughput understates the apply pass's. SC-PERF-003's ±25% is recorded as
    exceeded in ``baseline.md`` for this reason, in the safe direction.
    ``tests/integration/test_estimate_tolerance.py`` holds the measurement and
    the bound.
    """
    throughput = survey_result.observed_throughput
    if throughput is None:
        return survey_result.bytes_read / THROUGHPUT_FLOOR, True
    return survey_result.bytes_read / throughput, False


def render_estimate(survey_result: Survey) -> str:
    seconds, used_floor = estimate_seconds(survey_result)
    how = (
        f"the {THROUGHPUT_FLOOR / 1_000_000:.0f} MB/s floor — the survey was too "
        "small to time, so this figure is a pessimistic bound, not a measurement"
        if used_floor
        else f"{survey_result.observed_throughput / 1_000_000:.1f} MB/s, measured by "
             "the survey on this machine"
    )
    caveat = "" if used_floor else (
        " — a conservative bound: the survey scans for any uuid shape, which "
        "costs more per byte than the substitution's literal search, so the "
        "rewrite typically finishes in about half this (see baseline.md)"
    )
    return (
        f"{len(survey_result.documents)} document(s), "
        f"{survey_result.bytes_read / 1_000_000:.2f} MB to rewrite; "
        f"estimated {seconds:.2f} s at {how}{caveat}"
    )


# -- the verification (step 7) ---------------------------------------------------------


@dataclass
class Verification:
    """Per-check results (FR-016–FR-018). Data only; the caller decides."""

    zero_old_tokens: bool = False
    documents_valid: bool = False
    load_succeeds: bool = False
    adoption_unchanged: bool = False
    failures: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return (self.zero_old_tokens and self.documents_valid
                and self.load_succeeds and self.adoption_unchanged)

    def as_dict(self) -> dict:
        return asdict(self)


_SCHEMA_BY_NAME = {
    "settings.xml": "settings",
    "network_map.xml": "network_map",
    "default_mappings.xml": "project_mappings",
}


def _schema_for(path: Path) -> str | None:
    if path.name in _SCHEMA_BY_NAME:
        return _SCHEMA_BY_NAME[path.name]
    root = library_reach.root_local_name(path)
    if root == library_reach.SCRIPT_ROOT:
        return "script"
    if root == library_reach.MAPPINGS_ROOT:
        return "project_mappings"
    return None


def adoption_state(map_path) -> dict[str, tuple[str, str]]:
    """``mac -> (adopted, online)``, read with stdlib XML.

    Keyed by **MAC**, deliberately: the identity is the thing that changes, so
    keying on it would compare two different nodes and report every adoption as
    preserved. "Match by uuid, key by MAC" is the map's own practice, and this
    is the one comparison where only the MAC survives the operation.
    """
    path = Path(map_path)
    if not path.is_file():
        return {}
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return {}
    state: dict[str, tuple[str, str]] = {}
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "node":
            continue
        mac = (element.findtext("mac") or "").strip()
        if mac:
            state[mac] = (
                (element.findtext("adopted") or "").strip(),
                (element.findtext("online") or "").strip(),
            )
    return state


def verify(conf, documents, table: SubstitutionTable,
           adoption_before: dict, load: bool = True) -> Verification:
    """Zero old tokens, every touched document valid, a full load, adoption kept.

    **The one place the validating load path is used**, and it runs only after
    the rewrite has made validation possible (FR-006a). Before the rewrite
    these documents are, by construction, exactly the ones the schema refuses.
    """
    conf = Path(conf)
    failures: list[str] = []

    survivors = []
    for path in documents:
        text = _safe_read(path)
        for old in table.entries:
            if old in text:
                survivors.append(f"{path}: still carries {old}")
    if survivors:
        failures.extend(survivors)

    invalid = []
    for path in documents:
        schema_name = _schema_for(Path(path))
        if schema_name is None:
            continue
        try:
            from ..xml.schema import get_schema

            get_schema(schema_name).validate(str(path))
        except Exception as exc:  # noqa: BLE001 — any failure is a failure, named
            invalid.append(f"{path}: does not validate against {schema_name}.xsd ({exc})")
    if invalid:
        failures.extend(invalid)

    loaded = True
    if load:
        try:
            from .ConfigManager import ConfigManager

            ConfigManager(config_dir=str(conf), load_all=False).load_config()
        except Exception as exc:  # noqa: BLE001
            loaded = False
            failures.append(f"{conf}: a full load does not succeed ({exc})")

    after = adoption_state(conf / "network_map.xml")
    adoption_kept = after == adoption_before
    if not adoption_kept:
        failures.append(
            f"adoption state changed: before={adoption_before} after={after}"
        )

    return Verification(
        zero_old_tokens=not survivors,
        documents_valid=not invalid,
        load_succeeds=loaded,
        adoption_unchanged=adoption_kept,
        failures=tuple(failures),
    )


# -- the completion record (step 8, data-model §2.3) -----------------------------------


@dataclass
class CompletionRecord:
    """One per node per run. What makes "the cluster is converged" countable.

    The controller's run exiting cleanly says nothing about any other node,
    which is the whole reason this exists (FR-036c).
    """

    node: str
    table_digest: str
    table_path: str
    scope: str
    rewritten: list[str]
    verification: dict
    finished: str

    def save(self, path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path) -> "CompletionRecord":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**raw)


def completion_record_path(state_dir, node: str) -> Path:
    return Path(state_dir) / STATE_SUBDIR / f"completion-{node}.json"


def roll_call(records, map_path) -> tuple[bool, tuple[str, ...], tuple[str, ...]]:
    """``(complete, missing, unexpected)`` — the operator's count (FR-036c).

    ``records`` is every completion record collected from the cluster; the map
    supplies the rows. Equal sets mean the cluster is converged; a row with no
    record is a node the migration did not reach, and is reported as
    **incomplete** rather than inferred to be fine.
    """
    path = Path(map_path)
    rows: set[str] = set()
    if path.is_file():
        try:
            root = ET.parse(str(path)).getroot()
        except (ET.ParseError, OSError):
            root = None
        if root is not None:
            for element in root.iter():
                if element.tag.rsplit("}", 1)[-1] == "node":
                    uuid = (element.findtext("uuid") or "").strip()
                    if uuid:
                        rows.add(uuid)
    held = {record.node for record in records}
    missing = tuple(sorted(rows - held))
    unexpected = tuple(sorted(held - rows))
    return (not missing, missing, unexpected)


# -- the run ---------------------------------------------------------------------------


def _map_controller(map_path) -> str | None:
    """The identity of the row whose ``node_role`` is ``controller``."""
    path = Path(map_path)
    if not path.is_file():
        return None
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return None
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "node":
            continue
        if (element.findtext("node_role") or "").strip() == "controller":
            return (element.findtext("uuid") or "").strip() or None
    return None


def _own_identity(conf: Path) -> str | None:
    path = conf / "settings.xml"
    if not path.is_file():
        return None
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError):
        return None
    node = next((e for e in root.iter() if e.tag.rsplit("}", 1)[-1] == "node"), None)
    return ((node.findtext("uuid") if node is not None else None) or "").strip() or None


def _is_controller(own: str | None, map_controller: str | None,
                   table: "SubstitutionTable | None") -> bool:
    """Whether this node is the cluster's controller, across a partial rewrite.

    The plain comparison is ``own == map_controller``. The two table-aware ones
    exist because the re-mint rewrites ``settings.xml`` and ``network_map.xml``
    at different moments, so between them the two documents disagree **by
    design** — one carries the new identity and the other still the old. Both
    directions are checked because which document is ahead depends only on
    where the interruption fell.
    """
    if own is None or map_controller is None:
        return False
    if own == map_controller:
        return True
    if table is None:
        return False
    return (table.entries.get(map_controller) == own
            or table.entries.get(own) == map_controller)


def _record_nothing_to_do(state, own, table, scope) -> None:
    """A run that found nothing to do still leaves a completion record.

    It is this node's evidence that it was reached, and the roll-call counts
    records, not rewrites (FR-017a, FR-036c). A converged node with no record
    is indistinguishable from one the migration never reached.
    """
    node = own or ""
    CompletionRecord(
        node=node,
        table_digest=table.digest(),
        table_path="",
        scope=scope,
        rewritten=[],
        verification=Verification(True, True, True, True).as_dict(),
        finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    ).save(completion_record_path(state, node))


def run(args, *, confirm=None) -> int:  # noqa: C901 - the eight ordered steps
    """``cuems-init-node --remint``. The eight steps of contracts/cli-remint.md.

    Args:
        args: the parsed namespace — ``conf_dir``, ``state_dir``, ``library``,
            ``table``, ``dry_run``, ``resume``, ``yes``.
        confirm: injected for tests; called with the estimate when ``--yes``
            was not passed. Returning ``False`` abandons the run without
            writing.

    Returns:
        int: 0 done or nothing to do, 1 aborted or refused, 2 verification
        failed after a rewrite — a distinguishable class, because "we changed
        your cluster and cannot prove it is right" is not the same news as
        "we changed nothing".
    """
    conf = Path(args.conf_dir)
    state = Path(args.state_dir)

    own = _own_identity(conf)
    map_controller = _map_controller(conf / "network_map.xml")

    # The table is resolved and loaded **first**, because deciding whether this
    # node is the controller needs it. A partly-applied run leaves the two
    # documents disagreeing by construction: ``settings.xml`` is rewritten
    # before ``network_map.xml``, so between them this node's own identity is
    # the new one while the map's controller row still carries the old. A
    # comparison that did not know the table would read that as "not the
    # controller" and silently drop the library from the reach — on the resume
    # of the very run that was rewriting it.
    resolved_table = Path(args.table) if getattr(args, "table", None) else table_path(state)
    table = SubstitutionTable.load(resolved_table) if resolved_table.is_file() else None

    is_controller = _is_controller(own, map_controller, table)

    # 1. Survey — stdlib XML only.
    reach = library_reach.resolve(conf, getattr(args, "library", None))
    if not is_controller:
        # A plain node never rewrites its replica of the library: it is
        # controller-authoritative and arrives by replication (FR-011a).
        reach = library_reach.LibraryReach(
            None, degraded="this node is not the controller; its library replica is not "
                           "rewritten in place — it arrives by the project deployer's "
                           "replication on the next project load (FR-011a)"
        )
    found = survey(conf, reach)
    for note in found.notes:
        print(f"note: {note}")

    # 2. Refuse on a collision — before the table is built, so an abort costs
    #    not even a minted identity.
    found_collisions = collisions(conf / "network_map.xml")
    if found_collisions:
        raise Abort(collision_message(found_collisions, found.documents))

    # 3-4. The table: loaded if one exists, built only on the controller.
    scope = BOTH if is_controller else CONFIGURATION

    if table is not None:
        # A table whose ``controller`` is not *this* node is the normal case on
        # every node but one. The refusal is on a table minted by something
        # with no authority to mint it (data-model §2.2).
        #
        # Two values are acceptable, and the second is what makes a resume work
        # after the map itself has been rewritten: the table records the
        # controller's identity as it was at build time, while a partly-applied
        # map may already carry the controller's *new* one.
        acceptable = {table.controller, table.entries.get(table.controller)}
        if map_controller is not None and map_controller not in acceptable:
            raise Refused(
                f"the table was built by {table.controller}, which is not this cluster's "
                f"controller ({map_controller}); it was minted by something with no "
                "authority to mint it"
            )
        print(f"table: {resolved_table} ({len(table.entries)} entr(ies), "
              f"{len(table.applied)} file(s) already applied)")
    elif not is_controller:
        raise Refused(
            "this node is not the controller and no substitution table was given. "
            "Minting one locally is the divergence this design exists to prevent — "
            "pass --table with the table the controller built and the operator copied here."
        )
    else:
        table = build_table(found.node_identities, controller=own or "", scope=scope)
        if not table.entries:
            print("every node identity is already converged; nothing to do")
            _record_nothing_to_do(state, own, table, scope)
            return 0

    table.scope = scope
    table.check_invariants()

    # 5. Estimate and confirm.
    print(render_estimate(found))
    if getattr(args, "dry_run", False):
        # Writes nothing at all, not even a table (FR-PERF-003).
        for old, new in sorted(table.entries.items()):
            print(f"would substitute {old} -> {new}")
        for path in found.documents:
            print(f"would rewrite {path}" if any(old in _safe_read(path) for old in table.entries)
                  else f"unchanged {path}")
        return 0

    if not getattr(args, "yes", False):
        answer = confirm(render_estimate(found)) if confirm else False
        if not answer:
            print("abandoned; nothing was written")
            return 1

    # 4. Persist before the first write. This is the operation's only durable record.
    if not resolved_table.is_file():
        table.save(resolved_table)
    documents = list(found.documents)

    adoption_before = adoption_state(conf / "network_map.xml")

    # 6. Apply.
    rewritten = apply_table(table, documents, table_file=resolved_table)
    for path in rewritten:
        print(f"rewritten {path}")

    # 7. Verify.
    new_identity = table.entries.get(own or "", own or "")
    result = verify(conf, documents, table, adoption_before)
    for failure in result.failures:
        print(f"VERIFICATION FAILED: {failure}")

    # 8. Record.
    record = CompletionRecord(
        node=new_identity,
        table_digest=table.digest(),
        table_path=str(resolved_table),
        scope=scope,
        rewritten=[str(p) for p in rewritten],
        verification=result.as_dict(),
        finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    record.save(completion_record_path(state, new_identity))
    print(f"completion record: {completion_record_path(state, new_identity)}")
    if scope == CONFIGURATION:
        print("scope: configuration only — this node's library replica is not rewritten "
              "in place; it arrives by replication on the next project load")
    print("the cluster is converged only when one completion record exists per row in "
          "the network map; this node's run says nothing about the others")

    return 0 if result.ok else 2
