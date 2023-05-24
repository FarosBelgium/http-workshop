import sys


def read_and_validate_input_arguments() -> tuple:
    _, command, uri, port = sys.argv
    command = command.upper()
    if command not in {"HEAD", "GET", "PUT", "POST"}:
        print("No valid command given; GET is used by default.")
        command = "GET"

    if command in {"POST", "PUT"}:
        print("Please specify your body.")
        body = input()
    else:
        body = None

    if uri.startswith("http://"):
        uri = uri.split("http://")[1]

    try:
        server, path = uri.split("/")
        path = "/" + path
    except:
        server = uri
        path = "/"

    try:
        port = int(port)
    except:
        print("No valid port given; port 80 is used by default.")
        port = 80

    return command, server, path, port, body
