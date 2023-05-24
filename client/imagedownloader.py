import validators
from bs4 import BeautifulSoup

from imagerequestor import *


class ImageDownloader:

    # Instantiates an ImageDownloader-object with given body and http requestor
    def __init__(self, body: str, http_requestor: HttpRequestor):
        self.parser = BeautifulSoup(body, "html.parser")
        self.http_requestor = http_requestor

    # Returns the image name that is included in the given tag. If the given tag does not include an image,
    # None will be returned.
    def __get_image_name_from_tag(self, tag):
        attribute = tag_with_attribute[tag.name]
        if attribute in tag.attrs:
            image_name: str = tag[attribute]
            image_extensions = {"jpg", "jpeg", "png", "gif"}
            for extension in image_extensions:
                if image_name.endswith(extension):
                    return image_name
        return None

    # Downloads all the images on the html body
    def download(self):
        img_tags = self.parser.find_all("img")
        link_tags = self.parser.find_all("link")
        meta_tags = self.parser.find_all("meta")
        tags = img_tags + link_tags + meta_tags

        # Iterates over every tag
        for tag in tags:
            img_name = self.__get_image_name_from_tag(tag)

            # If no img name is found, this tag will be skipped
            if img_name is None:
                continue

            # If the img name is a URL of an external server, an ImageRequestorExternalServer-object will be created for
            # handling the request. Otherwise, an ImageRequestorSameServer-object will be created.
            if validators.url(img_name):
                image_requestor = ImageRequestorExternalServer(self.parser, tag, img_name)
            else:
                image_requestor = ImageRequestorSameServer(self.parser, tag, img_name, self.http_requestor)

            # Executes the request
            image_requestor.request()
