from re import match
from uuid import uuid4


UUID4_REGEX = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'

class Uuid():
    """A class to interact with unique identifiers.
        
        Comparisions should be made based on memory allocation.

        Calling or printing the instance will return the uuid4 string.
    """
    def __init__(self, uuid: str = None):
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

    def __eq__(self, other):
        if isinstance(other, Uuid):
            return self.uuid == other.uuid
        elif isinstance(other, str):
            return self.uuid == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __json__(self):
        return self.uuid

    def items(self):
        return [("uuid", self.uuid)]
    
    def check(self):
        m = match(UUID4_REGEX, self.uuid)
        if m:
            return m.span() == (0, 36)
        return False
