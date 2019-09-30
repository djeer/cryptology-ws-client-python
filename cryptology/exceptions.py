import aiohttp
from . import common


class CryptologyError(Exception):
    pass


class CryptologyProtocolError(CryptologyError):
    pass


class InvalidServerAddress(CryptologyProtocolError):
    pass


class IncompatibleVersion(CryptologyProtocolError):
    pass


class InvalidKey(CryptologyProtocolError):
    pass


class InvalidSequence(CryptologyProtocolError):
    pass


class UnsupportedMessage(CryptologyProtocolError):
    msg: aiohttp.WSMessage

    def __init__(self, msg: aiohttp.WSMessage) -> None:
        super(CryptologyProtocolError, self).__init__(f'unsupported message {msg!r}')
        self.msg = msg


class UnsupportedMessageType(CryptologyProtocolError):
    pass


class CryptologyConnectionError(CryptologyError):
    pass


class Disconnected(CryptologyConnectionError):
    def __init__(self, code: int, message: str) -> None:
        if message:
            super().__init__(f'disconnected with code {code} and message "{message}"')
        else:
            super().__init__(f'disconnected with code {code}')


class ConcurrentConnection(CryptologyConnectionError):
    pass


class ServerRestart(CryptologyConnectionError):
    pass


class RateLimit(CryptologyError):
    pass


class InvalidPayloadError(CryptologyProtocolError):
    pass


class PermissionDeniedError(CryptologyError):
    pass


class DuplicateClientOrderIdError(CryptologyProtocolError):
    pass


def handle_close_message(msg: aiohttp.WSMessage) -> None:
    if msg.type in common.CLOSE_MESSAGES:
        if msg.type == aiohttp.WSMsgType.CLOSE:
            if msg.data == 4000:
                raise ConcurrentConnection()
            elif msg.data == 4001:
                raise InvalidSequence()
            elif msg.data == 4009:
                raise RateLimit()
            elif msg.data == 1012:
                raise ServerRestart()
            elif msg.data == 4100:
                raise InvalidKey()
            elif msg.data == 4102:
                raise PermissionDeniedError(msg.extra)
            elif msg.data == 4103:
                raise IncompatibleVersion(msg.extra)
            elif msg.data == 4010:
                raise InvalidPayloadError(msg.extra)
            elif msg.data == 4013:
                raise PermissionDeniedError(msg.extra)
            elif msg.data == 4014:
                raise DuplicateClientOrderIdError(msg.extra)
        raise Disconnected(msg.data, msg.extra)
