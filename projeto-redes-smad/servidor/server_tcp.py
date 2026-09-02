#!/usr/bin/env python3
"""
SMAD - Sistema de Monitoramento Ambiental Distribuido
Servidor TCP MULTITHREAD (roda na VM1 - Gateway)

Regra de negocio:
  Cada cliente (VM2/VM3) representa uma estacao de sensores que envia
  leituras de temperatura e umidade. O servidor:
    1. valida a leitura,
    2. calcula o Indice de Risco de Mofo (processamento custoso, simulado
       com time.sleep) ,
    3. mantem o historico por estacao e devolve estatisticas acumuladas.

Cada conexao e atendida por uma thread propria, o que permite que VM2 e VM3
sejam servidas simultaneamente. Os logs mostram o nome da thread e o horario
para evidenciar o paralelismo.

Protocolo: JSON delimitado por '\n' (uma requisicao por linha).
"""

import json
import socket
import threading
import time
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000
TEMPO_PROCESSAMENTO = 3  # segundos - evidencia o multithreading

# Estado compartilhado entre as threads -> precisa de lock
historico = {}  # {"192.168.10.101": [22.5, 23.1, ...]}
lock = threading.Lock()


def log(msg):
    """Log com horario e nome da thread - e o que prova o paralelismo."""
    agora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{agora}] [{threading.current_thread().name}] {msg}", flush=True)


def calcular_indice_mofo(temperatura, umidade):
    """
    Processamento pesado simulado.
    O sleep e proposital: sem ele as requisicoes terminariam rapido demais
    e o paralelismo nao seria visivel no log.
    """
    log(
        f"Processando leitura (T={temperatura}C, U={umidade}%)... "
        f"aguardando {TEMPO_PROCESSAMENTO}s"
    )
    time.sleep(TEMPO_PROCESSAMENTO)

    # Regra: mofo prolifera com umidade alta e temperatura amena/quente
    if umidade < 60:
        indice = 0.0
    else:
        fator_umidade = (umidade - 60) / 40.0  # 0.0 a 1.0
        fator_temp = 1.0 if 20 <= temperatura <= 30 else 0.5
        indice = round(fator_umidade * fator_temp, 2)

    if indice >= 0.7:
        nivel = "CRITICO"
    elif indice >= 0.4:
        nivel = "ALERTA"
    else:
        nivel = "NORMAL"

    return indice, nivel


def validar(payload):
    """Valida o payload recebido. Levanta ValueError se estiver errado."""
    for campo in ("estacao", "temperatura", "umidade"):
        if campo not in payload:
            raise ValueError(f"campo obrigatorio ausente: {campo}")
    t, u = payload["temperatura"], payload["umidade"]
    if not (-50 <= t <= 80):
        raise ValueError(f"temperatura fora de faixa: {t}")
    if not (0 <= u <= 100):
        raise ValueError(f"umidade fora de faixa: {u}")
    return t, u


def atender_cliente(conn, addr):
    """Executada em uma thread dedicada por conexao."""
    ip = addr[0]
    log(f"Conexao ACEITA de {ip}:{addr[1]}")

    try:
        with conn, conn.makefile("r", encoding="utf-8") as leitor:
            for linha in leitor:  # uma requisicao por linha
                linha = linha.strip()
                if not linha:
                    continue

                try:
                    payload = json.loads(linha)
                    temperatura, umidade = validar(payload)
                except (json.JSONDecodeError, ValueError) as e:
                    erro = {"status": "erro", "mensagem": str(e)}
                    conn.sendall((json.dumps(erro) + "\n").encode("utf-8"))
                    log(f"Requisicao invalida de {ip}: {e}")
                    continue

                indice, nivel = calcular_indice_mofo(temperatura, umidade)

                # secao critica: atualiza o estado compartilhado
                with lock:
                    historico.setdefault(ip, []).append(temperatura)
                    leituras = list(historico[ip])
                    total_estacoes = len(historico)

                resposta = {
                    "status": "ok",
                    "estacao": payload["estacao"],
                    "ip_origem": ip,
                    "indice_risco_mofo": indice,
                    "nivel_alerta": nivel,
                    "estatisticas": {
                        "total_leituras": len(leituras),
                        "media_temperatura": round(sum(leituras) / len(leituras), 2),
                        "temp_minima": min(leituras),
                        "temp_maxima": max(leituras),
                    },
                    "estacoes_conectadas": total_estacoes,
                    "thread_servidor": threading.current_thread().name,
                    "processado_em": datetime.now().strftime("%H:%M:%S"),
                }

                conn.sendall((json.dumps(resposta) + "\n").encode("utf-8"))
                log(f"Resposta enviada a {ip} -> {nivel} (indice {indice})")

    except (ConnectionResetError, BrokenPipeError):
        log(f"Conexao com {ip} encerrada abruptamente")
    except Exception as e:
        log(f"Erro inesperado com {ip}: {e}")
    finally:
        log(f"Conexao ENCERRADA com {ip}")


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(10)

    print("=" * 62)
    print(f"  SMAD - Servidor TCP MULTITHREAD ouvindo em {HOST}:{PORT}")
    print(f"  Tempo de processamento simulado: {TEMPO_PROCESSAMENTO}s")
    print("  Ctrl+C para encerrar")
    print("=" * 62, flush=True)

    contador = 0
    try:
        while True:
            conn, addr = servidor.accept()
            contador += 1
            t = threading.Thread(
                target=atender_cliente,
                args=(conn, addr),
                name=f"Worker-TCP-{contador}",
                daemon=True,
            )
            t.start()
            log(f"Thread criada. Threads ativas: {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\nEncerrando servidor TCP...")
    finally:
        servidor.close()


if __name__ == "__main__":
    main()
