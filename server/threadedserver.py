import socket
import threading
import uuid

import select

from httprequest import *
from httpresponse import *


class ThreadedServer:

    # Instantiates a ThreadedServer-object with given hostname and port. If no host and/or port is given, the values
    # from the server-properties file will be used.
    def __init__(self, host: str = serverproperties.ip_address, port: int = serverproperties.port):
        self.threads = {}
        self.host = host
        self.port = port
        self.terminate = False
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.address)
        print("[SERVER UP]")

    @property
    def address(self) -> tuple:
        return self.host, self.port

    def __create_new_thread(self, connection, client_address):
        # Creates a new thread
        thread_id = uuid.uuid1()
        thread = threading.Thread(target=self.serve_client, args=(connection, client_address, thread_id))
        self.threads[thread_id] = thread

        # Starts the new thread
        thread.start()
        print(f"[THREAD STARTED] {client_address}")

    # Listens to the incoming client requests
    def listen(self):
        self.server.listen()
        while True:
            try:
                readable, _, _ = select.select([self.server], [], [], serverproperties.timeout)
                if self.server in readable:
                    connection, client_address = self.server.accept()
                    connection.settimeout(serverproperties.timeout)
                    self.__create_new_thread(connection, client_address)
            except KeyboardInterrupt:
                self.__shutdown()
                break

    def __shutdown(self):
        self.terminate = True
        nr_threads_running = len(self.threads)
        print(f"[INFO] There are currently {nr_threads_running} unfinished threads")
        print("[INFO] Waiting for unfinished threads before shutdown")
        for _, thread in list(self.threads.items()):
            thread.join()
        print("[SERVER DOWN]")

    def __read_message(self, connection):
        final_message = ""
        while True:
            # Gets message from connection.recv(...) If there is a time-out, None will be returned
            try:
                message: str = connection.recv(1024).decode(serverproperties.encoding)
                if not message:
                    return None
            except TimeoutError:
                return None

            # Adds message to the final message
            final_message += message

            # If the final message contains '\r\n\r\n', a body should be asked in case of a PUT or POST request
            # if it was not added yet. In all other cases, the final message is returned.
            if "\r\n\r\n" in final_message:
                if ("PUT" in final_message or "POST" in final_message) and final_message.endswith("\r\n\r\n"):
                    continue
                else:
                    return final_message.rstrip()

    def __generate_http_response(self, message: str) -> HttpResponse:

        close_connection = False

        # Creates a HttpRequest-object to parse the client message
        try:
            http_request: HttpRequest = parse_http_request(message)
            # If the headers in the request specify to close the connection after the current handling,
            # the current connection will be closed afterwards
            if "Connection" in http_request.headers and http_request.headers["Connection"] == "close":
                close_connection = True
        except:
            # If something wrong occurs during parsing the http request, a 400 status will be returned
            return create_http_response(400, close_connection)

        # If the http request headers don't contain a 'Host' field, a 400 status will be returned
        if "Host" not in http_request.headers:
            return create_http_response(400, close_connection, http_request)

        # Creates a FileManager-object given a file path
        file_manager = FileManager(http_request.file_path)

        # If the FileManager-object detects that the path does not exist, a 404 status will be returned
        if not file_manager.path_exists() and http_request.command != "POST":
            return create_http_response(404, close_connection, http_request)

        # Asks for a http response
        try:
            http_response = create_http_response(200, close_connection, http_request, file_manager)
            if "If-Modified-Since" in http_request.headers:
                if_modified_date = http_request.headers["If-Modified-Since"].rstrip()

                # If the requested file is not modified since the given date in the http request headers,
                # then no body will be returned and the returned status code is 304
                if HttpDate.is_after(if_modified_date, http_response.last_modified):
                    http_response = create_http_response(304, close_connection, http_request)

            return http_response

        except:
            # If something wrong occurs during creating the http response, a 500 status will be returned
            return create_http_response(500, close_connection, http_request)

    # Serves a specific client in a separate thread
    def serve_client(self, connection, client_address, thread_id):
        while True:
            # Reads the incoming message from the client
            message = self.__read_message(connection)

            # If the message is empty or None, the current loop will be broken to close the connection
            if not message:
                break

            http_response: HttpResponse = self.__generate_http_response(message)

            # If everything is right, the raw http response is sent back to the client
            connection.send(http_response.__repr__())

            # If the http response asks for closing the current connection, the current loop will be broken
            if http_response.close_connection:
                break

            if self.terminate:
                break

        # If the loop is broken, the connection will be closed and the current thread will be terminated
        connection.close()
        self.threads.pop(thread_id)
        print(f"[THREAD CLOSED] {client_address}")
