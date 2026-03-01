import socket
import threading
import json
import argparse
from datetime import datetime

from colorama import init, Fore, Style

init(autoreset=True)

# ── Configuración por defecto
DEFAULT_HOST = "0.0.0.0"     
DEFAULT_PORT = 9000

# Colores por node_id 
NODE_COLOR_MAP = {
    "quijote": Fore.CYAN,
    "cid":     Fore.YELLOW,
    "monitor": Fore.MAGENTA, # Agregamos un color para el futuro monitor
}
FALLBACK_COLORS = [Fore.GREEN, Fore.BLUE, Fore.WHITE]

# ── Estado compartido 
lock            = threading.Lock()
clients: dict[str, socket.socket]  = {} # node_events por un mapa de clientes conectados
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

            # ── CONNECT 
            if mtype == "connect":
                node_id = msg.get("node_id", "unknown")
                color   = get_node_color(node_id)
                
                # Guardamos el socket del cliente para poder enrutarle mensajes luego
                with lock:
                    clients[node_id] = conn
                    
                log(
                    f"[{node_id.upper()}] Nodo conectado  |  corpus: {msg.get('corpus', '?')}",
                    color,
                )
                conn.send(json.dumps({"type": "ack", "status": "ok"}).encode() + b"\n")

            # ── ENRUTADOR DE MENSAJES (Reemplaza la lógica de negocio) ───
            else:
                target = msg.get("target") # Leemos a quién va dirigido el mensaje
                
                with lock:
                    if target and target in clients:
                        # Reenvío privado (ej. un procesador enviando un evento al monitor)
                        clients[target].send((line + "\n").encode("utf-8"))
                    else:
                        # Broadcast: Si no hay un target específico, se reenvía a todos los demás
                        for cid, c_conn in clients.items():
                            if cid != node_id:
                                try:
                                    c_conn.send((line + "\n").encode("utf-8"))
                                except:
                                    pass

    except Exception as exc:
        log(f"Error en {addr}: {exc}", Fore.RED)
    finally:
        # Limpiamos al cliente cuando se desconecta
        if node_id:
            with lock:
                if node_id in clients:
                    del clients[node_id]
        conn.close()
        label = node_id.upper() if node_id else str(addr)
        log(f"[{label}] Conexión cerrada", Fore.RED)


def main() -> None:
    parser = argparse.ArgumentParser(description="MIDI-Sockets: Nodo Central")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    print(f"\n{Fore.MAGENTA}{'═' * 60}")
    print("   MIDI-SOCKETS  —  Nodo Central (Enrutador Puro)")
    print("   Sistemas Distribuidos 2526-2  |  UNIMET")
    print(f"{'═' * 60}{Style.RESET_ALL}\n")

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