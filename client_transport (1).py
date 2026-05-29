# client_transport.py
# pip install websockets

import asyncio
import websockets
import json
import threading

class GameClient:

    def __init__(self, uri="ws://localhost:8765", response_handler=None):
        self.uri = uri
        self.response_handler = response_handler
        self.websocket = None
        self.loop = asyncio.new_event_loop()
        self.thread = None

    async def _connect(self):
        self.websocket = await websockets.connect(self.uri)
        self.loop.create_task(self._listen())

    async def _send(self, data):
        if self.websocket:
            await self.websocket.send(json.dumps(data))

    async def _receive(self):
        response = await self.websocket.recv()
        return json.loads(response)

    async def _close(self):
        if self.websocket:
            await self.websocket.close()
        self.loop.stop()

    async def _listen(self):
        try:
            while True:
                response = await self._receive()
                if self.response_handler:
                    self.response_handler(response)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server.")

    def connect(self):
        self.thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True
        )

        self.thread.start()

        future = asyncio.run_coroutine_threadsafe(
            self._connect(),
            self.loop
        )

        return future.result()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def send_action(self, action, **kwargs):
        message = {"action": action}
        message.update(kwargs)

        asyncio.run_coroutine_threadsafe(
            self._send(message),
            self.loop
        )

    def close(self):
        if self.loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._close(),
                self.loop
            )

        if self.thread:
            self.thread.join(timeout=1)