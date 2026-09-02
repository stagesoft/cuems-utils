import json
import json_fix

from collections.abc import Mapping

from .CueList import CueList
from .MediaCue import MediaCue
from ..errors import IngestError, LoadReport, SchemaError, ValidationError
from ..log import logged, Logger
from ..helpers import as_cuemsdict, ensure_items, new_uuid, new_datetime, unique_values_to_list, CuemsDict
from ..tools.Uuid import Uuid

#: The schema every script document is described by. Bound here, once, so that
#: **no public signature takes a schema name** (FR-021, SC-004): it is a
#: property of the type, not of the caller, and it is passed at six call sites
#: across three repositories today.
SCHEMA_NAME = 'script'

REQ_ITEMS = {
    'id': new_uuid,
    'name': 'empty',
    'description': None,
    'created': new_datetime,
    'modified': new_datetime,
    # The **class**, not an instance — ``ensure_items`` and
    # ``from_decoded`` both call a callable default, exactly as they do for
    # ``new_uuid`` and ``new_datetime`` above. ``CueList()`` and ``CueList({})``
    # build the same object, so the defaulted value is unchanged.
    #
    # It used to be ``CueList({})``, evaluated once at **module import**, which
    # made a single cue-list instance the shared default for every script ever
    # constructed. It also could not survive this feature: the setters now
    # consult the schema-derived adapter table, so building a cue list at module
    # scope re-entered the registry while this very module was still
    # initialising, and ``import cuemsutils.cues.CuemsScript`` died with a
    # circular import. Deferring construction fixes both.
    'CueList': CueList,
    'ui_properties': None
}

class CuemsScript(CuemsDict):
    """A class representing a complete CueMS script.

    The script root is an **ordinary model object** (FR-012). Until feature 005
    it was a plain ``dict``, and that one exception is what forced a duplicated
    ``setter``, a divergent ``items()``, a missing build hook and the key-casing
    heuristic in ``__json__``: no guarantee about "every model object" could be
    stated while one object in the model answered "no" to *is this a
    declared-field model object?*
    """

    #: Declared fields and their defaults for this class alone;
    #: :meth:`CuemsDict.declared_defaults` accumulates the chain.
    DECLARED_DEFAULTS = REQ_ITEMS

    #: The root is the **only** model class that does not self-wrap: it is the
    #: document body, so its JSON is the payload rather than an entry in one.
    JSON_SELF_WRAPS = False

    def __init__(self, init_dict = None):
        """Initialize a CuemsScript.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
            self.setter(init_dict)
        self._fill_declared_defaults()

    def get_id(self):
        """Get the unique identifier of the script.
        
        Returns:
            Uuid: The script's unique identifier.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the unique identifier of the script.
        
        Args:
            id: The new unique identifier.
        """
        super().__setitem__('id', self.coerce('id', id))

    id: Uuid = property(get_id, set_id)

    def get_name(self):
        """Get the name of the script.
        
        Returns:
            str: The script's name.
        """
        return super().__getitem__('name')

    def set_name(self, name):
        """Set the name of the script.
        
        Args:
            name (str): The new name for the script.
        """
        super().__setitem__('name', name)

    name: str = property(get_name, set_name)

    def get_description(self):
        """Get the description of the script.
        
        Returns:
            str: The script's description.
        """
        return super().__getitem__('description')

    def set_description(self, description):
        """Set the description of the script.
        
        Args:
            description (str): The new description for the script.
        """
        super().__setitem__('description', description)

    description: str = property(get_description, set_description)

    def get_created(self):
        """Get the creation timestamp of the script.
        
        Returns:
            datetime: When the script was created.
        """
        return super().__getitem__('created')

    def set_created(self, created):
        """Set the creation timestamp of the script.
        
        Args:
            created (datetime): The new creation timestamp.
        """
        super().__setitem__('created', created)

    created = property(get_created, set_created)

    def get_modified(self):
        """Get the last modification timestamp of the script.
        
        Returns:
            datetime: When the script was last modified.
        """
        return super().__getitem__('modified')

    def set_modified(self, modified):
        """Set the last modification timestamp of the script.
        
        Args:
            modified (datetime): The new modification timestamp.
        """
        super().__setitem__('modified', modified)

    modified = property(get_modified, set_modified)

    def get_CueList(self) -> CueList:
        """Get the main cue list of the script.
        
        Returns:
            CueList: The script's main cue list.
        """
        return super().__getitem__('CueList')

    def set_CueList(self, cuelist: CueList | dict):
        """Set the main cue list of the script.
        
        Args:
            cuelist (CueList or dict): The new cue list or a dictionary to create one.
            
        Raises:
            ValueError: If the cuelist is not a valid CueList object or dictionary.
        """
        if not isinstance(cuelist, CueList):
            try:
                cuelist = CueList(cuelist)
            except:
                raise ValueError(
                    f'CueList {cuelist} is not a CueList object or a valid dict'
                )
        super().__setitem__('CueList', cuelist)

    cuelist: CueList = property(get_CueList, set_CueList)

    def get_ui_properties(self) -> CuemsDict:
        """Get the UI properties of the script.
        
        Returns:
            dict: The script's UI properties.
        """
        return super().__getitem__('ui_properties')

    def set_ui_properties(self, ui_properties: dict | CuemsDict):
        """Set the UI properties of the script.
        
        Args:
            ui_properties (dict): The new UI properties.
        """
        Logger.debug(f"Setting ui_properties to {ui_properties}")
        ui_properties = as_cuemsdict(ui_properties)
        super().__setitem__('ui_properties', ui_properties)

    ui_properties: CuemsDict = property(get_ui_properties, set_ui_properties)

    def find(self, uuid):
        """Find a cue by its UUID in the script.
        
        Args:
            uuid: The UUID to search for.
            
        Returns:
            Cue or None: The found cue, or None if not found.
        """
        return self.cuelist.find(uuid)

    @logged
    def get_media(self) -> dict:
        """Get all media files referenced in a CueList.
        
        Args:
            cuelist (CueList, optional): The cue list to search in.
                If not provided, uses the script's main cue list.
                
        Returns:
            dict: A dictionary mapping Cue UUIDs to their media information.
        """
        return self.cuelist.get_media()
    
    @logged
    def get_media_filenames(self) -> list:
        """Get all media filenames referenced in a CueList.
        
        Returns:
            list: A list of media filenames.
        """
        media_dict = {k: list(v.values())[0] for k, v in self.get_media().items()}
        return unique_values_to_list(media_dict)

    @logged
    def get_own_media(self, config: dict, cuelist: CueList | None = None) -> dict:
        """Get media files that are local to the current node.
        
        Args:
            cuelist (CueList, optional): The cue list to search in.
                If not provided, uses the script's main cue list.
            config: The configuration containing node information.
                
        Returns:
            dict: A dictionary mapping media file names to their associated cues
                that are local to the current node.
        """
        media_dict = dict()

        # If no cuelist is specified we are looking inside our own
        # script object, so our cuelist is our self cuelist
        if not cuelist:
            cuelist = self.cuelist

        if not cuelist.has_contents():
            return media_dict

        pos = 0
        for cue in cuelist.contents:  # type: ignore[union-attr]
            Logger.debug(f'CuemsScript get_own_media: {pos} {cue}')
            if type(cue) == CueList:
                media_dict.update(
                    self.get_own_media(config=config, cuelist=cue)
                )
            elif isinstance(cue, MediaCue) and hasattr(cue.media, 'file_name'):
                Logger.debug(f'get_own_media media cue at {pos}')
                cue.localize_cue(config.node_conf['uuid'])
                if cue._local:
                    media_dict[str(cue.id)] = cue.media.file_name
            pos += 1
        return media_dict

    @logged
    def get_own_media_filenames(self, config: dict, cuelist: CueList | None = None) -> list:
        """Get all media filenames that are local to the current node.
        
        Returns:
            list: A list of media filenames.
        """
        return unique_values_to_list(
            self.get_own_media(config=config, cuelist=cuelist)
        )

    # -- the public surface (T024, T025, T027, T028) ------------------------
    #
    # Six methods, and after this feature they are the only supported way
    # script data enters or leaves the library. ``to_wire``/``to_json`` are
    # inherited from ``CuemsDict`` unchanged — one body, shared with the config
    # models (FR-014a) — so they do not appear here.

    @classmethod
    def load(cls, path) -> 'CuemsScript':
        """Read a script document from disk.

        The returned object is **fully coerced**: every field holds its
        declared type, at every depth, regardless of how the document was
        written. That is a guarantee rather than a convention — there is no
        public path that produces a partially coerced script.

        **Runs full validation — T1 and T2** (feature 008, FR-037). This is a
        deliberate reversal of the earlier principle that reading never
        becomes stricter (FR-038, recorded here since this is the call site
        the reversal happens at): a document version older than this schema's
        current one converts **in memory** (the file on disk is left
        untouched — FR-041, FR-041a); a current document with a repairable
        semantic violation is repaired to its descriptor default; a current
        document with an unrepairable one raises; a document whose version
        marker is newer than this library raises, distinguishably (FR-052).
        Its runtime state is already initialized either way, so the engine can
        run it with no promotion step.

        This method keeps its signature so existing callers compile — it
        simply has no way to hand back *what* happened beyond the object
        itself. A caller that needs the conversions/repairs applied calls
        :meth:`load_with_report` instead (contracts §2).

        Replaces ``XmlReaderWriter(schema_name="script",
        xmlfile=path).read_to_objects()``.

        Args:
            path (str | os.PathLike): the document. Relative paths resolve
                against the process working directory, not against the package.

        Returns:
            CuemsScript: the decoded script.

        Raises:
            SchemaError: the document does not match ``script.xsd`` (T1).
            ValidationError: an unrepairable T2 violation, or a document
                version newer than this library (T2/version, FR-044/FR-052).
            OSError: propagated **unwrapped** — ``FileNotFoundError`` for a
                missing file, ``PermissionError`` for an unreadable one. Every
                consumer already handles these, and wrapping them would force
                callers to unwrap them to find out what happened (FR-035).
        """
        obj, _report = cls._load_full(path)
        return obj

    @classmethod
    def load_with_report(cls, path) -> tuple['CuemsScript', 'LoadReport']:
        """As :meth:`load`, and also returns what the load did (contracts §2).

        The report answers FR-046's five questions from data alone — which
        document, which conversions ran, which fields were repaired and to
        what, and whether the file on disk is now stale — so a caller
        (feature 009) can surface a load that changed something without this
        library acquiring a notification channel of its own (FR-047).

        A caller that saves a repaired or converted object **without** having
        read this report first destroys the original document, unreviewed,
        the moment it does — the library cannot prevent that, which is why
        surfacing the report is a migration-guide precondition (FR-053a)
        rather than something this method enforces.

        Returns:
            tuple[CuemsScript, LoadReport]: the decoded script, and a report
            with ``outcome == Outcome.CLEAN`` and both tuples empty for a
            document that needed neither conversion nor repair — never
            ``None`` in place of the report.

        Raises:
            Same as :meth:`load`.
        """
        return cls._load_full(path)

    @classmethod
    def _load_full(cls, path) -> tuple['CuemsScript', 'LoadReport']:
        """The one load path both :meth:`load` and :meth:`load_with_report`
        share (mirrors :meth:`_decode` being the one decode path both public
        entry points share, FR-001)."""
        from ..errors import ConversionRecord, Outcome
        from ..xml.documents import read_document_versioned
        from ..xml.validators import Violation, repair
        from ..xml.versioning import DocumentTooNewError

        try:
            source, original_version, steps = read_document_versioned(SCHEMA_NAME, path)
        except OSError:
            raise
        except DocumentTooNewError as exc:
            raise ValidationError(
                str(exc),
                violation=Violation("T1", "document_version_too_new", (None, None), str(exc)),
            ) from exc
        except Exception as exc:
            raise SchemaError(f"{path} is not a valid script document: {exc}") from exc

        obj = cls._decode(source)
        repairs = repair(obj)

        if repairs:
            outcome = Outcome.REPAIRED
        elif steps:
            outcome = Outcome.CONVERTED
        else:
            outcome = Outcome.CLEAN

        conversions = tuple(
            ConversionRecord(step.from_version, step.to_version, step.description, step.dropped_elements)
            for step in steps
        )
        report = LoadReport(
            document=str(path),
            outcome=outcome,
            conversions=conversions,
            repairs=tuple(repairs),
            file_differs_from_loaded=outcome is not Outcome.CLEAN,
        )
        return obj, report

    @classmethod
    def from_json(cls, payload) -> 'CuemsScript':
        """Build a script from a JSON payload — the editor's ingestion path.

        Accepts **all three** forms (contracts §C0): a JSON ``str``, UTF-8
        ``bytes``, or an already-decoded ``Mapping``. ``bytes`` is decoded as
        UTF-8 **only** and never sniffed for another codec (FR-036c). Both the
        wrapped shape ``{"CuemsScript": {...}}`` and a bare script body are
        accepted, because the editor sends both.

        Same coercion guarantee and same validation posture as :meth:`load`.
        Keys the schema does not declare are dropped and logged at ``DEBUG``,
        one record naming the class and the key.

        **What "structural validation" means here** (FR-023a): there is no XML
        document to hand the schema, so T1 is the mapper's *decode-time* check
        — every key resolved against a declared field, every value accepted by
        its adapter. It is deliberately not a second pass that builds a
        document in order to validate it, which would pay the projection cost
        FR-005a exists to avoid on the hottest ingestion path in the system.
        The asymmetry that follows, stated rather than left to be inferred: a
        payload accepted here can still fail :meth:`save`'s document-level
        check for a constraint only expressible on the assembled document
        (``xs:assert``). :meth:`load` carries the same asymmetry today; it is
        not new.

        Replaces ``CuemsParser(payload).parse()``.

        Args:
            payload (str | bytes | Mapping): the script payload.

        Returns:
            CuemsScript: the decoded script.

        Raises:
            IngestError: the payload is **not a script at all** — a JSON array
                or scalar, malformed JSON, a mapping whose root nothing
                recognises, or bytes that are not valid UTF-8. The message
                names what was expected.
            SchemaError: the payload *is* a script and fails the decode-time
                structural check.
        """
        return cls._decode(cls._ingest(payload))

    def validate(self):
        """Validate this object, with **no file involved**.

        Runs T1 **and** T2 and **collects** every violation rather than
        stopping at the first. That is the deliberate asymmetry with
        :meth:`save`: ``validate()`` exists to *inspect*, so it answers
        exhaustively; ``save()`` exists to *persist*, so it answers atomically
        and early.

        Replaces ``XmlReaderWriter(schema_name="script",
        xmlfile=None).validate_object(obj)``.

        Returns:
            A validation report. The type is internal — a caller inspects the
            report it is handed and never constructs one — so its shape is
            documented here in full, and this is the only place it is
            published:

            * the report is **falsy when empty**, so ``if script.validate():``
              reads as *"there are violations"*;
            * it reports ``len()`` and **iterates its violations**;
            * each violation carries four fields: ``tier`` (``"T1"``
              structural or ``"T2"`` semantic, so the two are distinguishable
              and neither absorbs the other), ``rule`` (the registered rule
              name for T2, the schema constraint for T1), ``location`` — a
              **pair** ``(cue_id, field)``, with ``cue_id`` ``None`` for a
              document-scoped rule, so a caller can address either half
              without parsing a string — and ``message``.

        Raises:
            Nothing on a violation: it reports them. Raising is :meth:`save`'s
            job, and only :meth:`save`'s. Errors from a genuinely
            unserializable object (a DMX scene that cannot be written)
            propagate.
        """
        from ..xml.validators import ValidationReport, Violation

        try:
            tree = self._build_tree()
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            return ValidationReport(
                [Violation('T1', 'document_build', (None, None), str(exc))]
            )
        return ValidationReport(self._violations(tree))

    def save(self, path) -> None:
        """Validate, **then** write.

        Runs T1 and T2 and raises at the **first** failure. On failure no file
        is created, truncated or partially written at the target path: the
        document is serialized to a temporary file in the target's directory
        and moved into place with an atomic rename, so a reader sees either the
        previous document or the new one.

        Persists **declared fields only**. Saving while a show is running is
        supported and document-only: playback state is ignored and the call
        does not refuse. The library never observes that a show is running and
        does not acquire a mechanism to.

        Replaces ``XmlReaderWriter(...).write_from_object(obj)``.

        Args:
            path (str | os.PathLike): where to write.

        Raises:
            SchemaError: a structural (T1) violation. Carries the violation.
            ValidationError: a semantic (T2) violation. Carries the violation,
                in the same form :meth:`validate` reports it (FR-034b) — a
                consumer catching this has something to show a user.
            OSError: propagated **unwrapped**, exactly as in :meth:`load`. A
                missing parent directory or a full filesystem is not a
                validation failure and must not arrive as one.
        """
        from ..xml.documents import write_tree

        tree = self._build_tree()
        for violation in self._violations(tree):
            error = SchemaError if violation.tier == 'T1' else ValidationError
            raise error(str(violation), violation=violation)
        write_tree(tree, path)

    # -- the machinery behind the six --------------------------------------

    @classmethod
    def _ingest(cls, payload) -> dict:
        """One of the three accepted forms, as a mapping — or ``IngestError``.

        Every refusal here is *"this is not a script"*, which is why they share
        an exception type distinct from ``SchemaError``: nothing was validated,
        because there was nothing of the right shape to validate.
        """
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = bytes(payload).decode('utf-8')
            except UnicodeDecodeError as exc:
                raise IngestError(
                    f"expected UTF-8 bytes for a {cls.__name__} payload; the "
                    f"input is not valid UTF-8 and no other codec is guessed: "
                    f"{exc}"
                ) from exc

        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError as exc:
                raise IngestError(
                    f"expected JSON text describing a {cls.__name__}: {exc}"
                ) from exc

        if not isinstance(payload, Mapping):
            raise IngestError(
                f"expected a {cls.__name__} payload as a mapping, JSON text or "
                f"UTF-8 bytes; got {type(payload).__name__}"
            )

        body = payload.get(cls.__name__) if len(payload) == 1 else None
        if body is not None:
            if not isinstance(body, Mapping):
                raise IngestError(
                    f"{cls.__name__} payload body must be a mapping, got "
                    f"{type(body).__name__}"
                )
            return {cls.__name__: dict(body)}

        # A bare body: accepted when it names at least one declared field. The
        # alternative — accepting any mapping — turns "this is not a script"
        # into a ``KeyError`` from somewhere inside the decoder, which is the
        # shape of failure FR-002 exists to prevent.
        if not set(payload) & set(cls.declared_fields()):
            raise IngestError(
                f"expected a {cls.__name__} payload; the mapping declares none "
                f"of {list(cls.declared_fields())} (got {sorted(payload)})"
            )
        return {cls.__name__: dict(payload)}

    @classmethod
    def _decode(cls, source: dict) -> 'CuemsScript':
        """The one decode path both public entry points share (FR-001)."""
        from ..xml.mapper import Mapper

        try:
            return Mapper(SCHEMA_NAME).decode_document(source)
        except (ValueError, TypeError, KeyError) as exc:
            raise SchemaError(
                f"the payload does not match {SCHEMA_NAME}.xsd: {exc}"
            ) from exc

    def _build_tree(self):
        from ..xml.documents import build_tree

        return build_tree(self, SCHEMA_NAME)

    def _violations(self, tree) -> list:
        """T1 then T2, in that order — the one list both call sites read.

        ``save()`` takes the first and ``validate()`` takes them all, from the
        **same** production, so the two cannot report a document differently
        and the violation carried on a raised exception is a value
        ``validate()`` also reports (FR-034b).

        T1 runs first because a structurally broken document makes every
        semantic finding on it unreliable, and because the two tiers must stay
        distinguishable rather than one absorbing the other.
        """
        from ..xml.documents import iter_schema_errors
        from ..xml.validators import run_rules, violation_from_schema_error

        violations = [
            violation_from_schema_error(error)
            for error in iter_schema_errors(SCHEMA_NAME, tree)
        ]
        violations.extend(run_rules(self))
        return violations

    def __json__(self):
        """The script's JSON payload — the editor's ``initial_template`` body.

        **The one ``__json__`` this feature keeps, and it projects nothing**
        (T036). It unwraps the document body: :meth:`to_wire` names the root
        element it produces — ``{"CuemsScript": {...}}``, matching what
        ``project_load`` carries — while ``json.dumps(script)`` has
        historically produced the body alone.

        That single line is what closes F21 without editing a consumer
        repository. ``cuems-editor``'s ``initial_template`` call site receives
        the **same** projection ``project_load`` does, so the two payloads stop
        disagreeing on every boolean (``true`` against ``"True"``) and on
        ``ui_properties`` integers. No frontend change is required: the
        existing ``=== true || === 'True'`` dual-check already absorbs it.

        Everything the old body did by hand — filtering to declared fields,
        preserving the root's *arrival* order (``CuemsScript`` is an ``xs:all``
        type, so emission order is arrival order), unwrapping a self-wrapping
        direct child — now happens once inside the projection, for every model
        object rather than for this one.
        """
        return self.to_wire()[type(self).__name__]
