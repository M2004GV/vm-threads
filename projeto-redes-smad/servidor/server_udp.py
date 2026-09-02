#!/usr/bin/env python3
"""
SMAD - Sistema de Monitoramento Ambiental Distribuido
Servidor UDP MULTITHREAD (roda na VM1 - Gateway)

Regra de negocio:
  Servico de consulta rapida, sem conexao. Os clientes consultam:
    - CONSULTA_STATUS : situacao geral da rede de sensores
    - CONSULTA_ALERTA : verifica se uma leitura dispara alerta, sem gravar
    - PING            : mede latencia

Como UDP nao tem conexao, o socket e unico. O paralelismo aparece porque
cada datagrama recebido e despachado para uma thread propria, entao varias
consultas de VM2 e VM3 sao processadas ao mesmo tempo em vez de enfileiradas.

Protocolo: um datagrama = uma mensagem JSON.
"""

import json
import socket
import threading
import time
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5001
TEMPO_PROCESSAMENTO = 2  # segundos - evidencia o multithreading

# Estado compartilhado entre as threads -> precisa de lock
estatisticas = {
    "total_requisicoes": 0,
    "por_comando": {},
    "clientes_vistos": set(),
    "inicio": datetime.now(),
}
lock = threading.Lock()


def log(msg):
    agora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{agora}] [{threading.current_thread().name}] {msg}", flush=True)


def processar(sock, dados, addr):
    """Executada em uma thread dedicada por datagrama recebido."""
    ip = addr[0]
    try:
        requisicao = json.loads(dados.decode("utf-8"))
    except json.JSONDecodeError:
        sock.sendto(b'{"status":"erro","mensagem":"JSON invalido"}', addr)
        return

    comando = requisicao.get("comando", "PING")
    msg_id = requisicao.get("msg_id")
    log(f"Recebido {comando} (msg {msg_id}) de {ip} - processando "
        f"{TEMPO_PROCESSAMENTO}s...")

    # processamento custoso simulado
    time.sleep(TEMPO_PROCESSAMENTO)

    # secao critica: atualiza contadores compartilhados
    with lock:
        estatisticas["total_requisicoes"] += 1
        estatisticas["por_comando"][comando] = \
            estatisticas["por_comando"].get(comando, 0) + 1
        estatisticas["clientes_vistos"].add(ip)
        total = estatisticas["total_requisicoes"]
        por_comando = dict(estatisticas["por_comando"])
        clientes = sorted(estatisticas["clientes_vistos"])
        uptime = int((datetime.now() - estatisticas["inicio"]).total_seconds())

    if comando == "CONSULTA_STATUS":
        corpo = {
            "servidor": "SMAD-UDP",
            "uptime_segundos": uptime,
            "total_requisicoes": total,
            "requisicoes_por_comando": por_comando,
            "clientes_distintos": clientes,
        }

    elif comando == "CONSULTA_ALERTA":
        t = requisicao.get("temperatura", 0)
        u = requisicao.get("umidade", 0)
        risco = u >= 70 and 20 <= t <= 30
        corpo = {
            "temperatura": t,
            "umidade": u,
            "alerta": "SIM" if risco else "NAO",
            "recomendacao": ("Ativar desumidificador" if risco
                             else "Condicoes normais"),
        }

    else:  # PING
        corpo = {"resposta": "PONG", "eco": requisicao.get("dados")}

    resposta = {
        "status": "ok",
        "comando": comando,
        "msg_id": msg_id,
        "thread_servidor": threading.current_thread().name,
        "respondido_em": datetime.now().strftime("%H:%M:%S"),
        **corpo,
    }

    sock.sendto(json.dumps(resposta).encode("utf-8"), addr)
    log(f"Resposta {comando} (msg {msg_id}) enviada a {ip} "
        f"[requisicao #{total}]")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))

    print("=" * 62)
    print(f"  SMAD - Servidor UDP MULTITHREAD ouvindo em {HOST}:{PORT}")
    print(f"  Tempo de processamento simulado: {TEMPO_PROCESSAMENTO}s")
    print("  Ctrl+C para encerrar")
    print("=" * 62, flush=True)

    contador = 0
    try:
        while True:
            dados, addr = sock.recvfrom(4096)
            contador += 1
            t = threading.Thread(
                target=processar,
                args=(sock, dados, addr),
                name=f"Worker-UDP-{contador}",
                daemon=True,
            )
            t.start()
    except KeyboardInterrupt:
        print("\nEncerrando servidor UDP...")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
