import json
import json_fix

from .CueList import CueList
from .MediaCue import MediaCue
from ..log import logged, Logger
from ..helpers import as_cuemsdict, ensure_items, new_uuid, new_datetime, unique_values_to_list, CuemsDict
from ..tools.Uuid import Uuid

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

    def to_json(self):
        """Convert the script to a JSON string.
        
        Returns:
            str: A JSON string representation of the script.
        """
        return json.dumps({'CuemsScript': self})

    def __json__(self):
        """The script's JSON payload — the editor's ``project_load`` body.

        The root does not self-wrap, so a child that *does* would arrive
        double-wrapped: ``CueList.__json__`` returns ``{"CueList": {...}}`` and
        the root already files it under the key ``CueList``. One of the two
        wrappers has to go, and it is the child's.

        This used to be decided by testing ``k.lower() != k`` — reading a
        structural property off the **casing of a key name**, which happened to
        work because the one wrapped child on the root is spelled ``CueList``.
        It now asks the child whether it self-wraps (``JSON_SELF_WRAPS``), which
        is the same question stated directly.

        Only *direct* children are unwrapped. List members stay wrapped —
        ``contents`` is a list of ``{"AudioCue": {...}}`` entries, and that
        wrapper is what tells the editor which cue type it is holding.

        **Arrival order, not declared order**, and this is the one projection
        where that distinction bites. ``CuemsScript`` is an ``xs:all`` type: the
        schema imposes no order, so emission order *is* arrival order. This
        payload is what the editor rebuilds and writes back, so ordering it by
        ``REQ_ITEMS`` — which lists ``CueList`` before ``ui_properties`` while
        every document carries the reverse — would re-sort the root element of
        every hand-authored script on the next save. ``items()`` is ordered by
        the declaration for the benefit of ordered (``xs:sequence``) types; the
        root filters by the same declared set but keeps its own order.
        """
        declared = set(self.declared_fields())
        payload = {}
        for key in list(self):
            if key not in declared:
                continue
            value = self[key]
            rendered = value.__json__() if hasattr(value, '__json__') else value
            if getattr(value, 'JSON_SELF_WRAPS', False):
                rendered = rendered[type(value).__name__]
            payload[key] = rendered
        return payload
