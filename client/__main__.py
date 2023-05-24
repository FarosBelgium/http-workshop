import os
import shutil
import sys

from inputreader import read_and_validate_input_arguments
from httprequestor import HttpRequestor
from httpresponse import *
from imagedownloader import ImageDownloader

if __name__ == "__main__":

    # Reads the input arguments
    try:
        command, server, path, port, body = read_and_validate_input_arguments()
    except:
        print("Bad input, try again.")
        sys.exit()

    # Removes all the files and directories of the previous request
    folder = clientproperties.content_path
    for filename in os.listdir(folder):
        if filename == ".gittouch":
            continue
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)

    # Creates a HttpRequestor-object that executes the request and receives a HttpResponse-object
    http_requestor = HttpRequestor(command=command, server=server, path=path, port=port, body=body)
    http_response: HttpResponse = http_requestor.request()

    # If the response is a HttpGetResponse-instance
    if isinstance(http_response, HttpGetResponse):
        # Gets the textual representation of the http response
        body = repr(http_response)

        # Writes the body of the response to a file
        with open(os.path.join(clientproperties.content_path, "file.html"), "w") as file:
            file.write(body)

        # Creates an ImageDownloader-object that downloads all the images on the given html-page (body)
        image_downloader = ImageDownloader(body, http_requestor)
        image_downloader.download()
