import logging
import re
import signal
import socket

from http_commons import nlc, to_bytes

max_buffer_size = 1024

logging.basicConfig(level=logging.DEBUG)

bnlc = nlc.encode()


def request_input(sock: socket.socket, uri: str):
    http_method = str(input("Enter HTTP method (HEAD, GET, PUT, POST):"))
    path = str(input("Enter path:"))
    if http_method == 'PUT' or http_method == 'POST':
        body = str(input("Enter body:"))
    else:
        body = None

    request = create_request(http_method, uri, path, body)
    logging.debug(request)
    send_request(sock, request)
    receive_response(sock, http_method)


def start_client():
    uri = str(input("Enter URL/IP:"))
    ip = socket.gethostbyname(uri)

    port = input("Enter port (or empty for 80):")
    if port:
        port = int(port)
    else:
        port = 80
    s = make_connection(ip, port)

    def interrupt_handler(signum, frame):
        logging.debug("Interrupt signal received")
        s.close()
        logging.debug("Server socket closed")
        exit(1)

    signal.signal(signal.SIGINT, interrupt_handler)

    while True:
        request_input(s, uri)


def split_uri(uri: str) -> (str, str):
    if uri.startswith("http://"):
        uri = uri[7:]
    uri_parts = uri.split("/", 1)
    uri = uri_parts[0]
    if len(uri_parts) > 1:
        path = "/" + uri_parts[1]
    else:
        path = "/"
    return uri, path


def make_connection(uri: str, port: int) -> socket:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logging.debug("Socket successfully created")
    except socket.error as err:
        logging.debug("socket creation failed with error %s" % err)
        return
    # connecting to the server
    s.connect((uri, port))  # host_ip
    logging.debug(f"The socket has successfully connected to {uri}:{port}.")
    return s


def create_request_line(command: str, path: str) -> str:
    return f"{command} {path} HTTP/1.1"


def create_generic_headers(uri: str) -> dict[str, str]:
    headers = dict()
    headers["Host"] = uri
    return headers


def create_head_headers(uri: str) -> dict[str, str]:
    headers = create_generic_headers(uri)
    return headers


def read_body_from_terminal() -> str:
    data = ""
    while True:
        terminal_in = str(input())
        if terminal_in == "":
            break
        data += terminal_in
    return data


def create_put_post_headers(uri: str, body: bytes) -> dict[str, str]:
    headers = create_generic_headers(uri)
    headers["Content-Length"] = str(len(body))
    return headers


def create_request(http_command: str, uri: str, path: str, body: bytes | None) -> bytes:
    request_line = create_request_line(http_command, path)
    if http_command == "HEAD":
        headers = create_head_headers(uri)
    elif http_command == "GET":
        headers = create_head_headers(uri)
    elif http_command == "PUT":
        headers = create_put_post_headers(uri, body)
    elif http_command == "POST":
        headers = create_put_post_headers(uri, body)
    else:
        raise Exception("Error - unsupported method")

    request = request_line + nlc
    for key in headers:
        request += f"{key}: {headers[key]}" + nlc
    request += nlc
    request = to_bytes(request)
    if body:
        request += body
    return request


def send_request(sock: socket.socket, request: bytes):
    sock.sendall(request)


def extract_response_line(response: bytes) -> (str, str, str, bytes):
    """Extract and split response line from request"""
    first_line_end = response.find(bnlc)
    first_line = response[:first_line_end]
    first = first_line.split(b" ")
    version = first[0].decode()
    status_code = first[1].decode()
    reason_phrase = first[2].decode()
    return version, status_code, reason_phrase, response[first_line_end + 2:]


def read_header_response(sock: socket, response: bytes):
    while not response.endswith(bnlc + bnlc):
        """until two newlines are received (signifying the end of the HTTP response) 
        we keep pulling data from the socket"""
        logging.debug("Response didn't end with 2 newline characters, receiving more data.")
        data = sock.recv(max_buffer_size)
        response += data
    print(response)


def read_content_length_response(sock: socket, response: bytes, remainder: bytes, headers: dict[bytes, bytes]):
    logging.debug("Fetching data until all is received according to Content-Length header")
    content_length = headers[b"Content-Length"]
    while len(remainder) != int(content_length):
        data = sock.recv(max_buffer_size)
        response += data
        remainder += data
    encoding = extract_encoding(headers)
    print(response.decode(encoding))


def read_chunked_response(sock: socket, response: bytes, remainder: bytes, headers: dict[bytes, bytes]):
    logging.debug("Fetching data until all is received according to chunking")
    while True:
        split = remainder.split(bnlc, 1)
        line = split[0]
        chunk_length = int(line, base=16)
        if chunk_length == 0:
            break
        remainder = split[1]
        rem_length = len(remainder)
        if rem_length > chunk_length:
            remainder = remainder[chunk_length + 2:]
        elif rem_length <= chunk_length:
            while rem_length < chunk_length:
                data = sock.recv(max_buffer_size)
                response += data
                remainder += data
                rem_length = len(remainder)
            remainder = remainder[chunk_length + 2:]
    encoding = extract_encoding(headers)
    print(response.decode(encoding))


def receive_response(sock: socket, method: str):
    response = sock.recv(max_buffer_size)
    if not response:
        logging.debug("No data received from socket, indicating connection was closed from server side")
        return
    elif response:
        version, status_code, reason_phrase, remainder = extract_response_line(response)
        if method == "HEAD" or status_code != "200":
            read_header_response(sock, response)
        else:
            headers, remainder = extract_headers(remainder)
            if b"Content-Length" in headers:
                read_content_length_response(sock, response, remainder, headers)
            elif b"Transfer-Encoding" in headers and headers[b"Transfer-Encoding"] == b"chunked":
                read_chunked_response(sock, response, remainder, headers)
            else:
                raise Exception


def extract_encoding(headers: dict[bytes, bytes]) -> str:
    if b"Content-Type" in headers and b"charset=" in headers[b"Content-Type"]:
        charset_match = re.findall(rb"charset=(\S+)", headers[b"Content-Type"])
        if len(charset_match) > 0:
            return charset_match[0].decode('utf-8')
    return 'utf-8'


def extract_headers(response: bytes) -> (dict[bytes, bytes], bytes):
    """Split headers and return as dictionary"""
    split = response.split(bnlc + bnlc, 1)
    header_block = split[0]
    body = split[1]
    headers = {}
    header_match = re.findall(rb"(\S+): ([\S ]+)", header_block)
    for name, value in header_match:
        headers[name] = value
    return headers, body


# start_client()


def test():
    uri = 'www.google.com'
    port = 80
    method = 'GET'
    path = '/'
    body = None
    ip = socket.gethostbyname(uri)

    s = make_connection(ip, port)
    request = create_request(method, uri, path, body)
    logging.debug(request)
    send_request(s, request)
    receive_response(s, method)


test()
