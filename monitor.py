import socket
import json
import os
import csv
import argparse
from datetime import datetime

from colorama import init, Fore, Style
from midi_writer import events_to_midi

init(autoreset=True)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000
OUTPUT_DIR   = "output"

# Almacenamiento local del monitor
node_events: dict[str, list[dict]] = {}

def log(msg: str, color: str = Fore.WHITE) -> None:
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Fore.WHITE}[{ts}]{Style.RESET_ALL} {color}{msg}")

def recv_lines(sock: socket.socket):
    """Generador: lee el socket y devuelve líneas JSON completas."""
    buffer = ""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk.decode("utf-8")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line:
                yield line

def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-Sockets: Nodo Monitor")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print(f"\n{Fore.MAGENTA}{'═' * 60}")
    print("   MIDI-SOCKETS  —  Nodo Cliente: MONITOR (Orquestador)")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((args.host, args.port))
            log("Conectado al Servidor Central exitosamente.", Fore.GREEN)
        except ConnectionRefusedError:
            log(f"No se pudo conectar a {args.host}:{args.port} — ¿Está corriendo el servidor?", Fore.RED)
            return

        # 1. registro en el servidor con el ID "monitor"
        connect_msg = {"type": "connect", "node_id": "monitor"}
        sock.send((json.dumps(connect_msg) + "\n").encode("utf-8"))

        log("Esperando eventos de los nodos de procesamiento...", Fore.CYAN)

        # 2. todo lo que el servidor nos reenvíe es recibido
        try:
            for line in recv_lines(sock):
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                mtype = msg.get("type")

                # continue el 'ack' de conexión
                if mtype == "ack":
                    continue

                # ── RECIBIR EVENTO Y GUARDARLO  ──
                elif mtype == "event":
                    sender_id = msg.get("node_id")
                    node_events.setdefault(sender_id, []).append(msg)
                    
                    log(
                        f"[{sender_id.upper()}]  oración:{msg['sentence_idx']:03d}"
                        f"  palabra:'{msg['word']:<12}'"
                        f"  raw:{msg['raw_value']:8.2f}"
                        f"  MIDI:{msg['midi_value']:3d}",
                        Fore.YELLOW
                    )

                # ── FIN DEL PROCESAMIENTO Y GENERACIÓN DE ARCHIVOS  ──
                elif mtype == "done":
                    sender_id = msg.get("node_id")
                    total = msg.get("total_events", 0)
                    log(f"[{sender_id.upper()}] Procesamiento completado  |  {total} eventos recibidos", Fore.GREEN)
                    
                    # Codigo Carlos (Mudado)
                    events = node_events.get(sender_id, [])
                    if events:
                        midi_path = os.path.join(OUTPUT_DIR, f"{sender_id}.mid")
                        events_to_midi(events, midi_path)
                        log(f"[{sender_id.upper()}] MIDI generado → {midi_path}", Fore.CYAN)

                        csv_path = os.path.join(OUTPUT_DIR, f"{sender_id}.csv")
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
                        log(f"[{sender_id.upper()}] CSV  generado → {csv_path}", Fore.CYAN)

        except KeyboardInterrupt:
            log("Monitor detenido por el usuario.", Fore.MAGENTA)

if __name__ == "__main__":
    main()