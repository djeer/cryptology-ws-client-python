=====
Usage
=====

.. code-block:: python3

    import asyncio
    from datetime import datetime

    from cryptology import ClientWriterStub, run_client

    async def main() -> None:
        async def writer(ws: ClientWriterStub, state: Dict = None) -> None:
            client_order_id = 0
            while True:
                await asyncio.sleep(1)
                client_order_id += 1
                await ws.send_signed(
                    sequence_id=sequence_id,
                    payload={'@type': 'PlaceBuyLimitOrder',
                             'trade_pair': 'BTC_USD',
                             'amount': '2.3',
                             'price': '15000.1',
                             'client_order_id': 123 + client_order_id,
                             'ttl': 0
                            }
                )

        async def read_callback(ts: datetime, message_id: int, payload: dict) -> None:
            print(order, ts, message_id, payload)

        await run_client(
            access_key='YOUR ACCESS KEY',
            secret_key='YOUR SECRET KEY',
            ws_addr='wss://api.sandbox.cryptology.com',
            writer=writer,
            read_callback=read_callback,
            last_seen_message_id=-1
        )
