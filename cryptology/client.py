import aiohttp
import asyncio
import functools
import inspect
import logging

from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, ClassVar, Optional, Tuple, Type, cast, Dict, List

from . import common, exceptions, parallel


__all__ = ('ClientReadCallback', 'ClientWriter', 'ClientWriterStub', 'run_client',)

logger = logging.getLogger(__name__)


CLIENTWEBSOCKETRESPONSE_INIT_ARGS = list(
    inspect.signature(aiohttp.ClientWebSocketResponse.__init__).parameters.keys())[1:]


class ClientWriterStub:
    async def send_message(self, *, payload: dict) -> None:
        pass


ClientReadCallback = Callable[[ClientWriterStub, datetime, int, dict], Awaitable[None]]
ClientWriter = Callable[[ClientWriterStub, List[str], Optional[Dict]], Awaitable[None]]
ClientThrottlingCallback = Callable[[int, int], Awaitable[bool]]


class BaseProtocolClient(aiohttp.ClientWebSocketResponse):
    VERSION: ClassVar[int] = 7

    access_key: ClassVar[str]
    secret_key: ClassVar[str]

    sequence_id: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kw = {}
        kw.update(dict(zip(CLIENTWEBSOCKETRESPONSE_INIT_ARGS, args)))
        kw.update(kwargs)
        super(BaseProtocolClient, self).__init__(**kw)
        self.send_fut = None
        self.throttle = 0

    async def authenticate(self, last_seen_message_id: int, get_balances: bool = False,
                           get_order_books: bool = False) -> Tuple[int, int, Dict, List[str]]:
        state_request_data = {}
        if get_balances:
            state_request_data['get_balances'] = get_balances
        if get_order_books:
            state_request_data['get_order_books'] = get_order_books

        await self.send_json({'access_key': self.access_key,
                              'secret_key': self.secret_key,
                              'last_seen_message_id': last_seen_message_id,
                              'version': self.VERSION,
                              **state_request_data})
        data = await common.receive_msg(self)
        try:
            if data['greeting'] != 'Welcome to Cryptology API Server':
                raise exceptions.InvalidServerAddress()
            last_seen_sequence = data['last_seen_sequence']
            server_version = data['version']
            state = data.get('state')
            pairs = data['trade_pairs']
        except (KeyError, TypeError):
            raise exceptions.InvalidServerAddress()
        self.sequence_id = last_seen_sequence
        return last_seen_sequence, server_version, state, pairs

    async def send_message(self, *, payload: dict) -> None:
        if self.closed:
            logger.warning('the socket is closed')
            raise exceptions.CryptologyConnectionError()

        self.sequence_id += 1
        sequence_id = self.sequence_id
        data = {'sequence_id': sequence_id,
                'data': payload}
        if self.send_fut:
            await self.send_fut
        if self.throttle:
            logger.warning('throttle for %f seconds', self.throttle)
            throttle, self.throttle = self.throttle, 0
            await asyncio.sleep(throttle)
        logger.debug('sending message with seq id %i: %s', sequence_id, payload)
        self.send_fut = asyncio.ensure_future(self.send_json(data))

    async def receive_iter(self, throttling_callback: ClientThrottlingCallback) -> AsyncIterator[Tuple[datetime, dict]]:
        while True:
            data = await common.receive_msg(self)

            message_type: common.ServerMessageType = common.ServerMessageType[data['response_type']]
            logger.debug('message %s received', message_type)
            if message_type is common.ServerMessageType.THROTTLING:
                level = data['overflow_level']
                sequence_id = data['sequence_id']
                if not throttling_callback or not await throttling_callback(level, sequence_id):
                    self.throttle = 0.001 * level
            elif message_type is common.ServerMessageType.MESSAGE:
                ts = data['timestamp']
                logger.debug('outbox message: %s', data['data'])
                yield datetime.utcfromtimestamp(ts), data['message_id'], data['data']
            else:
                logger.error('unsupported message type')
                raise exceptions.UnsupportedMessageType()

    def _pong_not_received(self):
        logger.warning('missed heartbeat from the server. connection will be closed')
        super()._pong_not_received()


@functools.lru_cache(typed=True)
def bind_response_class(access_key: str, secret_key: str) -> Type[BaseProtocolClient]:
    return cast(Type[BaseProtocolClient],
                type('BoundProtocolClient', (BaseProtocolClient,),
                     {'access_key': access_key, 'secret_key': secret_key}))


class CryptologyClientSession(aiohttp.ClientSession):
    def __init__(self, access_key: str, secret_key: str, *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(ws_response_class=bind_response_class(access_key, secret_key), loop=loop, conn_timeout=10)


async def run_client(*, access_key: str, secret_key: str, ws_addr: str,
                     read_callback: ClientReadCallback, writer: ClientWriter,
                     throttling_callback: ClientThrottlingCallback = None,
                     last_seen_message_id: int = 0,
                     loop: Optional[asyncio.AbstractEventLoop] = None,
                     get_balances: bool = False,
                     get_order_books: bool = False,
                     error_callback: Any = None) -> None:
    if error_callback:
        logger.warning('error_callback is deprecated')
    async with CryptologyClientSession(access_key, secret_key, loop=loop) as session:
        async with session.ws_connect(ws_addr, autoclose=True, autoping=True, receive_timeout=10, heartbeat=4) as ws:
            logger.info('connected to the server %s', ws_addr)
            sequence_id, server_version, state, pairs = await ws.authenticate(last_seen_message_id,
                                                                              get_balances,
                                                                              get_order_books)
            logger.info('Authentication succeeded, server version %i, sequence id = %i', server_version, sequence_id)
            if server_version < 6:
                raise exceptions.IncompatibleVersion('Server version less than 6 is not supported')

            async def reader_loop() -> None:
                async for ts, message_id, msg in ws.receive_iter(throttling_callback):
                    logger.debug('%s new msg from server @%i: %s', ts, message_id, msg)
                    asyncio.ensure_future(read_callback(ws, ts, message_id, msg))

            await parallel.run_parallel((
                reader_loop(),
                writer(ws, pairs, state)
            ), loop=loop)
