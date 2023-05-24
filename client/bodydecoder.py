from abc import *


class BodyDecoder:

    # Instantiates a BodyDecoder-object given raw body and charset
    def __init__(self, body: bytes, charset: str):
        self.body = body
        self.charset = charset

    @abstractmethod
    def decode(self) -> str:
        raise RuntimeError


class BodyDecoderContentLength(BodyDecoder):

    # Decodes the body given a specific charset (instance variable)
    def decode(self) -> str:
        return self.body.decode(self.charset)


class BodyDecoderTransferEncodingChunked(BodyDecoder):

    # Decodes a chunked body given a specific charset (instance variable)
    def decode(self) -> str:
        split_body = self.body.split(b'\r\n')
        result = ""
        charset = self.charset

        for i in range(1, len(split_body), 2):
            line = split_body[i]
            line = line.decode(charset)
            result += line

        return result


# Creates a suitable instance of a subclass of a BodyDecoder-object given the request headers, a raw body and a charset
def create_body_decoder(headers: dict, body: bytes, charset: str) -> BodyDecoder:
    if "Content-Length" in headers:
        return BodyDecoderContentLength(body, charset)

    elif "Transfer-Encoding" in headers and headers["Transfer-Encoding"] == "chunked":
        return BodyDecoderTransferEncodingChunked(body, charset)
