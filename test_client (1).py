from client_transport import GameClient

# 🛡️ Memoria global para evitar dados [0,0]
last_valid_dados = [0, 0]
last_player_id = None


# ─────────────────────────────────────────
# RESPUESTAS DEL SERVIDOR
# ─────────────────────────────────────────

def handle_response(response):
    global last_valid_dados, last_player_id

    print("\n==============================")

    if not isinstance(response, dict):
        print(response)
        return

    # ERROR
    if response.get("status") == "error" or response.get("error"):
        msg = response.get("message") or response.get("error")
        print(f"❌ ERROR: {msg}")
        return

    # BOARD STATE
    bs = response.get("board_state")

    if bs:
        game_state = bs.get("game_state", "?")
        current_id = bs.get("current_player", "?")
        dados = bs.get("dices_value", [0, 0])
        players = bs.get("players", [])

        # evitar perder dados visualmente
        if current_id != last_player_id:
            last_valid_dados = [0, 0]
            last_player_id = current_id

        if dados == [0, 0] and last_valid_dados != [0, 0]:
            dados = last_valid_dados
        else:
            last_valid_dados = dados

        current_name = next(
            (p["name"] for p in players if p["id"] == current_id),
            current_id
        )

        print(f"🎮 Estado: {game_state}")
        print(f"🎲 Dados: {dados}")

        if game_state == "in_progress":
            print(f"▶ Turno de: {current_name}")

        if game_state == "finished":
            winner = bs.get("winner")
            winner_name = next(
                (p["name"] for p in players if p["id"] == winner),
                winner
            )
            print(f"🏆 GANADOR: {winner_name}")

        _print_pieces(players)

        # opciones de movimiento
        if response.get("move_options"):
            print("\n📌 Opciones disponibles:")
            for i, op in enumerate(response["move_options"], start=1):
                print(f"   {i}. {op['description']}")

        # info
        if response.get("info"):
            print(f"\nℹ {response['info']}")

        # turno extra
        if response.get("extra_turn"):
            print("\n🎲 ¡PARES! TIENES TURNO EXTRA")

        return

    # GET PLAYERS
    if "players" in response:
        print("\n👥 JUGADORES:")
        for p in response["players"]:
            print(f" [{p['color']}] {p['name']} -> {p['id']}")
        return

    # GET MY ID
    if "id" in response:
        print(f"\n🧍 ID: {response['id']}")
        print(f"👤 Nombre: {response.get('name')}")
        return

    # CURRENT PLAYER
    if "player_id" in response:
        print(f"\n▶ Turno actual: {response['player_id']}")
        return

    print(response)


# ─────────────────────────────────────────
# PRINT DE FICHAS
# ─────────────────────────────────────────

def _print_pieces(players):

    print("\n📌 ESTADO DE FICHAS")

    for p in players:

        fichas = []

        for i, pos in enumerate(p["pieces"]):

            if pos == -1:
                txt = f"F{i}:🔒"
            elif pos == 76:
                txt = f"F{i}:🏁"
            elif pos >= 68:
                txt = f"F{i}:⭐{pos-67}"
            else:
                txt = f"F{i}:{pos}"

            fichas.append(txt)

        print(f"[{p['color']}] {p['name']} -> {' | '.join(fichas)}")


# ─────────────────────────────────────────
# MENÚ DE MOVIMIENTO
# ─────────────────────────────────────────

def move_menu(client):

    print("\n========= MOVER FICHA =========")

    print("1 -> Suma de dados")
    print("2 -> Usar dado 1")
    print("3 -> Usar dado 2")
    print("4 -> Dividir dados")
    print("5 -> Sacar TODAS de cárcel")

    op = input("Opción: ").strip()

    move_map = {
        "1": "sum",
        "2": "single_d0",
        "3": "single_d1",
        "4": "split",
        "5": "jail_all"
    }

    if op not in move_map:
        print("❌ Opción inválida")
        return

    move_type = move_map[op]

    # jail_all no necesita ficha
    if move_type == "jail_all":

        client.send_action(
            "move_piece",
            piece_id=0,
            move_type="jail_all"
        )
        return

    # ficha principal
    try:
        piece = int(input("Ficha principal (0-3): "))
    except:
        print("❌ Número inválido")
        return

    # split
    if move_type == "split":

        try:
            second = int(input("Segunda ficha (0-3): "))
        except:
            print("❌ Número inválido")
            return

        client.send_action(
            "move_piece",
            piece_id=piece,
            move_type="split",
            second_piece_id=second
        )

    else:

        client.send_action(
            "move_piece",
            piece_id=piece,
            move_type=move_type
        )


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():

    client = GameClient(
        "ws://127.0.0.1:8765",
        handle_response
    )

    client.connect()

    player = input("👤 Nombre del jugador: ")

    client.send_action(
        "join",
        player_name=player
    )

    while True:

        print("\n==============================")
        print("🎮 MENÚ PRINCIPAL")
        print("==============================")
        print("1 -> Ver jugadores")
        print("2 -> Ver turno")
        print("3 -> Tirar dados")
        print("4 -> Mover ficha")
        print("5 -> Ver tablero")
        print("6 -> Ver estado")
        print("7 -> Ver mi ID")
        print("0 -> Salir")

        op = input("\nOpción: ").strip()

        if op == "0":
            break

        elif op == "1":
            client.send_action("get_players")

        elif op == "2":
            client.send_action("current_player")

        elif op == "3":
            client.send_action("roll_dice")

        elif op == "4":
            move_menu(client)

        elif op == "5":
            client.send_action("get_board")

        elif op == "6":
            client.send_action("get_state")

        elif op == "7":
            client.send_action("get_my_id")

        else:
            print("❌ Opción inválida")

    client.close()


if __name__ == "__main__":
    main()