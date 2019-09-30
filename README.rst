=============================================
Welcome to cryptology-ws-client-python v1.1.5
=============================================

This is an official Python client library for the Cryptology exchange WebSocket API.

By using this Cryptology Python client you confirm that you have read and accept `License Agreement: <https://github.com/CryptologyExchange/cryptology-ws-client-python/blob/master/LICENSE>`_

Features
--------

- Asynchronous implementation of all WebSocket Market Data and Account endpoints.
- Handling response errors
- Withdrawal functionality

Quick Start
-----------
Receive your own API access key and secret key.

.. code:: bash

    pip install cryptology-ws-client

Run tests.

.. code:: bash

    make tests

And see example.

.. code:: python

    import asyncio
    import itertools
    import os
    import logging
    import time

    from collections import namedtuple
    from cryptology import ClientWriterStub, run_client, exceptions
    from datetime import datetime
    from decimal import Decimal
    from typing import Iterable, Dict, List

    SERVER = os.getenv('SERVER', 'wss://api.sandbox.cryptology.com')


    logging.basicConfig(level='DEBUG')


    async def main():

        async def writer(ws: ClientWriterStub, pairs: List, state: Dict) -> None:
            while True:
                client_order_id = int(time.time() * 10)
                await ws.send_message(payload={
                    '@type': 'PlaceBuyLimitOrder',
                    'trade_pair': 'BTC_USD',
                    'price': '1',
                    'amount': '1',
                    'client_order_id': client_order_id,
                    'ttl': 0
                })
                await asyncio.sleep(5)

        async def read_callback(ws: ClientWriterStub, ts: datetime, message_id: int, payload: dict) -> None:
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
                    last_seen_message_id=-1
                )
            except exceptions.ServerRestart:
                await asyncio.sleep(60)


    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())




For more `check out the documentation <https://github.com/CryptologyExchange/api>`_.
