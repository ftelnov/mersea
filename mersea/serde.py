import base64
import json
import zlib


def encode(code: str) -> str:
    """Encode mermaid code into a pako URL fragment for mermaid.live."""
    state = {
        "code": code,
        "mermaid": '{"theme":"default"}',
        "updateDiagram": True,
        "rough": False,
    }
    json_bytes = json.dumps(state).encode("utf-8")
    compressed = zlib.compress(json_bytes, 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"pako:{encoded}"


def decode(hash_str: str) -> str:
    """Decode a pako URL fragment back to mermaid code."""
    if hash_str.startswith("#"):
        hash_str = hash_str[1:]
    if not hash_str.startswith("pako:"):
        raise ValueError(f"Expected 'pako:' prefix, got: {hash_str[:20]}")

    data = hash_str[5:]
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding

    compressed = base64.urlsafe_b64decode(data)
    json_bytes = zlib.decompress(compressed)
    state = json.loads(json_bytes)
    return state["code"]
