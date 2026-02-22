import socket
import threading
import json
import os
import argparse
from datetime import datetime

from colorama import init, Fore, Style

import csv

from midi_writer import events_to_midi

init(autoreset=True)

# ── Configuración por defecto ───────────────────────────────────────────────
DEFAULT_HOST = "0.0.0.0"     
DEFAULT_PORT = 9000
OUTPUT_DIR   = "output"

# Colores por node_id (se asignan en orden de conexión si no están en el mapa)
NODE_COLOR_MAP = {
    "quijote": Fore.CYAN,
    "cid":     Fore.YELLOW,
}
FALLBACK_COLORS = [Fore.GREEN, Fore.MAGENTA, Fore.BLUE, Fore.WHITE]

# ── Estado compartido ───────────────────────────────────────────────────────
lock            = threading.Lock()
node_events: dict[str, list[dict]] = {}
node_colors: dict[str, str]        = {}
color_counter                      = 0


def get_node_color(node_id: str) -> str:
    global color_counter
    with lock:
        if node_id not in node_colors:
            color = NODE_COLOR_MAP.get(
                node_id, FALLBACK_COLORS[color_counter % len(FALLBACK_COLORS)]
            )
            node_colors[node_id] = color
            color_counter += 1
        return node_colors[node_id]


def log(msg: str, color: str = Fore.WHITE) -> None:
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    with lock:
        print(f"{Fore.WHITE}[{ts}]{Style.RESET_ALL} {color}{msg}")


def recv_lines(conn: socket.socket):
    """Generador: lee el socket y yield líneas JSON completas."""
    buffer = ""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buffer += chunk.decode("utf-8")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line:
                yield line


def handle_client(conn: socket.socket, addr: tuple) -> None:
    log(f"Nueva conexión desde {addr[0]}:{addr[1]}", Fore.GREEN)
    node_id = None

    try:
        for line in recv_lines(conn):
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                log(f"Mensaje inválido ignorado: {line[:60]}", Fore.RED)
                continue

            mtype = msg.get("type")

            # ── CONNECT ──────────────────────────────────────────────────
            if mtype == "connect":
                node_id = msg["node_id"]
                color   = get_node_color(node_id)
                with lock:
                    node_events[node_id] = []
                log(
                    f"[{node_id.upper()}] Nodo conectado  |  corpus: {msg.get('corpus', '?')}",
                    color,
                )
                conn.send(json.dumps({"type": "ack", "status": "ok"}).encode() + b"\n")

            # ── EVENT ────────────────────────────────────────────────────
            elif mtype == "event":
                node_id = msg["node_id"]
                color   = get_node_color(node_id)
                with lock:
                    node_events.setdefault(node_id, []).append(msg)
                log(
                    f"[{node_id.upper()}]  oración:{msg['sentence_idx']:03d}"
                    f"  palabra:'{msg['word']:<12}'"
                    f"  raw:{msg['raw_value']:8.2f}"
                    f"  MIDI:{msg['midi_value']:3d}",
                    color,
                )

            # ── DONE ─────────────────────────────────────────────────────
            elif mtype == "done":
                node_id = msg["node_id"]
                color   = get_node_color(node_id)
                total   = msg.get("total_events", 0)
                log(
                    f"[{node_id.upper()}] Procesamiento completado  |  {total} eventos",
                    color,
                )
                # Generar archivo MIDI
                with lock:
                    events = list(node_events.get(node_id, []))
                if events:
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    midi_path = os.path.join(OUTPUT_DIR, f"{node_id}.mid")
                    events_to_midi(events, midi_path)
                    log(f"[{node_id.upper()}] MIDI generado → {midi_path}", color)

                    csv_path = os.path.join(OUTPUT_DIR, f"{node_id}.csv")
                    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                        writer = csv.DictWriter(
                            csvfile,
                            fieldnames=["sentence_idx", "word", "raw_value", "midi_value"],
                        )
                        writer.writeheader()
                        for e in events:
                            writer.writerow({
                                "sentence_idx": e["sentence_idx"],
                                "word":         e["word"],
                                "raw_value":    e["raw_value"],
                                "midi_value":   e["midi_value"],
                            })
                    log(f"[{node_id.upper()}] CSV  generado → {csv_path}", color)

    except Exception as exc:
        log(f"Error en {addr}: {exc}", Fore.RED)
    finally:
        conn.close()
        label = node_id.upper() if node_id else str(addr)
        log(f"[{label}] Conexión cerrada", Fore.RED)


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-Sockets: Nodo Central")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print(f"\n{Fore.MAGENTA}{'═' * 60}")
    print("   MIDI-SOCKETS  —  Nodo Central (Monitor/Servidor)")
    print("   Sistemas Distribuidos 2526-2  |  UNIMET")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((args.host, args.port))
        srv.listen(10)
        log(f"Escuchando en {args.host}:{args.port}  (Ctrl+C para detener)", Fore.GREEN)

        try:
            while True:
                conn, addr = srv.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print(f"\n{Fore.MAGENTA}Servidor detenido.{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
