import clientproperties
from bodydecoder import create_body_decoder


# This class represents an HttpResponse-object on CLIENT side
class HttpResponse:

    # Instantiates an HttpResponse-object. In fact, this class should not be instantiated as this is considered to be
    # abstract.
    def __init__(self):
        self.headers = dict()

    # Does the same as the __str__() method for each subclass
    def __repr__(self):
        return self.__str__()

    # Retrieves the charset from the headers. If the headers don't contain a content type, None is returned.
    # If no charset is specified, ISO-8859-1 will be used.
    @property
    def charset(self):
        if "Content-Type" not in self.headers:
            return None
        try:
            content_type = self.headers["Content-Type"]
            return content_type.split("charset=")[1]
        except IndexError:
            return "ISO-8859-1"

    # Returns a textual representation of the headers info
    @property
    def textual_headers(self):
        result = self.headers["Status"] + "\n"
        for key, value in self.headers.items():
            if key == "Status":
                continue
            result += f"{key}: {value}\n"

        return result.strip()

    # Fills the headers dictionary (instance variable) with the given headers information
    def fill_dict_of_headers(self, headers: str):
        headers = headers.split("\r\n")
        self.headers["Status"] = headers[0].strip()
        for line in headers[1:]:
            key, value = line.split(": ")
            self.headers[key] = value.strip()


class HttpHeadResponse(HttpResponse):

    # Instantiates a HttpHeadResponse-object with given raw response information in bytes
    def __init__(self, response: bytes):
        super().__init__()
        headers = response.strip().decode(clientproperties.encoding)
        self.fill_dict_of_headers(headers)
        print("\n" + self.textual_headers)
        print("-" * 200)

    # Provides a textual representation of the HttpHeadResponse-object.
    # It returns the decoded headers information in a readable format.
    def __str__(self):
        return self.textual_headers


class HttpGetResponse(HttpResponse):

    # Instantiates a HttpGetResponse-object with given raw response information in bytes
    def __init__(self, response: bytes):
        super().__init__()
        response = response.strip()
        headers, body = response.split(b'\r\n\r\n', 1)
        headers = headers.decode(clientproperties.encoding)
        self.fill_dict_of_headers(headers)
        self.__body = body
        print("\n" + self.textual_headers)
        print("-" * 200)

    # Returns the raw body (in bytes) of the http response
    @property
    def raw_body(self):
        return self.__body

    # Returns the decoded body in the charset specified in the headers
    @property
    def decoded_body(self) -> str:
        return create_body_decoder(self.headers, self.raw_body, self.charset).decode()

    # Provides a textual representation of the HttpGetResponse-object.
    # It returns the decoded body in a readable format.
    def __str__(self):
        return self.decoded_body


class HttpPutResponse(HttpResponse):

    # Instantiates a HttpPutResponse-object with given raw response information in bytes
    def __init__(self, response: bytes):
        super().__init__()
        headers = response.strip().decode(clientproperties.encoding)
        self.fill_dict_of_headers(headers)
        print("\n" + self.textual_headers)
        print("-" * 200)

    # Provides a textual representation of the HttpPutResponse-object.
    # It returns the decoded headers information in a readable format.
    def __str__(self):
        return self.textual_headers


class HttpPostResponse(HttpResponse):

    # Instantiates a HttpPostResponse-object with given raw response information in bytes
    def __init__(self, response: bytes):
        super().__init__()
        headers = response.strip().decode(clientproperties.encoding)
        self.fill_dict_of_headers(headers)
        print("\n" + self.textual_headers)
        print("-" * 200)

    # Provides a textual representation of the HttpPostResponse-object.
    # It returns the decoded headers information in a readable format.
    def __str__(self):
        return self.textual_headers


# Creates a suitable instance of a subclass of a HttpResponse-object given a command and raw response
# information in bytes
def create_http_response(command: str, response: bytes) -> HttpResponse:
    command = command.title()
    http_response = globals()[f"Http{command}Response"]
    return http_response(response)
