import pytest

from api.routers.system import sanitize_value, sanitize_dict

def test_sanitize_value_none():
    """Test sanitize_value with None."""
    assert sanitize_value(None) == 0.0

@pytest.mark.parametrize("input_value, expected_output", [
    (10, 10),
    (0, 0),
    (-5, -5),
    (3.14, 3.14),
    (0.0, 0.0),
    (-2.5, -2.5),
    ("string", "string"),
    ([1, 2, 3], [1, 2, 3]),
    (True, True)
])
def test_sanitize_value_normal_values(input_value, expected_output):
    """Test sanitize_value with valid/normal types."""
    assert sanitize_value(input_value) == expected_output

@pytest.mark.parametrize("invalid_value", [
    float('nan'),
    float('inf'),
    float('-inf')
])
def test_sanitize_value_nan_inf(invalid_value):
    """Test sanitize_value specifically for NaN and Infinity."""
    assert sanitize_value(invalid_value) == 0.0

def test_sanitize_dict_empty():
    """Test sanitize_dict with empty dictionary."""
    assert sanitize_dict({}) == {}

def test_sanitize_dict_flat():
    """Test sanitize_dict with flat dictionary without nans."""
    input_data = {"a": 1, "b": "test", "c": 3.14, "d": None}
    expected = {"a": 1, "b": "test", "c": 3.14, "d": 0.0}
    assert sanitize_dict(input_data) == expected

def test_sanitize_dict_flat_with_nan_inf():
    """Test sanitize_dict with flat dictionary containing NaN and Inf."""
    input_data = {"a": float('nan'), "b": float('inf'), "c": float('-inf'), "d": 5}
    expected = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 5}
    assert sanitize_dict(input_data) == expected

def test_sanitize_dict_nested_dicts():
    """Test sanitize_dict with nested dictionaries containing NaN and Inf."""
    input_data = {
        "level1": {
            "a": float('nan'),
            "level2": {
                "b": float('inf'),
                "c": 10
            }
        },
        "d": 42
    }
    expected = {
        "level1": {
            "a": 0.0,
            "level2": {
                "b": 0.0,
                "c": 10
            }
        },
        "d": 42
    }
    assert sanitize_dict(input_data) == expected

def test_sanitize_dict_nested_lists():
    """Test sanitize_dict with lists containing mixed elements including NaN and Inf."""
    input_data = {
        "list1": [1, float('nan'), 3.14, float('inf')],
        "list2": ["test", None, float('-inf')],
        "empty_list": []
    }
    expected = {
        "list1": [1, 0.0, 3.14, 0.0],
        "list2": ["test", 0.0, 0.0],
        "empty_list": []
    }
    assert sanitize_dict(input_data) == expected

def test_sanitize_dict_complex_nested():
    """Test sanitize_dict with complex mix of nested dicts and lists."""
    input_data = {
        "data": [
            {"id": 1, "score": float('nan')},
            {"id": 2, "score": 95.5, "metadata": {"confidence": float('inf')}},
            [float('-inf'), {"nested_list_dict": float('nan')}]
        ],
        "status": "ok"
    }
    expected = {
        "data": [
            {"id": 1, "score": 0.0},
            {"id": 2, "score": 95.5, "metadata": {"confidence": 0.0}},
            [0.0, {"nested_list_dict": 0.0}]
        ],
        "status": "ok"
    }
    assert sanitize_dict(input_data) == expected
