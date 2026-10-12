from re import match
from uuid import uuid4

UUID4_REGEX = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

class Uuid():
    """A class to interact with unique identifiers.
        
        Comparisions should be made based on memory allocation.

        Calling or printing the instance will return the uuid4 string.
    """
    def __init__(self, uuid: str | None = None):
        if not uuid:
            self.uuid = str(uuid4())
        else:
            self.uuid = str(uuid)
        if not self.check():
            raise ValueError(f'uuid {uuid} is not valid')
    
    def __str__(self):
        return self.uuid
    
    def __repr__(self):
        return self.uuid

    def __call__(self):
        return self.uuid

    def __hash__(self):
        return hash(self.uuid)

    def __eq__(self, other):
        if isinstance(other, Uuid):
            return self.uuid == other.uuid
        elif isinstance(other, str):
            return self.uuid == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    # -- total ordering (feature 012, FR-029, data-model §6.2) --------------
    #
    # ``sorted()`` over a collection of these used to raise ``TypeError``, which
    # every consumer hit the first time it wanted a stable node order. Adding it
    # here removes the failure for all of them at once, including the ones that
    # have not been fixed (M-b) — the argument for putting it in the library
    # rather than asking each consumer to convert.
    #
    # Ordering **completes** the comparison set rather than introducing new
    # semantics. ``__eq__`` and ``__hash__`` already work against both ``Uuid``
    # and ``str``, so the only consistent ordering is the string form's, and it
    # crosses the same boundary: a set that compared equal to a ``str`` and
    # refused to order against one would be the more confusing outcome.
    #
    # ``functools.total_ordering`` is deliberately not used. It derives the
    # other three operators from ``__lt__`` and ``__eq__``, and ``__eq__`` here
    # returns ``False`` for an unrelated type rather than ``NotImplemented`` —
    # so the derived ``__le__`` would answer ``True`` for
    # ``Uuid(...) <= object()`` instead of raising. Spelling the four out keeps
    # ``NotImplemented`` where it belongs.
    #
    # **Not added**: slicing, ``len`` and ``split``. They would invite treating
    # an identity as a string in ways the compound ``<identity>_<output>``
    # parsing already handles elsewhere, and the consumer census (research R4)
    # found no site that needs them.

    def _comparable(self, other) -> str | None:
        if isinstance(other, Uuid):
            return other.uuid
        if isinstance(other, str):
            return other
        return None

    def __lt__(self, other):
        value = self._comparable(other)
        return NotImplemented if value is None else self.uuid < value

    def __le__(self, other):
        value = self._comparable(other)
        return NotImplemented if value is None else self.uuid <= value

    def __gt__(self, other):
        value = self._comparable(other)
        return NotImplemented if value is None else self.uuid > value

    def __ge__(self, other):
        value = self._comparable(other)
        return NotImplemented if value is None else self.uuid >= value


    def __json__(self):
        return self.uuid

    def items(self):
        return [("uuid", self.uuid)]
    
    def check(self):
        m = match(UUID4_REGEX, self.uuid)
        if m:
            return m.span() == (0, 36)
        return False
