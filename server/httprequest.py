# This class represents a HttpRequest-object on SERVER side
class HttpRequest:

    # Instantiates a HttpRequest-object given the headers and body from the client
    def __init__(self, headers, request_body):
        self.headers = headers
        self.request_body = request_body

    # Returns the asked command of the client
    @property
    def command(self):
        return self.headers["Command"].split(" ")[0]

    # Returns the file path asked by the client
    @property
    def file_path(self):
        return self.headers["Command"].split(" ")[1]


def parse_http_request(message: str) -> HttpRequest:
    headers, *body = message.split("\r\n\r\n", 1)
    headers = headers.split("\n")
    headers_dict = {"Command": headers[0].strip()}
    for line in headers[1:]:
        key, value = line.split(":", 1)
        headers_dict[key] = value.rstrip().strip()
    body = "\n".join(body)
    return HttpRequest(headers_dict, body)
