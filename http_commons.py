import re

nlc = new_line_character = "\r\n"


def extract_headers(request: str) -> (dict[str, str], str):
    """Split headers and return as dictionary"""
    split = request.split(nlc + nlc, 1)
    header_block = split[0]
    body = split[1]
    headers = {}
    header_match = re.findall(r"(\S+): (\S+)", header_block)
    for name, value in header_match:
        headers[name] = value
    return headers, body


def to_bytes(string: str) -> bytes:
    """Encode string into bytes"""
    return string.encode()
