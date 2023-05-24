import os
from abc import *

import serverproperties
from filemanager import FileManager
from httpdate import HttpDate
from httprequest import HttpRequest


# This class represents a HttpResponse-object on SERVER side
class HttpResponse:

    # Instantiates a HttpResponse-object with given path and request_body.
    # In fact, this class should not be instantiated as this is considered to be abstract.
    def __init__(self, status_code: int, http_request: HttpRequest, file_manager: FileManager, close_connection: bool):
        self.headers = {}
        self.status_code = status_code
        self.http_request = http_request
        self.file_manager = file_manager
        self.close_connection = close_connection

        try:
            last_modified: float = os.stat(self.file_manager.file_path_on_server).st_mtime
            self.last_modified = HttpDate.get_http_date_from_timestamp(last_modified)
        except FileNotFoundError:
            self.last_modified = None

        self.headers["Content-Type"] = self.content_type
        self.headers["Content-Length"] = file_manager.size
        self.headers["Date"] = HttpDate.now()

    @property
    def response_headers(self) -> str:
        result = f"HTTP/1.1 {self.status_code}"
        if self.status_code == 200:
            result += " OK\r\n"
        result += '\r\n'.join([f"{key}: {value}" for key, value in self.headers.items()])
        return result

    @property
    def empty_line(self) -> str:
        return "\r\n\r\n"

    @property
    def content_type(self) -> str:
        file_path = self.file_manager.file_path
        _, extension = file_path.split(".")
        match extension:
            case "html":
                return f"text/html; charset={serverproperties.encoding}"
            case "txt":
                return f"text/plain; charset={serverproperties.encoding}"
            case "json":
                return "application/json"
            case "pdf":
                return "application/pdf"
            case "gif":
                return "image/gif"
            case "png":
                return "image/png"
            case "jpg":
                return "image/jpg"
            case _:
                raise RuntimeError(f"The given content type '{extension}' is currently not supported")

    @abstractmethod
    def __repr__(self) -> bytes:
        raise RuntimeError()


class HttpHeadResponse(HttpResponse):

    def __init__(self, status_code: int, http_request: HttpRequest, file_manager: FileManager, close_connection: bool):
        super().__init__(status_code, http_request, file_manager, close_connection)

    def __repr__(self) -> bytes:
        return (self.response_headers + self.empty_line).encode(serverproperties.encoding)


class HttpGetResponse(HttpResponse):
    def __init__(self, status_code: int, http_request: HttpRequest, file_manager: FileManager, close_connection: bool):
        super().__init__(status_code, http_request, file_manager, close_connection)
        self.response_body = file_manager.read_file()

    def __repr__(self) -> bytes:
        return (self.response_headers + self.empty_line).encode(serverproperties.encoding) + self.response_body


class HttpPostResponse(HttpResponse):

    def __init__(self, status_code: int, http_request: HttpRequest, file_manager: FileManager, close_connection: bool):
        super().__init__(status_code, http_request, file_manager, close_connection)
        request_body = http_request.request_body

        try:
            self.file_manager.append_text_to_file(request_body)
        except FileNotFoundError:
            self.file_manager.write_text_to_file(request_body)

        self.headers["Content-Location"] = self.file_manager.file_path
        self.headers["Content-Length"] = file_manager.size
        self.response_body = file_manager.read_file()

    def __repr__(self) -> bytes:
        return (self.response_headers + self.empty_line).encode(serverproperties.encoding) + self.response_body


class HttpPutResponse(HttpResponse):

    def __init__(self, status_code: int, http_request: HttpRequest, file_manager: FileManager, close_connection: bool):
        super().__init__(status_code, http_request, file_manager, close_connection)
        request_body = http_request.request_body
        self.file_manager.write_text_to_file(request_body)

        self.headers["Content-Location"] = self.file_manager.file_path
        self.headers["Content-Length"] = file_manager.size
        self.response_body = file_manager.read_file()

    def __repr__(self) -> bytes:
        return (self.response_headers + self.empty_line).encode(serverproperties.encoding) + self.response_body


def create_http_response(status_code: int, close_connection: bool, http_request: HttpRequest = None,
                         file_manager: FileManager = None) -> HttpResponse:
    command = http_request.command.title()

    if not file_manager:
        error_path = os.path.join(serverproperties.content_path, "error", f"{status_code}.html")
        file_manager = FileManager(error_path)

    return globals()[f"Http{command}Response"](status_code, http_request, file_manager, close_connection)
