import pytest
from cortexheal.runtime.hashing import deterministic_hash, serialize

def test_deterministic_hash_same_object():
    obj1 = {"a": 1, "b": {"c": 2}, "d": [1, 2, 3]}
    obj2 = {"d": [1, 2, 3], "a": 1, "b": {"c": 2}}
    assert deterministic_hash(obj1) == deterministic_hash(obj2)

def test_deterministic_hash_different_object():
    obj1 = {"a": 1}
    obj2 = {"a": 2}
    assert deterministic_hash(obj1) != deterministic_hash(obj2)

def test_deterministic_hash_none_handling():
    assert deterministic_hash(None) == "null_hash"

def test_deterministic_hash_empty_handling():
    assert deterministic_hash({}) == "empty_hash"
    assert deterministic_hash([]) == "empty_hash"
    assert deterministic_hash("") == "empty_hash"

def test_deterministic_hash_data_types():
    obj1 = {"int": 1, "float": 1.0, "bool": True, "str": "test", "none": None}
    obj2 = {"none": None, "str": "test", "bool": True, "float": 1.0, "int": 1}
    assert deterministic_hash(obj1) == deterministic_hash(obj2)
