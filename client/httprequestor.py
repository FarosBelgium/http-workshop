import socket

from httprequest import create_http_request
from httpresponse import *


class HttpRequestor:

    # Instantiates a HttpRequestor-object with given server, port, path and request body.
    # If no port is given, the value of the client properties file will be used
    # If no path is given, it is '/' by default.
    # If no command is given, it is 'GET' by default.
    # If no body is given, it is None by default.
    def __init__(self, server: str, port: int = clientproperties.port, path: str = "/", command: str = "GET",
                 body: str = None):
        self.server = server
        self.port = port
        self.path = path
        self.command = command
        self.body = body
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(clientproperties.timeout)
        self.client.connect(self.address)

    # Returns a tuple of the server name and the server port
    @property
    def address(self) -> tuple:
        return self.server, self.port

    # Executes an http request with given response length. If no response length is given, it is 1024 bytes by default.
    # An HttpResponse-object is returned by this method.
    def request(self, response_length: int = 1024) -> HttpResponse:
        self.__send()
        response = self.__receive(response_length)
        assert response

        # If the response is not complete yet, the remaining parts will be retrieved at this point.
        while True:
            next = self.__receive(1024)
            if not next:
                break
            response += next

        return create_http_response(self.command, response)

    def __send(self):
        http_request = create_http_request(self.command, self.server, self.path, self.body)
        request = http_request.__repr__()
        print(str(http_request).strip())
        self.client.send(request)

    def __receive(self, length: int):
        try:
            return self.client.recv(length)
        except socket.error:
            return None
