import socket
import json
import time
import argparse
import os

from colorama import init, Fore, Style

from text_processor import tokenize_sentences, process_sentence

init(autoreset=True)


def send_msg(sock: socket.socket, payload: dict) -> None:
    """Serializa el mensaje como JSON + newline y lo envía."""
    sock.send(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-Sockets: Nodo de Procesamiento")
    parser.add_argument("--host",    default="127.0.0.1")
    parser.add_argument("--port",    type=int,   default=9000)
    parser.add_argument("--corpus",  required=True, help="Ruta al archivo de texto")
    parser.add_argument("--node-id", required=True, help="Nombre del nodo (ej: quijote)")
    parser.add_argument("--delay",   type=float, default=0.05,
                        help="Delay entre eventos en segundos (default: 0.05)")
    args = parser.parse_args()

    # ── Banner ───────────────────────────────────────────────────────────────
    print(f"\n{Fore.CYAN}{'═' * 60}")
    print(f"   MIDI-SOCKETS  —  Nodo: {args.node_id.upper()}")
    print(f"   Corpus: {args.corpus}")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

    # ── Cargar corpus ────────────────────────────────────────────────────────
    if not os.path.exists(args.corpus):
        print(f"{Fore.RED}✖  No se encontró el archivo: {args.corpus}{Style.RESET_ALL}")
        return

    with open(args.corpus, "r", encoding="utf-8") as f:
        text = f.read()

    sentences = tokenize_sentences(text)
    print(f"{Fore.GREEN}✔  Corpus cargado: {len(sentences)} oraciones{Style.RESET_ALL}\n")

    # ── Conectar al servidor ─────────────────────────────────────────────────
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((args.host, args.port))
        except ConnectionRefusedError:
            print(
                f"{Fore.RED}✖  No se pudo conectar a {args.host}:{args.port}"
                f"  — ¿Está corriendo el servidor?{Style.RESET_ALL}"
            )
            return

        # Handshake
        send_msg(sock, {
            "type":    "connect",
            "node_id": args.node_id,
            "corpus":  os.path.basename(args.corpus),
        })
        raw_ack = sock.recv(1024).decode("utf-8").strip()
        ack = json.loads(raw_ack)
        print(f"{Fore.GREEN}✔  Conectado al servidor  |  ack: {ack['status']}{Style.RESET_ALL}\n")

        # ── Procesar y enviar eventos ────────────────────────────────────────
        total_events = 0
        for s_idx, sentence in enumerate(sentences):
            word_events = process_sentence(sentence)
            for word, raw_val, midi_val in word_events:
                event = {
                    "type":         "event",
                    "node_id":      args.node_id,
                    "sentence_idx": s_idx,
                    "word":         word,
                    "raw_value":    round(raw_val, 4),
                    "midi_value":   midi_val,
                    "timestamp":    round(time.time(), 4),
                }
                send_msg(sock, event)
                print(
                    f"  [{args.node_id.upper()}] "
                    f"oración:{s_idx:03d}  "
                    f"'{word:<12}'  "
                    f"raw:{raw_val:8.2f}  "
                    f"MIDI:{midi_val:3d}"
                )
                total_events += 1
                time.sleep(args.delay)

        # Señal de fin
        send_msg(sock, {
            "type":         "done",
            "node_id":      args.node_id,
            "total_events": total_events,
        })

    print(f"\n{Fore.GREEN}✔  Completado: {total_events} eventos enviados{Style.RESET_ALL}")


if __name__ == "__main__":
    main()
