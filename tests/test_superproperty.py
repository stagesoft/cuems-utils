"""
Test that a class can call diretly a __super__ property from a parent class.

It also shows how when inheriting from a dict, object properties are different than the dictionary keys.
"""

### Arrange
class Parent(dict):
    def __init__(self):
        self["_hello"] = "Hello, World!"

    @property
    def hello(self) -> str:
        return self["_hello"]
    
    @hello.setter
    def hello(self, value: str) -> None:
        self["_hello"] = value

class Child(Parent):
    def __init__(self, hello_str: str):
        super().__init__()
        self.hello = hello_str
        self.bye = "See you soon!"

### Act
parent = Parent()

sec_parent = Parent()
sec_parent.hello = "Hello World!, also"

child = Child("Goodbye, World!")

child.bye2 = "See you later!"


### Assert
def test_superproperty():
    """Test that a class can call diretly a __super__ property from a parent class."""
    assert parent.hello == "Hello, World!"
    assert sec_parent.hello == "Hello World!, also"
    
    assert child.hello == "Goodbye, World!"
    assert child.hello == child["_hello"]
    assert child.bye == "See you soon!"
    assert child.bye2 == "See you later!"

    child["bye3"] = "See you later, alligator!"
    child.__setitem__("bye4", "See you later, alligator!")

    assert [i for i in child.keys()] == ["_hello", "bye3", "bye4"]

    import json
    assert json.dumps(child) == '{"_hello": "Goodbye, World!", "bye3": "See you later, alligator!", "bye4": "See you later, alligator!"}'

def test_frominitdict(caplog):
    from src.cuemsutils.log import Logger
    from logging import DEBUG
    caplog.set_level(DEBUG)

    class Parent(dict):
        def __init__(self, init_dict = None):
            if init_dict:
                for k, v in init_dict.items():
                    try:
                        x = getattr(self, f"set{k}")
                        x(v)
                    except AttributeError:
                        next
        
        def seta(self, a):
            super().__setitem__('a', a + 1)

        def setb(self, b):
            super().__setitem__('_b', b + 1)

        def setc(self, c):
            super().__setitem__('c', c)

        @property
        def a(self):
            return str(super().__getitem__('a'))
        @a.setter
        def a(self, a):
            # a =+ 1
            super().__setitem__('a', a)

        @property
        def b(self):
            return super().__getitem__('_b')
        @b.setter
        def b(self, b):
            super().__setitem__('_b', b)

        @property
        def C(self):
            return super().__getitem__('c')
        @C.setter
        def C(self, c):
            super().__setitem__('c', c)

    p = Parent({"a": 1, "b": 3, "_b": 2, "_c": 3, "c": True})

    import json
    assert json.dumps(p) == '{"a": 2, "_b": 4, "c": true}'
