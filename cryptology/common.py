import json
import logging
from datetime import timedelta
from enum import Enum, unique
from typing import Any, Optional

import aiohttp

from . import exceptions


logger = logging.getLogger(__name__)


HEARTBEAT_INTERVAL = timedelta(seconds=2)

CLOSE_MESSAGES = (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING,
                  aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR,)


class ByValue(Enum):
    @classmethod
    def by_value(cls, value: int) -> Any:
        for val in cls:
            if val.value == value:
                return val
        raise IndexError(value)


@unique
class ClientMessageType(ByValue):
    INBOX_MESSAGE = 1
    RPC_REQUEST = 2


@unique
class ServerMessageType(ByValue):
    MESSAGE = 1
    ERROR = 2
    BROADCAST = 3
    THROTTLING = 4


class ServerErrorType(ByValue):
    UNKNOWN_ERROR = -1
    DUPLICATE_CLIENT_ORDER_ID = 1
    INVALID_PAYLOAD = 2
    PERMISSION_DENIED = 3


async def receive_msg(ws: aiohttp.ClientWebSocketResponse, *, timeout: Optional[float] = None) -> dict:
    msg = await ws.receive(timeout=timeout)
    if msg.type in CLOSE_MESSAGES:
        logger.info('close msg received (type %s): %s', msg.type.name, msg.data)
        exceptions.handle_close_message(msg)
        raise exceptions.UnsupportedMessage(msg)

    return json.loads(msg.data)
