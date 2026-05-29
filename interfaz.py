import os
import json
import sys
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot, QTimer, QPointF
from PyQt5.QtGui import QPixmap, QBrush, QPen
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout, 
    QLabel, QPushButton, QComboBox, QGraphicsScene, QGraphicsView, 
    QGraphicsEllipseItem, QInputDialog, QMessageBox, QGraphicsPixmapItem
)
from client_transport import GameClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# 🎲 Diccionario de dados generado dinámicamente
dices_images = {i: os.path.join(ASSETS_DIR, f"dice-six-faces-{['one','two','three','four','five','six'][i-1]}.png") for i in range(1, 7)}

# 📌 Mapa de movimientos integrado del código original
MOVE_TYPE_MAP = {0: "sum", 1: "single_d0", 2: "single_d1", 3: "jail_all"}

# 📍 COORDENADAS RECALCULADAS PARA LA MATRIZ 500x500
COORDENADAS_TABLERO = {
    "carcel_red":   [[55, 55],  [105, 55],  [55, 105],  [105, 105]],
    "carcel_blue":  [[395, 55], [445, 55], [395, 105], [445, 105]],

    # ── RECORRIDO PRINCIPAL DEL TABLERO (0 a 68) ──
    0:  [208, 185],  
    1:  [305, 482], 2:  [305, 459], 3:  [305, 435], 4:  [305, 412], 5:  [305, 388],
    6:  [305, 364], 7:  [305, 342], 8:  [295, 317],
    9:  [317, 292], 10: [342, 305], 11: [364, 305], 12: [389, 305], 13: [412, 305],
    14: [435, 305], 15: [459, 305], 16: [482, 305],
    17: [482, 250], 18: [482, 195], 19: [459, 195], 20: [435, 195], 21: [412, 195],
    22: [389, 195],  
    23: [364, 195], 24: [342, 195], 25: [317, 208],
    26: [295, 183], 27: [305, 158], 28: [305, 136], 29: [305, 112], 30: [305, 88],
    31: [305, 65], 32: [305, 41], 33: [305, 18], 34: [250, 18], 35: [195, 18],
    36: [195, 41], 37: [195, 65], 38: [195, 88], 39: [195, 112],  
    40: [195, 136],
    41: [195, 158], 42: [205, 183], 43: [183, 208], 44: [158, 195], 45: [136, 195],
    46: [111, 195], 47: [88, 195], 48: [65, 195], 49: [41, 195], 50: [18, 195],
    51: [18, 250], 52: [18, 305], 53: [41, 305], 54: [65, 305], 55: [88, 305],
    56: [112, 305], 57: [136, 305], 58: [158, 305], 59: [183, 292],
    60: [208, 317], 61: [195, 342], 62: [195, 364],  
    63: [195, 388],
    64: [195, 412], 65: [195, 435], 66: [195, 459], 67: [195, 482], 68: [250, 482],

    # ── METAS / PASILLO AZUL ──
    69: [451, 250], 70: [424, 250], 71: [397, 250], 72: [370, 250], 73: [343, 250],
}

# 🪟 VENTANA PRINCIPAL
class NewWindow(QMainWindow):
    def __init__(self, name):
        super().__init__()
        self.player_name, self.my_id, self.my_color = name, None, None
        self.setWindowTitle(f"Parchís – {name}")
        self.setFixedSize(720, 780)

        # UI Base
        central = QWidget()
        central.setObjectName("MainCentralWidget") # Identificador para aplicar estilos de fondo
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setFixedSize(520, 520)
        layout.addWidget(self.view, alignment=Qt.AlignCenter)

        # Tablero
        board_path = os.path.join(ASSETS_DIR, "Parchís.svg.png")
        if not os.path.exists(board_path):
            board_path = os.path.join(BASE_DIR, "Parchís.svg.png")
        pixmap = QPixmap(board_path)
        self.board_item = QGraphicsPixmapItem(pixmap.scaled(500, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.scene.addItem(self.board_item)

        # Fichas
        self.fichas = {"red": [], "blue": []}
        for color, qt_color in [("red", Qt.red), ("blue", Qt.blue)]:
            for i in range(4):
                ficha = QGraphicsEllipseItem(0, 0, 20, 20)
                ficha.setBrush(QBrush(qt_color))
                ficha.setPen(QPen(Qt.white, 2))
                ficha.setPos(*COORDENADAS_TABLERO[f"carcel_{color}"][i])
                self.scene.addItem(ficha)
                self.fichas[color].append(ficha)

        # Estado 
        self.label_status = QLabel("Esperando jugadores...")
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.setStyleSheet("font-size:18px; font-weight:bold; color:#1a237e;")
        layout.addWidget(self.label_status)

        # 🎛️ Controles ajustados a la lógica original
        controls = QGridLayout()
        controls.setContentsMargins(0, 10, 0, 0)
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(10)
        
        self.button_roll = QPushButton("🎲 Lanzar Dados", clicked=self.roll_dice)
        self.button_pass = QPushButton("⏭️ Pasar Turno", clicked=self.pass_turn)
        
        self.combo_pieces = QComboBox()
        self.combo_pieces.addItems([f"Ficha {i+1}" for i in range(4)])
        
        self.combo_move = QComboBox()
        self.combo_move.addItems(["Sumar", "Dado 1", "Dado 2", "Sacar todas"])
        
        self.button_move = QPushButton("♟️ Mover Ficha", clicked=self.send_move)

        # Asignación de widgets a la cuadrícula (Grid)
        controls.addWidget(self.button_roll, 0, 0)
        controls.addWidget(self.button_pass, 0, 1)
        controls.addWidget(self.combo_pieces, 1, 0)
        controls.addWidget(self.combo_move, 1, 1)
        controls.addWidget(self.button_move, 1, 2)

        # Dados Visuales
        self.dice0, self.dice1 = QLabel(), QLabel()
        for i, d in enumerate([self.dice0, self.dice1]):
            d.setFixedSize(70, 70)
            d.setStyleSheet("background:white; border:2px solid black;")
            d.setAlignment(Qt.AlignCenter)
            controls.addWidget(d, 0, 2 + i)
            self.set_dice(d, 1)

        layout.addLayout(controls)
        self.client = GameClient("ws://127.0.0.1:8765", self._safe_handle_response)

    def normalize_position(self, pos):
        try:
            pos_key = int(pos)
        except Exception:
            return pos
        if pos_key == 0:
            return 1
        if pos_key > 68:
            return pos_key - 68
        return pos_key

    def set_dice(self, label, value):
        value = int(value)
        if 1 <= value <= 6:
            pix = QPixmap(dices_images.get(value))
            if not pix.isNull():
                label.setPixmap(pix.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        label.setText(str(value) if 1 <= value <= 6 else "?")

    def iniciar_conexion(self):
        try:
            self.client.connect()
        except Exception as e:
            try:
                QMessageBox.critical(self, "Error de conexión", f"No se pudo conectar al servidor:\n{e}")
            except Exception:
                pass
            self.label_status.setText("🔌 Error: no se pudo conectar al servidor")
            return

        QTimer.singleShot(300, lambda: self.client.send_action("join", player_name=self.player_name))

    # ⚙️ Funciones de la lógica original integradas
    def roll_dice(self): 
        self.client.send_action("roll_dice")
        
    def pass_turn(self):  
        self.client.send_action("next_turn")
        
    def send_move(self):
        piece_id = self.combo_pieces.currentIndex()
        move_type = MOVE_TYPE_MAP.get(self.combo_move.currentIndex(), "sum")
        self.client.send_action("move_piece", piece_id=piece_id, move_type=move_type)

    def _safe_handle_response(self, response):
        QMetaObject.invokeMethod(self, "_handle_response_main_thread", Qt.QueuedConnection, Q_ARG(str, json.dumps(response)))

    @pyqtSlot(str)
    def _handle_response_main_thread(self, payload):
        try: self.handle_response(json.loads(payload))
        except Exception: pass

    def handle_response(self, data):
        if "error" in data:
            self.label_status.setText(f"⚠️  {data['error']}"); return

        if "your_id" in data:
            try: self.my_id = data.get("your_id")
            except Exception: pass

        if "dice" in data:
            try:
                dices = data.get("dice", [0, 0])
                if any(dices):
                    self.set_dice(self.dice0, dices[0])
                    self.set_dice(self.dice1, dices[1])
            except Exception: pass

        board = data.get("board_state", {})
        players = board.get("players", [])
        
        if "winner" in data:
            w_name = next((p["name"] for p in players if p["id"] == data["winner"]), data["winner"])
            QMessageBox.information(self, "🏆 ¡Ganador!", f"¡{w_name} ganó el juego!")
            self.label_status.setText(f"🏆 ¡{w_name} ganó!"); return

        if not board: return

        # Determinar el color e ID del jugador actual
        for p in players:
            if self.my_id is None and p["name"] == self.player_name:
                self.my_id, self.my_color = p["id"], p["color"]
            if self.my_id is not None and p["id"] == self.my_id:
                self.my_color = p["color"]

        # ── SECCIÓN DE CAMBIO DE COLOR DE FONDO ──
        # Se aplican tonos pastel para evitar interferencia visual con los componentes del juego
        if self.my_color == "red":
            self.centralWidget().setStyleSheet("#MainCentralWidget { background-color: #ffe6e6; }")
        elif self.my_color == "blue":
            self.centralWidget().setStyleSheet("#MainCentralWidget { background-color: #e6f2ff; }")
        # ──────────────────────────────────────────

        dices_rem = board.get("dices_remaining", [])
        is_my_turn = (self.my_id is not None) and (board.get("current_player") == self.my_id)
        
        # ── SECCIÓN DE CONTROL DE ESTADOS LÓGICOS DE TURNO ──
        game_state = board.get("game_state", "")
        status_text = self.label_status.text()
        
        if game_state == "waiting_for_players":
            status_text = "⏳ Esperando al segundo jugador..."
        elif game_state == "defining_turn_order":
            status_text = "🎲 Lanza el dado para definir quién empieza" if is_my_turn else "⏳ El oponente lanza para definir turno..."
        elif game_state == "in_progress":
            if is_my_turn:
                # Filtrar valores booleanos de los dados
                dados_validos = [d for d in dices_rem if isinstance(d, int) and d > 0]
                if dados_validos:
                    status_text = f"🟢 TU TURNO — Mueve una ficha (dados: {dados_validos})"
                else:
                    status_text = "🟢 TU TURNO — Lanza los dados"
            else:
                status_text = "🔴 Turno del oponente..."
        elif game_state == "finished":
            status_text = "🏁 Juego terminado"

        self.label_status.setText(status_text)
        # ── FIN DE LA SECCIÓN DE CONTROL DE ESTADOS ──

        dices = board.get("dices_value", [0, 0])
        if any(dices):
            self.set_dice(self.dice0, dices[0])
            self.set_dice(self.dice1, dices[1])

        self.update_piece_positions(players)

    def update_piece_positions(self, players):
        for p in players:
            color = p.get("color", "").lower()
            pieces = p.get("pieces", [])
            if color not in self.fichas: continue

            for idx, pos in enumerate(pieces):
                if idx >= len(self.fichas[color]): continue

                if pos == -1:
                    coord = COORDENADAS_TABLERO.get(f"carcel_{color}")[idx]
                else:
                    pos_key = self.normalize_position(pos)
                    coord = COORDENADAS_TABLERO.get(pos_key)

                if coord is None:
                    coord = [250, 250] 

                x, y = coord[0] - 10, coord[1] - 10
                piece_item = self.fichas[color][idx]
                piece_item.setZValue(10) 
                piece_item.setData(0, x)
                piece_item.setData(1, y)
                piece_item.setPos(QPointF(x, y))

        self.scene.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    nombre, ok = QInputDialog.getText(None, "Jugador", "Tu nombre:")
    if ok and nombre.strip():
        w = NewWindow(nombre.strip())
        w.show(); w.iniciar_conexion()
        sys.exit(app.exec_())