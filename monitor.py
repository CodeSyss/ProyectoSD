import mido
import time
import socket
import json
import os
import csv
import argparse
import threading
from datetime import datetime

from colorama import init, Fore, Style
from midi_writer import events_to_midi

init(autoreset=True)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9000
OUTPUT_DIR   = "output"

node_events: dict[str, list[dict]] = {}

def log(msg: str, color: str = Fore.WHITE) -> None:
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"{Fore.WHITE}[{ts}]{Style.RESET_ALL} {color}{msg}")

def recv_lines(sock: socket.socket):
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

def input_thread(sock: socket.socket):
    """Hilo para manejar la entrada del usuario y enviar la configuración."""
    print(f"\n{Fore.YELLOW}► Escribe 'iniciar' y presiona ENTER para distribuir la carga a los nodos.{Style.RESET_ALL}\n")
    while True:
        cmd = input()
        if cmd.strip().lower() == "iniciar":
            log("Distribuyendo configuración a los procesadores...", Fore.MAGENTA)
            
            #configuración nodo Quijote
            sock.send((json.dumps({
                "type": "config", 
                "target": "quijote", 
                "corpus": "corpus/quijote.txt"
            }) + "\n").encode("utf-8"))
            
            #configuración nodo Cid
            sock.send((json.dumps({
                "type": "config", 
                "target": "cid", 
                "corpus": "corpus/cid.txt"
            }) + "\n").encode("utf-8"))
            break

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
            log(f"No se pudo conectar a {args.host}:{args.port}", Fore.RED)
            return

        # 1. Registro
        connect_msg = {"type": "connect", "node_id": "monitor"}
        sock.send((json.dumps(connect_msg) + "\n").encode("utf-8"))

        # el hilo inicia para leer el input del usuario
        threading.Thread(target=input_thread, args=(sock,), daemon=True).start()

    # Inicializar puerto MIDI para tiempo real
        try:
            # En Windows suele llamarse así. Si falla, el except te dirá cómo se llama el tuyo.
            midi_out = mido.open_output('Microsoft GS Wavetable Synth 0')
            log("🎵 Sintetizador MIDI en tiempo real activado.", Fore.GREEN)
        except Exception as e:
            midi_out = None
            puertos_disponibles = mido.get_output_names()
            log(f"⚠️ Falló el audio. Puertos detectados: {puertos_disponibles}", Fore.YELLOW)

        log("Esperando eventos de los nodos de procesamiento...", Fore.CYAN)

        # 2. Escucha de eventos
        try:
            for line in recv_lines(sock):
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                mtype = msg.get("type")

                if mtype == "ack":
                    continue

                elif mtype == "event":
                    sender_id = msg.get("node_id")
                    node_events.setdefault(sender_id, []).append(msg)
                    log(
                        f"[{sender_id.upper()}]  oración:{msg['sentence_idx']:03d}"
                        f"  palabra:'{msg['word']:<12}'  raw:{msg['raw_value']:8.2f}  MIDI:{msg['midi_value']:3d}",
                        Fore.YELLOW
                    )
                
                # --- REPRODUCCIÓN EN TIEMPO REAL ---
                    if midi_out:
                        midi_val = int(msg['midi_value'])
                        note = int(midi_val * 0.5 + 36)
                        velocity = max(40, min(127, midi_val + 30))
                        
                        # Encender la nota
                        midi_out.send(mido.Message('note_on', note=note, velocity=velocity))
                        
                        # Apagar la nota un instante después usando un hilo rápido para no bloquear la red
                        def note_off(n):
                            time.sleep(0.2)
                            if midi_out:
                                midi_out.send(mido.Message('note_off', note=n, velocity=0))
                        threading.Thread(target=note_off, args=(note,), daemon=True).start()
                    # -----------------------------------

                elif mtype == "done":
                    sender_id = msg.get("node_id")
                    total = msg.get("total_events", 0)
                    log(f"[{sender_id.upper()}] Procesamiento completado  |  {total} eventos recibidos", Fore.GREEN)
                    
                    events = node_events.get(sender_id, [])
                    if events:
                        midi_path = os.path.join(OUTPUT_DIR, f"{sender_id}.mid")
                        events_to_midi(events, midi_path)
                        log(f"[{sender_id.upper()}] MIDI generado → {midi_path}", Fore.CYAN)

                        csv_path = os.path.join(OUTPUT_DIR, f"{sender_id}.csv")
                        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=["sentence_idx", "word", "raw_value", "midi_value"])
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
            log("Monitor detenido.", Fore.MAGENTA)

if __name__ == "__main__":
    main()