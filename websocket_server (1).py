# websocket_server.py

import asyncio
import uuid
import websockets
import json

from server_adapter import handle_request

connected_players = {}  # websocket -> player_id


async def handler(websocket):
    connected_players[websocket] = None

    try:
        while True:
            try:
                message = await websocket.recv()
                request = json.loads(message)

                # JOIN
                if request.get("action") == "join":
                    pid = str(uuid.uuid4())[:8]
                    connected_players[websocket] = pid
                    request["player_id"] = pid

                # YA TIENE ID
                elif websocket in connected_players:
                    request["player_id"] = connected_players[websocket]

                # LÓGICA
                response = handle_request(request)

                if response:
                    if response.get("message_type") == "broadcast":
                        await broadcast(response)
                    else:
                        await unicast(response, websocket)

            except websockets.exceptions.ConnectionClosed:
                break

            except Exception as e:
                print("REQUEST ERROR:", e)

    finally:
        connected_players.pop(websocket, None)

async def broadcast(message):
    payload = json.dumps(message)

    for ws in list(connected_players.keys()):
        try:
            await ws.send(payload)
        except:
            connected_players.pop(ws, None)


async def unicast(message, websocket):
    try:
        await websocket.send(json.dumps(message))
    except:
        pass

async def main():
    print("WebSocket server for Parchis started on ws://localhost:8765")

    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())