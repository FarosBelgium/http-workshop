import os
from abc import *

import clientproperties
from httprequestor import HttpRequestor, HttpGetResponse

# Represents a dictionary whereby for each tag an attribute-name is associated in which an image can be found
tag_with_attribute = {"img": "src", "link": "href", "meta": "content"}


class ImageRequestor:

    # Instantiates an ImageRequestor-object with given parser, tag and img_name.
    # In fact, this class should not be instantiated as this is considered to be abstract.
    # An image requestor does a request and handles the response for one single image.
    def __init__(self, parser, tag, img_name):
        self.parser = parser
        self.tag = tag
        self.img_name = img_name

    @abstractmethod
    def request(self):
        raise RuntimeError


class ImageRequestorSameServer(ImageRequestor):

    def __init__(self, parser, tag, img_name, http_requestor: HttpRequestor):
        super().__init__(parser, tag, img_name)
        self.http_requestor = http_requestor

    def request(self):
        # Specifies the local path of the image, so where it will be saved locally
        local_path = os.path.join(clientproperties.content_path,
                                  self.img_name[1:] if self.img_name[0] == "/" else self.img_name)
        local_path = local_path.replace("%20", " ")

        # Adds a '/' to the beginning of the path to prepare the request
        request_path = self.img_name if self.img_name[0] == "/" else "/" + self.img_name

        # Creates locally (if possible) the folder-structure of the image like on the server
        try:
            os.makedirs(os.path.dirname(local_path))
        except FileExistsError:
            pass

        # Executes the request and asks the raw body
        self.http_requestor.path = request_path
        http_response = self.http_requestor.request()
        assert isinstance(http_response, HttpGetResponse)
        img_data = http_response.raw_body

        # Writes the image to the file on the specified local path
        with open(local_path, "wb") as file:
            file.write(img_data)

        # Removes the '/' at the beginning of the attribute to make sure the image can be found locally
        attribute = tag_with_attribute[self.tag.name]
        self.tag[attribute] = request_path[1:]

        # Updates file.html with the right local attribute
        with open(os.path.join(clientproperties.content_path, "file.html"), "w") as file:
            file.write(str(self.parser))


class ImageRequestorExternalServer(ImageRequestor):

    def request(self):
        # Removes the protocol from the img name
        self.img_name = self.img_name.split("://")[1]

        # Separates the server and path name from the img name
        server, path = self.img_name.split("/", 1)

        # Creates a new HttpRequestor-object to execute the request and asks the raw body
        new_http_requestor = HttpRequestor(server=server, port=80, path=path, command="GET")
        http_response = new_http_requestor.request()
        assert isinstance(http_response, HttpGetResponse)
        img_data = http_response.raw_body

        # Creates a local img name
        self.img_name = self.img_name.split("/")[-1]

        # Updates file.html with the right local attribute
        with open(os.path.join(clientproperties.content_path, self.img_name), "wb") as file:
            file.write(img_data)

        # Removes the '/' at the beginning of the attribute to make sure the image can be found locally
        attribute = tag_with_attribute[self.tag.name]
        self.tag[attribute] = self.img_name

        # Updates file.html with the right local src-attribute
        with open(os.path.join(clientproperties.content_path, "file.html"), "w") as file:
            file.write(str(self.parser))
