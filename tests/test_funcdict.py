def test_funcdict():
    """Proof of concept that a function can be called from a dictionary."""

    ## Arrange
    def hello():
        return "Hello, World!"
    
    def goodbye():
        return "Goodbye, World!"

    func_dict = {
        "hello": hello,
        "goodbye": goodbye
    }

    ## Act
    result_hello = func_dict["hello"]()
    result_goodbye = func_dict["goodbye"]()

    func_hello = func_dict["hello"]

    ## Assert
    assert result_hello == "Hello, World!"
    assert result_goodbye == "Goodbye, World!"
    assert func_hello() == "Hello, World!"
