import os
import random
import string
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"

if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR.parent / "static"
if not STATIC_DIR.exists():
    STATIC_DIR = Path("/app/static")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


rooms: dict[str, dict] = {}


def generate_room_code() -> str:
    while True:
        code = "".join(random.choices(string.digits, k=4))
        if code not in rooms:
            return code


def create_empty_board() -> list[list[int]]:
    return [[0 for _ in range(7)] for _ in range(6)]


def check_winner(
    board: list[list[int]], player: int
) -> Optional[list[tuple[int, int]]]:
    rows, cols = 6, 7

    for row in range(rows):
        for col in range(cols - 3):
            cells = [(row, col + i) for i in range(4)]
            if all(board[r][c] == player for r, c in cells):
                return cells

    for row in range(rows - 3):
        for col in range(cols):
            cells = [(row + i, col) for i in range(4)]
            if all(board[r][c] == player for r, c in cells):
                return cells

    for row in range(rows - 3):
        for col in range(cols - 3):
            cells = [(row + i, col + i) for i in range(4)]
            if all(board[r][c] == player for r, c in cells):
                return cells

    for row in range(3, rows):
        for col in range(cols - 3):
            cells = [(row - i, col + i) for i in range(4)]
            if all(board[r][c] == player for r, c in cells):
                return cells

    return None


def check_draw(board: list[list[int]]) -> bool:
    return all(cell != 0 for row in board for cell in row)


def get_next_open_row(board: list[list[int]], col: int) -> Optional[int]:
    for row in range(5, -1, -1):
        if board[row][col] == 0:
            return row
    return None


def create_room() -> dict:
    code = generate_room_code()
    rooms[code] = {
        "code": code,
        "board": create_empty_board(),
        "players": {},
        "sockets": {},
        "current_turn": 1,
        "scores": {1: 0, 2: 0},
        "status": "waiting",
        "winner": None,
        "winning_cells": [],
    }
    return {"code": code}


def get_room_state(room: dict) -> dict:
    players = {}
    for num, info in room["players"].items():
        players[num] = {
            "name": info.get("name", f"Player {num}"),
            "color": info.get("color", "#ff0000"),
        }

    return {
        "type": "state",
        "board": room["board"],
        "current_turn": room["current_turn"],
        "scores": room["scores"],
        "status": room["status"],
        "winner": room["winner"],
        "winning_cells": room["winning_cells"],
        "players": players,
    }


@app.get("/")
async def get_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>index.html not found</h1>")


@app.get("/create-room")
async def create_room_endpoint():
    return create_room()


@app.websocket("/ws/{room_code}")
async def websocket_endpoint(websocket: WebSocket, room_code: str):
    if room_code not in rooms:
        await websocket.close(code=4004, reason="Room not found")
        return

    room = rooms[room_code]

    if len(room["players"]) >= 2:
        await websocket.close(code=4003, reason="Room is full")
        return

    player_num = 1 if 1 not in room["players"] else 2
    ws_id = id(websocket)

    room["sockets"][ws_id] = websocket
    room["players"][player_num] = {
        "name": None,
        "color": None,
        "player_num": player_num,
        "ws_id": ws_id,
    }

    await websocket.accept()
    await websocket.send_json({"type": "assigned", "player_num": player_num})

    for ws in room["sockets"].values():
        await ws.send_json(get_room_state(room))

    try:
        while True:
            data = await websocket.receive_json()
            await handle_message(room, ws_id, player_num, data)
    except WebSocketDisconnect:
        handle_disconnect(room, ws_id, player_num)


async def handle_message(room: dict, ws_id: int, player_num: int, data: dict):
    msg_type = data.get("type")

    if msg_type == "set_info":
        if player_num in room["players"]:
            room["players"][player_num]["name"] = data.get(
                "name", f"Player {player_num}"
            )
            room["players"][player_num]["color"] = data.get("color", "#ff0000")

        if (
            len(room["players"]) == 2
            and all(p.get("name") and p.get("color") for p in room["players"].values())
            and room["status"] == "waiting"
        ):
            room["status"] = "playing"

        await broadcast_state(room)

    elif msg_type == "drop":
        if room["status"] != "playing":
            return
        if room["current_turn"] != player_num:
            return

        col = data.get("col")
        if col is None or col < 0 or col > 6:
            return

        row = get_next_open_row(room["board"], col)
        if row is None:
            return

        room["board"][row][col] = player_num

        winning_cells = check_winner(room["board"], player_num)
        if winning_cells:
            room["status"] = "finished"
            room["winner"] = player_num
            room["winning_cells"] = winning_cells
            room["scores"][player_num] += 1
        elif check_draw(room["board"]):
            room["status"] = "finished"
            room["winner"] = None
        else:
            room["current_turn"] = 2 if room["current_turn"] == 1 else 1

            if len(room["players"]) == 2 and all(
                p.get("name") and p.get("color") for p in room["players"].values()
            ):
                room["status"] = "playing"

        await broadcast_state(room)

    elif msg_type == "next_round":
        room["board"] = create_empty_board()
        room["current_turn"] = 1
        room["status"] = (
            "playing"
            if len(room["players"]) == 2
            and all(p.get("name") and p.get("color") for p in room["players"].values())
            else "waiting"
        )
        room["winner"] = None
        room["winning_cells"] = []
        await broadcast_state(room)

    elif msg_type == "reset_scores":
        room["scores"] = {1: 0, 2: 0}
        room["board"] = create_empty_board()
        room["current_turn"] = 1
        room["status"] = "waiting"
        room["winner"] = None
        room["winning_cells"] = []
        await broadcast_state(room)


def handle_disconnect(room: dict, ws_id: int, player_num: int):
    if ws_id in room["sockets"]:
        del room["sockets"][ws_id]
    if player_num in room["players"]:
        del room["players"][player_num]

    if len(room["players"]) == 0:
        if room.get("code") in rooms:
            del rooms[room["code"]]
        return

    if room["status"] == "playing":
        room["status"] = "waiting"
        room["board"] = create_empty_board()
        room["current_turn"] = 1
        room["winner"] = None
        room["winning_cells"] = []

    import asyncio

    for ws in list(room["sockets"].values()):
        try:
            asyncio.run(ws.send_json({"type": "opponent_disconnected"}))
        except:
            pass


async def broadcast_state(room: dict):
    state = get_room_state(room)
    disconnected = []

    for ws_id, ws in list(room["sockets"].items()):
        try:
            await ws.send_json(state)
        except:
            disconnected.append(ws_id)

    for ws_id in disconnected:
        if ws_id in room["sockets"]:
            del room["sockets"][ws_id]
        player_num = None
        for num, info in list(room["players"].items()):
            if info.get("ws_id") == ws_id:
                player_num = num
                break
        if player_num and player_num in room["players"]:
            del room["players"][player_num]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
