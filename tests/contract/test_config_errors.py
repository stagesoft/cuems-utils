"""Contract C2 errors (T039a) — FR-014b, SC-020, CHK037.

Config **accessors** take the same error posture as the show surface, for the
same reason: two failure kinds a consumer must tell apart must not arrive as
one exception.

================================  ==================================  ===============
condition                         raises                              why
================================  ==================================  ===============
config file missing/unreadable    ``OSError``, **unwrapped**          a node with no
                                                                      config and a
                                                                      node with a
                                                                      corrupt one are
                                                                      different
                                                                      operational
                                                                      problems
file fails schema validation      ``SchemaError`` naming the element  ...and they must
                                                                      never arrive as
                                                                      the same type
================================  ==================================  ===============

**The posture belongs to the accessor, not to the reader**, and the split is
deliberate. ``ConfigManager``/``ConfigBase`` is what a consumer holds; the
``Settings`` family is internal machinery that US4 turns into a deprecation
shim, and its *raw* verdicts are what ``tests/golden/outcomes.json`` pins
document by document. Wrapping down there would have moved a recorded golden to
express a requirement about a surface one layer up.

The schema-failure fixture is the measured **X13** case: ``gradient_osc_port``
was added to ``settings.xsd`` as **required**, which invalidated every settings
file written before it — including two this project shipped, vendored as
``negative/settings-utils-v0.1.0rc2.xml`` and ``-rc7.xml``.

X13 is **reported here and fixed elsewhere**: under the schema evolution
convention, not in this feature. No ``.xsd`` is edited here (FR-033). What this
pins is that the failure is *legible* — an operator can tell "this file
predates a schema change" from "there is no file".
"""

from __future__ import annotations

import os
import shutil

import pytest

from cuemsutils.errors import CuemsError, SchemaError
from cuemsutils.tools.ConfigManager import ConfigManager
from tests.support.config_inventory import CONFIG_DIR
from tests.support.corpus import by_relpath

#: The two settings files this project shipped before ``gradient_osc_port``
#: became required. Vendored precisely so the regression has a name.
X13_DOCUMENTS = [
    "negative/settings-utils-v0.1.0rc2.xml",
    "negative/settings-utils-v0.1.0rc7.xml",
]


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """A writable copy of the vendored configuration directory."""
    monkeypatch.delenv("CUEMS_CONF_PATH", raising=False)
    target = tmp_path / "cuems"
    shutil.copytree(CONFIG_DIR, target)
    return target


def test_the_fixture_directory_loads_cleanly(config_dir):
    """The control. Without it, every failure below could be the fixture."""
    assert ConfigManager(config_dir=str(config_dir)) is not None


def test_a_missing_config_directory_raises_oserror_unwrapped(tmp_path, monkeypatch):
    monkeypatch.delenv("CUEMS_CONF_PATH", raising=False)
    with pytest.raises(FileNotFoundError) as caught:
        ConfigManager(config_dir=str(tmp_path / "absent"))
    assert not isinstance(caught.value, CuemsError)


def test_a_missing_settings_file_raises_oserror_unwrapped(config_dir):
    (config_dir / "settings.xml").unlink()
    with pytest.raises(FileNotFoundError) as caught:
        ConfigManager(config_dir=str(config_dir))
    assert not isinstance(caught.value, CuemsError)


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses file permissions",
)
def test_an_unreadable_settings_file_raises_oserror_unwrapped(config_dir):
    target = config_dir / "settings.xml"
    target.chmod(0o000)
    try:
        with pytest.raises(OSError) as caught:
            ConfigManager(config_dir=str(config_dir))
        assert not isinstance(caught.value, CuemsError)
    finally:
        target.chmod(0o600)


@pytest.mark.parametrize("relpath", X13_DOCUMENTS)
def test_a_schema_invalid_settings_file_raises_schema_error(config_dir, relpath):
    (config_dir / "settings.xml").write_bytes(by_relpath(relpath).path.read_bytes())
    with pytest.raises(SchemaError) as caught:
        ConfigManager(config_dir=str(config_dir))
    assert not isinstance(caught.value, OSError)


@pytest.mark.parametrize("relpath", X13_DOCUMENTS)
def test_the_schema_error_names_the_offending_element(config_dir, relpath):
    """"It failed validation" is not actionable; *what* failed is.

    The X13 case must say ``gradient_osc_port``, because that word is what
    tells an operator the file predates a schema change rather than being
    corrupt.
    """
    (config_dir / "settings.xml").write_bytes(by_relpath(relpath).path.read_bytes())
    with pytest.raises(SchemaError) as caught:
        ConfigManager(config_dir=str(config_dir))
    assert "gradient_osc_port" in str(caught.value), str(caught.value)


def test_a_schema_invalid_network_map_raises_schema_error(config_dir):
    """Asserted per document kind, because each has its own call site."""
    (config_dir / "network_map.xml").write_bytes(
        by_relpath("cuems-common/network_map.xml").path.read_bytes()
    )
    with pytest.raises(SchemaError):
        ConfigManager(config_dir=str(config_dir))


def test_the_two_failures_never_share_a_type(config_dir, tmp_path, monkeypatch):
    """The requirement, stated as the thing a consumer actually does."""
    monkeypatch.delenv("CUEMS_CONF_PATH", raising=False)

    (config_dir / "settings.xml").write_bytes(
        by_relpath(X13_DOCUMENTS[0]).path.read_bytes()
    )
    with pytest.raises(SchemaError):
        ConfigManager(config_dir=str(config_dir))

    try:
        ConfigManager(config_dir=str(tmp_path / "absent"))
    except SchemaError:  # pragma: no cover - would mean the types collapsed
        pytest.fail("a missing config directory was reported as a schema failure")
    except FileNotFoundError:
        pass


def test_an_absent_optional_section_is_not_an_error(config_dir):
    """C2's third row: an accessor asked for a section the document omits gets
    the model-layer default, per the schema evolution convention.

    ``project_settings`` is absent from the vendored fixture, and
    ``load_project_config`` says so at INFO and carries on rather than raising.
    """
    manager = ConfigManager(config_dir=str(config_dir))
    manager.load_project_config("test_project")
    assert manager.project_conf == {}


def test_the_internal_reader_keeps_its_raw_verdict():
    """The other half of the split, asserted so it cannot drift.

    ``tests/golden/outcomes.json`` records the exact exception type and message
    head that ``Settings`` produces for every corpus document. If the reader
    ever started wrapping, that golden would have to move — and moving it is
    what this design avoids.
    """
    from cuemsutils.xml import Settings

    doc = by_relpath(X13_DOCUMENTS[0])
    with pytest.raises(Exception) as caught:
        Settings(str(doc.path))
    assert not isinstance(caught.value, CuemsError), (
        "the internal reader started wrapping; outcomes.json now disagrees"
    )
