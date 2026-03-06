import socket
import json
import time
import argparse
import os

from colorama import init, Fore, Style
from text_processor import tokenize_sentences, process_sentence

init(autoreset=True)

def send_msg(sock: socket.socket, payload: dict) -> None:
    sock.send(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")

def recv_lines(sock: socket.socket):
    """Generador para leer mensajes completos del socket."""
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
    parser = argparse.ArgumentParser(description="MIDI-Sockets: Nodo de Procesamiento")
    parser.add_argument("--host",    default="127.0.0.1")
    parser.add_argument("--port",    type=int,   default=9000)
    parser.add_argument("--node-id", required=True, help="Nombre del nodo (ej: quijote)")
    parser.add_argument("--delay",   type=float, default=0.05)
    args = parser.parse_args()

    print(f"\n{Fore.CYAN}{'═' * 60}")
    print(f"   MIDI-SOCKETS  —  Nodo: {args.node_id.upper()}")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((args.host, args.port))
        except ConnectionRefusedError:
            print(f"{Fore.RED}✖  No se pudo conectar al servidor.{Style.RESET_ALL}")
            return

        #  sin enviar el corpus aún
        send_msg(sock, {
            "type":    "connect",
            "node_id": args.node_id,
        })
        
        print(f"{Fore.YELLOW}Esperando configuración del Orquestador (Monitor)...{Style.RESET_ALL}")

        # Bucle de espera
        for line in recv_lines(sock):
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            if msg.get("type") == "ack":
                print(f"{Fore.GREEN}✔  Conectado al servidor central.{Style.RESET_ALL}")
                continue

            # ORDEN DE INICIO 
            if msg.get("type") == "config":
                corpus_path = msg.get("corpus")
                print(f"\n{Fore.GREEN}✔  Configuración recibida. Corpus asignado: {corpus_path}{Style.RESET_ALL}")

                if not os.path.exists(corpus_path):
                    print(f"{Fore.RED}✖  No se encontró el archivo: {corpus_path}{Style.RESET_ALL}")
                    return

                with open(corpus_path, "r", encoding="utf-8") as f:
                    text = f.read()

                sentences = tokenize_sentences(text)
                print(f"{Fore.CYAN}Iniciando procesamiento de {len(sentences)} oraciones...{Style.RESET_ALL}\n")

                total_events = 0
                for s_idx, sentence in enumerate(sentences):
                    word_events = process_sentence(sentence)
                    for word, raw_val, midi_val in word_events:
                        event = {
                            "type":         "event",
                            "target":       "monitor",
                            "node_id":      args.node_id,
                            "sentence_idx": s_idx,
                            "word":         word,
                            "raw_value":    round(raw_val, 4),
                            "midi_value":   midi_val,
                            "timestamp":    round(time.time(), 4),
                        }
                        send_msg(sock, event)
                        print(
                            f"  [{args.node_id.upper()}] oración:{s_idx:03d}  "
                            f"'{word:<12}'  raw:{raw_val:8.2f}  MIDI:{midi_val:3d}"
                        )
                        total_events += 1
                        time.sleep(args.delay)

                # Señal de fin
                send_msg(sock, {
                    "type":         "done",
                    "target":       "monitor",
                    "node_id":      args.node_id,
                    "total_events": total_events,
                })
                print(f"\n{Fore.GREEN}✔  Completado: {total_events} eventos enviados{Style.RESET_ALL}")
                break # Termina el cliente luego de enviar todo

if __name__ == "__main__":
    main()