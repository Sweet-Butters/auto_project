from auto_project.main import greet


def test_greet_default():
    assert greet() == "Hello, world!"


def test_greet_with_name():
    assert greet("Alice") == "Hello, Alice!"
