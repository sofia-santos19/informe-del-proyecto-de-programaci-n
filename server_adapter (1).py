import game_engine


def handle_request(request):
    action = request.get("action")
    player_id = request.get("player_id")

    # PLAYERS
    if action == "join":
        return game_engine.add_player(
            request.get("player_name"),
            player_id
        )

    if action == "get_players":
        return game_engine.get_players()

    if action == "get_my_id":
        return game_engine.get_my_id(player_id)

    # GAME STATE
    if action == "get_state":
        return game_engine.get_state()

    if action == "get_board":
        return game_engine.get_board()

    # TURNS
    if action == "current_player":
        return game_engine.get_current_player()

    if action == "next_turn":
        return game_engine.next_turn()

    # DICE
    if action == "roll_dice":
        return game_engine.roll_dice(player_id)

    if action == "get_move_options":
        return game_engine.get_move_options(player_id)

    # PIECES
    if action == "move_piece":
        return game_engine.move_piece(
            player_id,
            request.get("piece_id"),
            request.get("move_type", "sum"),
            request.get("second_piece_id")
        )

    return {
        "message_type": "unicast",
        "error": "Acción inválida"
    }