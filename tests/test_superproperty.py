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
