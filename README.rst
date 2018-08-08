========================================
Welcome to cryptology-client-python v1.0
========================================

This is an official Python client library for the Cryptology exchange WebSocket API.

By using this Cryptology Python client you confirm that you have read and accept [License Agreement](https://github.com/CryptologyExchange/cryptology-client-python/blob/master/LICENSE)

Features
--------

- Asynchronous implementation of all WebSocket Market Data and Account endpoints.
- Handling response errors
- Withdrawal functionality

Quick Start
-----------
Receive your own API public/secret keys pair.

.. code:: bash

    pip install cryptology-client-python

Run tests.

.. code:: bash

    make tests

And see example.

.. code:: python

    import asyncio
    import itertools
    import os

    from collections import namedtuple
    from cryptology import ClientWriterStub, run_client, exceptions
    from datetime import datetime
    from decimal import Decimal
    from typing import Iterable

    SERVER = os.getenv('SERVER', 'ws://127.0.0.1:8080')
    Order = namedtuple('Order', ('order_id', 'amount', 'price', 'client_order_id'))


    def iter_orders(payload: dict) -> Iterable[Order]:
        for book in payload['order_books'].values():
            for order in itertools.chain(book['buy'], book['sell']):
                yield Order(
                    order_id=order['order_id'],
                    amount=Decimal(order['amount']),
                    price=Decimal(order['price']),
                    client_order_id=order['client_order_id']
                )


    async def main():

        async def writer(ws: ClientWriterStub) -> None:
            client_order_id = 0
            while True:
                await ws.send_message(payload={
                    '@type': 'PlaceBuyLimitOrder',
                    'trade_pair': 'BTC_USD',
                    'price': '1',
                    'amount': '1',
                    'client_order_id': client_order_id,
                    'ttl': 0
                })
                await asyncio.sleep(1)

        async def read_callback(ws: ClientWriterStub, ts: datetime, payload: dict) -> None:
            if payload['@type'] == 'BuyOrderPlaced':
                await ws.send_message(payload={'@type': 'CancelOrder', 'order_id': payload['order_id']})

        while True:
            try:
                await run_client(
                    access_key='YOUR ACCESS KEY',
                    secret_key='YOUR SECRET KEY',
                    ws_addr=SERVER,
                    writer=writer,
                    read_callback=read_callback,
                    last_seen_order=0
                )
            except exceptions.ServerRestart:
                asyncio.sleep(60)


    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())



For more `check out the documentation <https://client-python.docs.cryptology.com/>`_.
