#game engine
# game_engine.py
import copy
from random import randint

# =================================================
# CONFIGURACIÓN DE JUEGO
# =================================================

COLORS = ["red", "blue"]
GAME_STATES = [
    "waiting_for_players",
    "defining_turn_order",
    "in_progress",
    "finished"
]
SAFE_SQUARES = {0, 8, 13, 17, 22, 26, 31, 34, 39, 43, 48, 52, 57}
START_SQUARES = [0, 34]
BOARD_LENGTH = 68
PIECES_PER_PLAYER = 4
GOAL_POSITION = 76


def random_dice_values():
    return randint(1, 6), randint(1, 6)


class GameController:

    def __init__(self):
        self.players = []
        self.current_player = None
        self.dices_value = [0, 0]
        self.dice_available = [False, False]
        self.board = {}
        self.game_state = GAME_STATES[0]
        self.winner = None
        self.first_turn = {
            "draw": set(),
            "rolls": 0,
            "best_value": 0,
            "turn": None
        }

    def _find_player(self, pid):
        return next((player for player in self.players if player["id"] == pid), None)

    def _player_index(self, pid):
        return next((idx for idx, player in enumerate(self.players) if player["id"] == pid), None)

    def _absolute_position(self, pid, relative):
        if relative < 0:
            return -1

        player_index = self._player_index(pid)
        if player_index is None:
            return -1

        if relative >= BOARD_LENGTH:
            return (player_index + 1) * 1000 + (relative - BOARD_LENGTH)

        return (START_SQUARES[player_index] + relative) % BOARD_LENGTH

    def _rebuild_board_map(self):
        lanes = {}
        for player in self.players:
            for piece_id, position in enumerate(player["pieces"]):
                if position < 0 or position == GOAL_POSITION:
                    continue
                board_key = self._absolute_position(player["id"], position)
                lanes.setdefault(board_key, []).append([player["id"], piece_id])
        self.board = lanes

    def _snapshot(self):
        self._rebuild_board_map()
        return copy.deepcopy({
            "players": self.players,
            "current_player": self.current_player,
            "dices_value": self.dices_value,
            "dice_available": self.dice_available,
            "dices_remaining": self.dice_available,
            "game_state": self.game_state,
            "board": self.board,
            "winner": self.winner
        })

    def _advance_to_next_player(self):
        if self.game_state != GAME_STATES[2] or not self.players:
            return

        current_idx = self._player_index(self.current_player)
        self.current_player = self.players[(current_idx + 1) % len(self.players)]["id"]
        self.dices_value = [0, 0]
        self.dice_available = [False, False]

    def _is_safe_square(self, board_key):
        return board_key in SAFE_SQUARES

    def _capture_enemy_pieces(self, attacker_id, board_key):
        if self._is_safe_square(board_key):
            return []

        occupants = self.board.get(board_key, [])
        captured = []
        for pid, piece_id in occupants:
            if pid != attacker_id:
                target = self._find_player(pid)
                if target:
                    target["pieces"][piece_id] = -1
                    captured.append({
                        "player_id": pid,
                        "player_name": target["name"],
                        "piece_id": piece_id
                    })
        if captured:
            self._rebuild_board_map()
        return captured

    def _validate_piece_move(self, player, piece_id, steps):
        if not 0 <= piece_id < PIECES_PER_PLAYER:
            return False, "Ficha inválida"

        current_pos = player["pieces"][piece_id]
        if current_pos == GOAL_POSITION:
            return False, "Ya llegó a meta"

        if current_pos == -1:
            if self.dices_value[0] != self.dices_value[1]:
                return False, "Necesita pares"
            return True, "Sale de cárcel"

        if current_pos + steps > GOAL_POSITION:
            return False, "No puede pasar la meta"

        return True, "OK"

    def add_player(self, name, pid):
        if len(self.players) >= 2:
            return {
                "message_type": "broadcast",
                "board_state": self._snapshot()
            }

        self.players.append({
            "id": pid,
            "name": name,
            "color": COLORS[len(self.players)],
            "pieces": [-1] * PIECES_PER_PLAYER
        })

        if len(self.players) == 2:
            self.game_state = GAME_STATES[1]
            self.current_player = self.players[0]["id"]

        return {
            "message_type": "broadcast",
            "board_state": self._snapshot()
        }

    def get_players(self):
        return {
            "message_type": "unicast",
            "players": self.players
        }

    def get_my_id(self, pid):
        player = self._find_player(pid)
        return {
            "message_type": "unicast",
            "id": pid,
            "name": player["name"] if player else None
        }

    def get_current_player(self):
        return {
            "message_type": "unicast",
            "player_id": self.current_player
        }

    def next_turn(self):
        self._advance_to_next_player()
        return {
            "message_type": "broadcast",
            "board_state": self._snapshot()
        }

    def roll_dice(self, pid):
        if self.game_state == GAME_STATES[1]:
            if self.current_player != pid:
                return {
                    "message_type": "unicast",
                    "error": "No es tu turno"
                }

            d0, d1 = random_dice_values()
            self.dices_value = [d0, d1]
            total = d0 + d1
            self.first_turn["rolls"] += 1

            if total > self.first_turn["best_value"]:
                self.first_turn["best_value"] = total
                self.first_turn["turn"] = pid
                self.first_turn["draw"] = {pid}
            elif total == self.first_turn["best_value"]:
                self.first_turn["draw"].add(pid)

            opponents = [player for player in self.players if player["id"] != pid]
            if opponents:
                self.current_player = opponents[0]["id"]

            if self.first_turn["rolls"] >= 2:
                if len(self.first_turn["draw"]) == 1:
                    self.current_player = self.first_turn["turn"]
                    self.game_state = GAME_STATES[2]
                else:
                    self.first_turn = {
                        "draw": set(),
                        "rolls": 0,
                        "best_value": 0,
                        "turn": None
                    }

            return {
                "message_type": "broadcast",
                "board_state": self._snapshot()
            }

        if self.current_player != pid:
            return {
                "message_type": "unicast",
                "error": "No es tu turno"
            }

        if any(self.dice_available):
            return {
                "message_type": "unicast",
                "error": "Aún tienes dados disponibles"
            }

        d0, d1 = random_dice_values()
        self.dices_value = [d0, d1]
        self.dice_available = [True, True]

        return {
            "message_type": "broadcast",
            "board_state": self._snapshot()
        }

    def get_move_options(self, pid):
        d0, d1 = self.dices_value
        available = self.dice_available
        options = []

        if d0 == d1:
            options.append({"type": "jail_all", "description": "Sacar todas las fichas"})

        if available[0] and available[1]:
            options.append({"type": "sum", "description": f"Suma ({d0 + d1})"})

        if available[0]:
            options.append({"type": "single_d0", "description": f"Dado 1 ({d0})"})

        if available[1]:
            options.append({"type": "single_d1", "description": f"Dado 2 ({d1})"})

        if available[0] and available[1]:
            options.append({"type": "split", "description": f"Separar ({d0} y {d1})"})

        return {
            "message_type": "unicast",
            "move_options": options
        }

    def move_piece(self, pid, piece_id, move_type="sum", second_piece_id=None):
        if self.current_player != pid:
            return {
                "message_type": "unicast",
                "error": "No es tu turno"
            }

        player = self._find_player(pid)
        if not player:
            return {
                "message_type": "unicast",
                "error": "Jugador inválido"
            }

        d0, d1 = self.dices_value
        is_pair = d0 == d1
        captures = []

        if move_type == "jail_all":
            if not any(self.dice_available):
                return {
                    "message_type": "unicast",
                    "error": "No hay dados disponibles"
                }

            if not is_pair:
                return {
                    "message_type": "unicast",
                    "error": "Necesita pares"
                }

            if not any(pos == -1 for pos in player["pieces"]):
                return {
                    "message_type": "unicast",
                    "error": "No tienes fichas en cárcel"
                }

            for index, position in enumerate(player["pieces"]):
                if position == -1:
                    player["pieces"][index] = 0

            self.dice_available = [False, False]
            self.dices_value = [0, 0]
            self._rebuild_board_map()

            return {
                "message_type": "broadcast",
                "board_state": self._snapshot(),
                "extra_turn": is_pair
            }

        if move_type == "split":
            if second_piece_id is None:
                return {
                    "message_type": "unicast",
                    "error": "Falta segunda ficha"
                }

            ok_first, msg_first = self._validate_piece_move(player, piece_id, d0)
            ok_second, msg_second = self._validate_piece_move(player, second_piece_id, d1)

            if not ok_first:
                return {"message_type": "unicast", "error": msg_first}
            if not ok_second:
                return {"message_type": "unicast", "error": msg_second}

            if player["pieces"][piece_id] == -1:
                player["pieces"][piece_id] = 0
            else:
                player["pieces"][piece_id] += d0

            if player["pieces"][second_piece_id] == -1:
                player["pieces"][second_piece_id] = 0
            else:
                player["pieces"][second_piece_id] += d1

            self.dice_available = [False, False]
            self._rebuild_board_map()

            first_key = self._absolute_position(pid, player["pieces"][piece_id])
            second_key = self._absolute_position(pid, player["pieces"][second_piece_id])
            captures.extend(self._capture_enemy_pieces(pid, first_key))
            captures.extend(self._capture_enemy_pieces(pid, second_key))

            if not is_pair:
                self._advance_to_next_player()
            else:
                self.dices_value = [0, 0]

            return {
                "message_type": "broadcast",
                "board_state": self._snapshot(),
                "captures": captures,
                "extra_turn": is_pair
            }

        if move_type == "sum":
            steps = d0 + d1
            self.dice_available = [False, False]
        elif move_type == "single_d0":
            steps = d0
            self.dice_available[0] = False
        elif move_type == "single_d1":
            steps = d1
            self.dice_available[1] = False
        else:
            return {
                "message_type": "unicast",
                "error": "Tipo inválido"
            }

        ok, message = self._validate_piece_move(player, piece_id, steps)
        if not ok:
            return {"message_type": "unicast", "error": message}

        if player["pieces"][piece_id] == -1:
            player["pieces"][piece_id] = 0
        else:
            player["pieces"][piece_id] += steps

        self._rebuild_board_map()
        capture_list = self._capture_enemy_pieces(pid, self._absolute_position(pid, player["pieces"][piece_id]))

        if all(position == GOAL_POSITION for position in player["pieces"]):
            self.game_state = GAME_STATES[3]
            self.winner = pid

        if not any(self.dice_available):
            if is_pair:
                self.dices_value = [0, 0]
            else:
                self._advance_to_next_player()

        return {
            "message_type": "broadcast",
            "board_state": self._snapshot(),
            "captures": capture_list,
            "extra_turn": is_pair
        }

    def get_board(self):
        self._rebuild_board_map()
        return {
            "message_type": "unicast",
            "board": self.board,
            "safe_squares": list(SAFE_SQUARES)
        }

    def get_state(self):
        self._rebuild_board_map()
        return {
            "message_type": "unicast",
            "players": self.players,
            "current_player": self.current_player,
            "dices_value": self.dices_value,
            "dice_available": self.dice_available,
            "dices_remaining": self.dice_available,
            "board": self.board,
            "game_state": self.game_state,
            "winner": self.winner
        }

engine = GameController()


def add_player(name, pid):
    return engine.add_player(name, pid)


def get_players():
    return engine.get_players()


def get_my_id(pid):
    return engine.get_my_id(pid)


def get_current_player():
    return engine.get_current_player()


def next_turn():
    return engine.next_turn()


def roll_dice(pid):
    return engine.roll_dice(pid)


def get_move_options(pid):
    return engine.get_move_options(pid)


def move_piece(pid, piece_id, move_type="sum", second_piece_id=None):
    return engine.move_piece(pid, piece_id, move_type, second_piece_id)


def get_board():
    return engine.get_board()


def get_state():
    return engine.get_state()