import aiohttp
import asyncio
import logging
from typing import Optional, Callable, Awaitable, List
import urllib
from urllib.parse import urlencode
from multidict import MultiDict


from . import exceptions, common
from datetime import datetime
from decimal import Decimal

__all__ = ('run',)


logger = logging.getLogger(__name__)


MarketDataCallback = Callable[[dict], Awaitable[None]]
OrderBookCallback = Callable[[int, str, dict, dict], Awaitable[None]]
TradesCallback = Callable[[datetime, int, str, Decimal, Decimal], Awaitable[None]]


async def reader_loop(
        ws: aiohttp.ClientWebSocketResponse,
        market_data_callback: MarketDataCallback,
        order_book_callback: OrderBookCallback,
        trades_callback: TradesCallback) -> None:
    logger.info(f'broadcast connection established')
    while True:
        msg = await common.receive_msg(ws)

        try:
            message_type: common.ServerMessageType = common.ServerMessageType[msg['response_type']]
            if message_type != common.ServerMessageType.BROADCAST:
                raise exceptions.UnsupportedMessageType()
            payload = msg['data']
            if market_data_callback is not None:
                await market_data_callback(payload)
            if payload['@type'] == 'OrderBookAgg':
                if order_book_callback is not None:
                    asyncio.ensure_future(order_book_callback(
                        payload['current_order_id'],
                        payload['trade_pair'],
                        payload.get('buy_levels', dict),
                        payload.get('sell_levels', dict)
                    ))
            elif payload['@type'] == 'AnonymousTrade':
                if trades_callback is not None:
                    asyncio.ensure_future(trades_callback(
                        datetime.utcfromtimestamp(payload['time'][0]),
                        payload['current_order_id'],
                        payload['trade_pair'],
                        Decimal(payload['amount']),
                        Decimal(payload['price'])
                    ))
            else:
                raise exceptions.UnsupportedMessageType()
        except (KeyError, ValueError, exceptions.UnsupportedMessageType):
            logger.exception('failed to decode data')
            raise exceptions.CryptologyError('failed to decode data')


async def run(*, ws_addr: str, market_data_callback: MarketDataCallback = None,
              order_book_callback: OrderBookCallback = None,
              trades_callback: TradesCallback = None,
              trade_pairs: List[str] = None,
              loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    url = ws_addr
    if trade_pairs:
        params = MultiDict()
        for trade_pair in trade_pairs:
            params.add('trade_pair', trade_pair)
        url = '{}?{}'.format(url, urlencode(params))
    async with aiohttp.ClientSession(loop=loop) as session:
        async with session.ws_connect(url, receive_timeout=20, heartbeat=8) as ws:
            await reader_loop(ws, market_data_callback, order_book_callback, trades_callback)
