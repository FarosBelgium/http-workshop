import clientproperties


# This class represents a HttpRequest-object on CLIENT side
class HttpRequest:

    # Instantiates a HttpRequest-object with given server name, path and request body.
    # In fact, this class should not be instantiated as this is considered to be abstract.
    def __init__(self, server: str, path: str, request_body: str):
        self.server = server

        if not path.startswith("/"):
            path = "/" + path
        self.path = path

        if request_body:
            self.request_body = request_body

    # Returns a textual representation of the http request, encoded in binary data
    def __repr__(self) -> bytes:
        return self.__str__().encode(clientproperties.encoding)


class HttpHeadRequest(HttpRequest):

    # Returns a textual representation of the http HEAD request
    def __str__(self):
        return f"HEAD {self.path} HTTP/1.1\r\nHost: {self.server}\r\n\r\n"


class HttpGetRequest(HttpRequest):

    # Returns a textual representation of the http GET request
    def __str__(self):
        return f"GET {self.path} HTTP/1.1\r\nHost: {self.server}\r\n\r\n"


class HttpPutRequest(HttpRequest):

    # Returns a textual representation of the http PUT request
    def __str__(self):
        return f"PUT {self.path} HTTP/1.1\r\nHost: {self.server}\r\n\r\n{self.request_body}"


class HttpPostRequest(HttpRequest):

    # Returns a textual representation of the http POST request
    def __str__(self):
        return f"POST {self.path} HTTP/1.1\r\nHost: {self.server}\r\n\r\n{self.request_body}"


# Creates a suitable instance of a subclass of a HttpRequest-object given a command, a server name, a path and
# a request body if necessary
def create_http_request(command: str, server: str, path: str, request_body: str):
    command = command.title()
    http_request = globals()[f"Http{command}Request"]
    return http_request(server, path, request_body)
