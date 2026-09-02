#!/usr/bin/env python3
"""
SMAD - Cliente UDP (roda na VM2 e na VM3)

Consulta o servico sem conexao da VM1. Alterna entre os comandos
CONSULTA_STATUS, CONSULTA_ALERTA e PING.

Modo padrao   : envia as consultas em sequencia.
Modo paralelo : dispara todas de uma vez (--paralelo), util para mostrar
                varias threads simultaneas no servidor a partir de um
                unico cliente.

Uso:
    python3 client_udp.py                 # 5 consultas sequenciais
    python3 client_udp.py 8               # 8 consultas
    python3 client_udp.py 5 --paralelo    # 5 consultas simultaneas
"""

import json
import random
import socket
import sys
import threading
from datetime import datetime

SERVIDOR = "192.168.10.1"
PORTA = 5001
TIMEOUT = 15

COMANDOS = ["CONSULTA_STATUS", "CONSULTA_ALERTA", "PING"]


def montar_requisicao(msg_id):
    comando = COMANDOS[msg_id % len(COMANDOS)]
    req = {"comando": comando, "msg_id": msg_id}
    if comando == "CONSULTA_ALERTA":
        req["temperatura"] = round(random.uniform(18.0, 32.0), 1)
        req["umidade"] = round(random.uniform(45.0, 95.0), 1)
    elif comando == "PING":
        req["dados"] = f"teste-{msg_id}"
    return req


def consultar(msg_id):
    """Envia um datagrama e aguarda a resposta."""
    req = montar_requisicao(msg_id)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    envio = datetime.now()
    try:
        sock.sendto(json.dumps(req).encode("utf-8"), (SERVIDOR, PORTA))
        print(f"[{envio.strftime('%H:%M:%S')}] --> msg {msg_id}: "
              f"{req['comando']}", flush=True)

        dados, _ = sock.recvfrom(4096)
        resp = json.loads(dados.decode("utf-8"))
        rtt = (datetime.now() - envio).total_seconds()

        print(f"[{datetime.now().strftime('%H:%M:%S')}] <-- msg {msg_id} "
              f"em {rtt:.2f}s (atendido por {resp.get('thread_servidor')})")

        if resp.get("comando") == "CONSULTA_STATUS":
            print(f"    uptime: {resp['uptime_segundos']}s | "
                  f"requisicoes: {resp['total_requisicoes']} | "
                  f"clientes: {', '.join(resp['clientes_distintos'])}")
        elif resp.get("comando") == "CONSULTA_ALERTA":
            print(f"    T={resp['temperatura']}C U={resp['umidade']}% -> "
                  f"alerta: {resp['alerta']} ({resp['recomendacao']})")
        else:
            print(f"    {resp.get('resposta')} | eco: {resp.get('eco')}")
        print(flush=True)

    except socket.timeout:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] !!! msg {msg_id}: "
              f"sem resposta em {TIMEOUT}s (datagrama perdido? "
              f"servidor no ar?)\n", flush=True)
    except OSError as e:
        print(f"ERRO de rede na msg {msg_id}: {e}", flush=True)
    finally:
        sock.close()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    paralelo = "--paralelo" in sys.argv
    total = int(args[0]) if args else 5

    print("=" * 62)
    print(f"  Cliente UDP - {socket.gethostname().upper()}")
    print(f"  Servidor: {SERVIDOR}:{PORTA} | consultas: {total} "
          f"| modo: {'PARALELO' if paralelo else 'SEQUENCIAL'}")
    print("=" * 62, flush=True)

    try:
        if paralelo:
            threads = [threading.Thread(target=consultar, args=(i,))
                       for i in range(1, total + 1)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        else:
            for i in range(1, total + 1):
                consultar(i)
        print("Consultas finalizadas.")
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")


if __name__ == "__main__":
    main()
