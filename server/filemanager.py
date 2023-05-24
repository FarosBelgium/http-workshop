import os

import serverproperties


class FileManager:

    # Instantiates a FileManager-object with given file path
    def __init__(self, file_path: str):
        if file_path == "/":
            file_path = "/index.html"

        if not file_path.startswith("/"):
            file_path = "/" + file_path

        self.file_path = file_path

    def path_exists(self):
        return os.path.exists(self.file_path_on_server)

    @property
    def size(self):
        return os.stat(self.file_path_on_server).st_size

    # Returns the exact path to a file on the server
    @property
    def file_path_on_server(self):
        return os.path.join(serverproperties.content_path, self.file_path[1:])

    # Reads the content of a specific file and returns its binary data. If no path is given, file_path
    # (instance variable) will be used
    def read_file(self, path=None) -> bytes:
        if path is None:
            path = self.file_path_on_server
        with open(path, "rb") as file:
            body = file.read()
        return body

    # Appends a given text to a given file. If no path is given, file_path (instance variable) will be used.
    def append_text_to_file(self, text: str, path=None):
        if path is None:
            path = self.file_path_on_server
        with open(path, "a") as file:
            file.write(text.rstrip())

    # Writes a given text to a given file. If no path is given, file_path (instance variable) will be used.
    # If the given file already exists, it will be overridden.
    def write_text_to_file(self, text: str, path=None):
        if path is None:
            path = self.file_path_on_server
        with open(path, "w") as file:
            file.write(text.rstrip())
