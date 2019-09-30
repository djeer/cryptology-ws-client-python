import asyncio
import os
import logging

from cryptology import ClientWriterStub, run_client, exceptions
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

SERVER = os.getenv('SERVER', 'wss://api.sandbox.cryptology.com')

logging.basicConfig(level='INFO')
logger = logging.getLogger(__name__)


ACCESS_KEY = 'YOUR ACCESS KEY'
SECRET_KEY = 'YOUR SECRET KEY'


TRADE_PAIR = 'CTX_BTC'
COIN_PRICE = 0.15
SPREAD = 1  # percent
BASE_CURRENCY, QUOTED_CURRENCY = TRADE_PAIR.split('_')


def read_last_seen_message_id() -> int:
    file_path = os.path.join('.', 'last_seen_message_id')
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return int(f.read())
    else:
        return -1


def write_last_seen_message_id(last_seen_message_id: int) -> None:
    file_path = os.path.join('.', 'last_seen_message_id')
    with open(file_path, 'w') as f:
        f.write(str(last_seen_message_id))


def round_decimal(number: Decimal, precision: int = 8):
    return number.quantize(Decimal(10) ** -precision).normalize()


async def main():
    balances = {}

    async def create_bid(ws: ClientWriterStub):
        second_currency_balance = Decimal(balances[QUOTED_CURRENCY]['available'])
        assert second_currency_balance, 'Account has insufficient funds for {}'.format(QUOTED_CURRENCY)
        bid_price = round_decimal(Decimal(COIN_PRICE * (100 - SPREAD / 2) / 100))

        can_buy = second_currency_balance / bid_price
        bid_amount = round_decimal(Decimal(can_buy / 3))

        await ws.send_message(payload={
            '@type': 'PlaceBuyLimitOrder',
            'trade_pair': TRADE_PAIR,
            'price': str(bid_price),
            'amount': str(bid_amount)
        })

    async def create_ask(ws: ClientWriterStub):
        base_currency_balance = Decimal(balances[BASE_CURRENCY]['available'])
        assert base_currency_balance, 'Account has insufficient funds for {}'.format(BASE_CURRENCY)
        ask_price = round_decimal(Decimal(COIN_PRICE * (100 + SPREAD / 2) / 100))

        ask_amount = round_decimal(Decimal(base_currency_balance / 3))

        await ws.send_message(payload={
            '@type': 'PlaceSellLimitOrder',
            'trade_pair': TRADE_PAIR,
            'price': str(ask_price),
            'amount': str(ask_amount)
        })

    async def writer(ws: ClientWriterStub, pairs: List, state: Dict) -> None:
        balances.update(state['balances'])

        await create_bid(ws)
        await create_ask(ws)
        while True:
            await asyncio.sleep(5)

    async def read_callback(ws: ClientWriterStub, ts: datetime, message_id: int, payload: dict) -> None:
        write_last_seen_message_id(message_id)

        if payload['@type'] == 'BuyOrderClosed':
            logger.info('Buy order %i closed', payload['order_id'])
            await create_bid(ws)
        elif payload['@type'] == 'SellOrderClosed':
            logger.info('Sell order %i closed', payload['order_id'])
            await create_ask(ws)
        elif payload['@type'] == 'SetBalance':
            balances.setdefault(payload['currency'], {'available': 0})
            balances[payload['currency']]['available'] = payload['balance']
        elif payload['@type'] == 'BuyOrderPlaced':
            logger.info('Buy order with id %i, amount %s and price %s is placed',
                        payload['order_id'], payload['amount'], payload['price'])
        elif payload['@type'] == 'SellOrderPlaced':
            logger.info('Sell order with id %i, amount %s and price %s is placed',
                        payload['order_id'], payload['amount'], payload['price'])

    try:
        await run_client(
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            ws_addr=SERVER,
            writer=writer,
            read_callback=read_callback,
            last_seen_message_id=read_last_seen_message_id(),
            get_balances=True
        )
    except exceptions.ServerRestart:
        await asyncio.sleep(60)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
