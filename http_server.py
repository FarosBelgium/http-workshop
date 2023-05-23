import logging
import os.path
import signal
import socket
import threading
import time
from datetime import datetime
from threading import Thread

import select

from http_commons import extract_headers, nlc, to_bytes

host_port = 8080
max_buffer_size = 1024

logging.basicConfig(level=logging.DEBUG)


def start_server():
    """Setup listening socket, start waiting for connections"""
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.debug("Socket successfully created.")
    except socket.error as err:
        logging.error(f"Socket creation failed with error {err}.")
        return
    server_socket.bind(('', host_port))
    server_socket.listen()
    logging.debug("Socket is listening...")
    await_connections(server_socket)


def await_connections(server_socket: socket):
    """Handle incoming connections, keep track of active connections through threads"""

    def interrupt_handler(signum, frame):
        """Wait for all connection threads to shut down"""
        logging.debug("Interrupt signal received")
        while threading.active_count() > 1:
            logging.debug(f"Waiting for {threading.active_count() - 1} threads to finish")
            time.sleep(1)
        logging.debug("Closing server socket")
        server_socket.close()
        logging.debug("Server socket closed")
        exit(1)

    signal.signal(signal.SIGINT, interrupt_handler)

    while True:
        readable, _, _ = select.select([server_socket], [], [], 1.0)
        if server_socket in readable:
            client, address = server_socket.accept()
            logging.debug(f"Connected to: {address[0]}:{address[1]}")
            thread = Thread(target=client_connection_handler_thread, args=[client])
            thread.start()


def client_connection_handler_thread(client_socket: socket):
    """Handling of opened connections and any HTTP messages received within a thread"""
    logging.debug(f"Thread started: connected to {client_socket.getpeername()}")
    try:
        while True:
            logging.debug("Receiving data from client")
            data = client_socket.recv(max_buffer_size)
            if not data:
                logging.debug("No data received from socket, indicating connection was closed from client side")
                break
            elif data:
                request = data.decode('utf-8')  # decode the bytes received from the socket into a str
                method, _, _, remainder = extract_request_line(request)
                mode = 0
                if method == "PUT" or method == "POST":
                    mode = 1
                if mode == 0:
                    while not request.endswith('\r\n\r\n'):
                        """until two newlines are received (signifying the end of the HTTP request) 
                        we keep pulling data from the socket"""
                        logging.debug("Request didn't end with 2 newline characters, receiving more data.")
                        data = client_socket.recv(max_buffer_size)
                        request += data.decode('utf-8')
                elif mode == 1:
                    logging.debug("Fetching data until all is received according to Content-Length header")
                    headers, remainder = extract_headers(remainder)
                    content_length = headers["Content-Length"]
                    while len(remainder) != int(content_length):
                        data = client_socket.recv(max_buffer_size)
                        data = data.decode('utf-8')
                        request += data
                        remainder += data
                logging.debug("Received full request")
                handle_request(client_socket, request)
    except Exception as e:
        logging.error("Exception caught: %s", e)
        headers = server_error_headers()
        body = status_code_body(500)
        send_response(client_socket, 500, headers, body)
        raise
    finally:
        logging.debug(f"Shutdown thread: connected to {client_socket.getpeername()}")
        client_socket.shutdown(socket.SHUT_RDWR)
        client_socket.close()
        logging.debug(f"Shutdown thread done")


def handle_request(client_socket: socket, request: str) -> None:
    """Handles a complete HTTP request"""
    (method, uri, version, remainder) = extract_request_line(request)
    logging.debug(f"Extracted request line: {method} {uri} {version}")
    request_headers, body = extract_headers(remainder)
    logging.debug(f"Extracted request headers: {request_headers}")
    if not (validate_version(version) or validate_request_headers(request_headers)):
        response_status, response_headers, response_body = bad_request_response()
    else:
        logging.debug("Passed version and header validation")
        if method == "HEAD":
            response_status, response_headers, response_body = handle_head_request(uri, request_headers)
        elif method == "GET":
            response_status, response_headers, response_body = handle_get_request(uri, request_headers)
        elif method == "PUT":
            response_status, response_headers, response_body = handle_put_request(uri, body)
        elif method == "POST":
            response_status, response_headers, response_body = handle_post_request(uri, body)
        else:
            response_status, response_headers, response_body = method_not_allowed_response()

    send_response(client_socket, response_status, response_headers, response_body)


def send_response(client_socket: socket, status: int, headers: dict[str, any], body: bytes) -> None:
    response_line = f"HTTP/1.1 {map_status(status)}"
    if body:
        size = len(body)
        if size > max_buffer_size * 10:
            headers["transfer-coding"] = "chunked"
            header_block = stringify_headers(headers)
            response_start = to_bytes(response_line + nlc + header_block + nlc)
            client_socket.sendall(response_start)
            index = 0
            while index < size:
                left = index
                right = (index + max_buffer_size) if size > index + max_buffer_size else size
                body_part = body[left: right]
                hexed = hex(len(body_part))
                index = index + max_buffer_size
                to_send = to_bytes(hexed + nlc) + body_part + to_bytes(nlc)
                client_socket.sendall(to_send)
            client_socket.sendall(to_bytes("0" + nlc))
        else:
            headers["Content-Length"] = size
            header_block = stringify_headers(headers)
            response = to_bytes(response_line + nlc + header_block + nlc) + body
            client_socket.sendall(response)
    else:
        header_block = stringify_headers(headers)
        response = to_bytes(response_line + nlc + header_block + nlc)
        client_socket.sendall(response)


def stringify_headers(headers: dict[str, any]) -> str:
    header_block = ""
    for header in headers:
        header_block += f"{header}: {headers[header]}{nlc}"
    return header_block


def map_status(status: int) -> str:
    if status == 200:
        return "200 Success"
    if status == 304:
        return "304 Not Modified"
    if status == 400:
        return "400 Bad Request"
    if status == 404:
        return "404 Not Found"
    if status == 405:
        return "405 Method Not Allowed"
    if status == 500:
        return "500 Server Error"

    return f"{status} Unmapped status"


def validate_request_headers(headers: dict[str, str]) -> bool:
    """Check whether all required request headers are present"""
    if "Host" not in headers:
        return False
    return True


def extract_request_line(request: str) -> (str, str, str, str):
    """Extract and split request line from request"""
    first_line_end = request.find(nlc)
    first_line = request[:first_line_end]
    [method, uri, version] = first_line.split(" ")
    return method, uri, version, request[first_line_end + 2:]


def handle_head_request(uri: str, request_headers: dict[str, str]) -> (int, dict[str, str], bytes):
    """Handle HEAD request and return response (basically equal to GET handling but without body in the response)"""
    logging.debug("Handling HEAD request")
    if not is_found(uri):
        return 404, not_found_headers(), None
    if not is_modified(uri, request_headers):
        return 304, not_modified_headers(), None
    headers = generic_headers(uri)
    headers["Content-Length"] = get_size(uri)
    return 200, headers, None


def handle_get_request(uri: str, request_headers: dict[str, str]) -> (int, dict[str, str], bytes):
    """Handle GET request and return response"""
    logging.debug("Handling GET request")
    if not is_found(uri):
        return not_found_response()
    if not is_modified(uri, request_headers):
        return not_modified_response()
    headers = generic_headers(uri)
    body = get_body(uri)
    return 200, headers, body


def handle_put_request(uri: str, body: str) -> (int, dict[str, str], bytes):
    """Handle PUT request and return response"""
    logging.debug("Handling PUT request")
    created = not os.path.isfile(map_uri(uri))
    new_fd = open(map_uri(uri), 'w')
    new_fd.write(body)
    new_fd.close()
    if created:
        status = 201
    else:
        status = 200
    headers = put_or_post_headers(uri)
    return status, headers, None


def handle_post_request(uri: str, body: str) -> (int, dict[str, str], bytes):
    """Handle POST request and return response"""
    logging.debug("Handling POST request")
    fd = open(map_uri(uri), 'a')
    fd.write(body)
    fd.close()
    headers = put_or_post_headers(uri)
    return 200, headers, None


def bad_request_response() -> (int, dict[str, str], bytes):
    """Create a standard 400 Bad Request message"""
    header = bad_request_headers()
    body = status_code_body(400)
    return 400, header, body


def method_not_allowed_response() -> (int, dict[str, any], bytes):
    """Create a standard 405 Method Not Allowed message"""
    headers = method_not_allowed_headers()
    body = status_code_body(405)
    return 405, headers, body


def not_found_response() -> (int, dict[str, any], bytes):
    """Create a standard 404 Not Found message"""
    headers = not_found_headers()
    body = status_code_body(404)
    return 404, headers, body


def not_modified_response() -> (int, dict[str, any], bytes):
    """Create a standard 304 Not Modified message"""
    headers = not_modified_headers()
    body = status_code_body(304)
    return 304, headers, body


def bad_request_headers() -> dict[str, any]:
    """Create header for bad request message"""
    return generic_headers("/400_bad_request.html")


def method_not_allowed_headers() -> dict[str, any]:
    """Create header for method not allowed message"""
    headers = generic_headers("/405_method_not_allowed.html")
    headers["Allow"] = "GET,HEAD,PUT,POST"
    return headers


def not_found_headers() -> dict[str, any]:
    """Create a standard 404 Not Found header"""
    return generic_headers("/404_not_found.html")


def not_modified_headers() -> dict[str, any]:
    """Create a standard 304 Not Modified header"""
    return generic_headers("/304_not_modified.html")


def put_or_post_headers(uri: str) -> dict[str, any]:
    """Create a success header"""
    date = current_date()
    headers = dict()
    headers["Date"] = date
    headers["Content-Location"] = uri
    return headers


def server_error_headers() -> dict[str, any]:
    """Created header for server error message"""
    return generic_headers("/500_server_error.html")


def generic_headers(uri: str) -> dict[str, any]:
    """Create a success header"""
    date = current_date()
    media_type = map_media_type(uri)

    headers = dict()
    headers["Date"] = date
    headers["Content-Type"] = media_type

    return headers


def get_body(uri) -> bytes:
    return get_file_content(uri)


def status_code_body(number) -> bytes:
    """Create status code based body"""
    if number == 304:
        body = get_file_content("/304_not_modified.html")
    elif number == 400:
        body = get_file_content("/400_bad_request.html")
    elif number == 404:
        body = get_file_content("/404_not_found.html")
    elif number == 405:
        body = get_file_content("/405_method_not_allowed.html")
    else:
        body = get_file_content("/500_server_error.html")
    return body


def is_modified(uri: str, request_headers: dict[str, str]) -> bool:
    """Check whether the resource on a URI has been modified"""
    if 'If-Modified-Since' not in request_headers:
        logging.debug("If-Modified-Since header not present, continuing flow as if modified")
        return True
    modified_seconds = os.path.getmtime(map_uri(uri))
    file_modified = datetime.fromtimestamp(modified_seconds)
    if_modified_since = datetime.strptime(request_headers['If-Modified-Since'], "%a, %d %b %Y %H:%M:%S %Z")
    logging.debug(f"Requested resource {uri} was {'' if file_modified > if_modified_since else 'not'} modified")
    return file_modified > if_modified_since


def current_date() -> str:
    """Returns formatted current date"""
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(time.time()))


def get_size(uri: str) -> int:
    """Returns size of file"""
    return os.path.getsize(map_uri(uri))


def map_media_type(uri: str) -> str:
    """Map file to correct media type"""
    _, extension = os.path.splitext(uri)
    logging.debug(f"Found extension: {extension}")
    if extension == '.html':
        return 'text/html'
    if extension == '.jpg':
        return 'image/jpg'
    if extension == '.pdf':
        return 'text/pdf'


def is_found(uri: str) -> bool:
    """Check whether a file exists for the given uri"""
    if os.path.isfile(map_uri(uri)):
        logging.debug(f"Requested resource {uri} found")
        return True
    else:
        logging.debug(f"Requested resource {uri} not found")
        return False


def map_uri(uri: str) -> str:
    """Maps a URI to its server configured location"""
    return f"server_files{uri}"


def get_file_content(uri: str) -> bytes:
    fd = open(map_uri(uri), 'rb')
    return fd.read()


def validate_version(version: str) -> bool:
    """Validates version. Only HTTP/1.1 supported"""
    return "HTTP/1.1" == version


start_server()
