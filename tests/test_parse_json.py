from interview_helper.parse_json import extract_json_array, extract_json_object


def test_extract_json_object_plain() -> None:
    data = extract_json_object('{"a": 1, "b": "x"}')
    assert data == {"a": 1, "b": "x"}


def test_extract_json_object_with_fence() -> None:
    data = extract_json_object("```json\n{\"ok\": true}\n```")
    assert data == {"ok": True}


def test_extract_json_array_plain() -> None:
    data = extract_json_array('[{"a": 1}, {"a": 2}]')
    assert data == [{"a": 1}, {"a": 2}]

