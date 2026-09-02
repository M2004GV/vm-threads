#!/usr/bin/env python3
"""
SMAD - Cliente TCP (roda na VM2 e na VM3)

Simula uma estacao de sensores enviando leituras periodicas ao servidor
da VM1. Mantem UMA conexao TCP aberta e envia varias leituras por ela,
o que faz a thread do servidor viver durante toda a sessao.

Uso:
    python3 client_tcp.py                    # 5 leituras, estacao pelo hostname
    python3 client_tcp.py 10                 # 10 leituras
    python3 client_tcp.py 10 ESTACAO-NORTE   # 10 leituras, nome customizado
"""

import json
import random
import socket
import sys
import time
from datetime import datetime

SERVIDOR = "192.168.10.1"
PORTA = 5000


def gerar_leitura(estacao):
    """Simula o sensor lendo o ambiente."""
    return {
        "estacao": estacao,
        "temperatura": round(random.uniform(18.0, 32.0), 1),
        "umidade": round(random.uniform(45.0, 95.0), 1),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def main():
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    estacao = sys.argv[2] if len(sys.argv) > 2 else socket.gethostname().upper()

    print("=" * 62)
    print(f"  Cliente TCP - estacao {estacao}")
    print(f"  Servidor: {SERVIDOR}:{PORTA} | leituras: {total}")
    print("=" * 62, flush=True)

    try:
        with socket.create_connection((SERVIDOR, PORTA), timeout=30) as sock:
            leitor = sock.makefile("r", encoding="utf-8")
            print(f"Conectado a {SERVIDOR}:{PORTA}\n", flush=True)

            for i in range(1, total + 1):
                leitura = gerar_leitura(estacao)
                envio = datetime.now()

                sock.sendall((json.dumps(leitura) + "\n").encode("utf-8"))
                print(f"[{envio.strftime('%H:%M:%S')}] "
                      f"--> Leitura {i}/{total} enviada: "
                      f"T={leitura['temperatura']}C U={leitura['umidade']}%",
                      flush=True)

                linha = leitor.readline()
                if not linha:
                    print("Servidor fechou a conexao.")
                    break

                resposta = json.loads(linha)
                rtt = (datetime.now() - envio).total_seconds()

                if resposta.get("status") != "ok":
                    print(f"    <-- ERRO: {resposta.get('mensagem')}\n")
                    continue

                est = resposta["estatisticas"]
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"<-- Resposta em {rtt:.2f}s "
                      f"(atendido por {resposta['thread_servidor']})")
                print(f"    Indice de mofo : {resposta['indice_risco_mofo']} "
                      f"({resposta['nivel_alerta']})")
                print(f"    Media acumulada: {est['media_temperatura']}C "
                      f"| min {est['temp_minima']}C | max {est['temp_maxima']}C "
                      f"| {est['total_leituras']} leituras")
                print(f"    Estacoes ativas no servidor: "
                      f"{resposta['estacoes_conectadas']}\n", flush=True)

                time.sleep(1)  # intervalo entre leituras do sensor

            print("Sessao encerrada.")

    except ConnectionRefusedError:
        print(f"ERRO: nao foi possivel conectar em {SERVIDOR}:{PORTA}. "
              f"O server_tcp.py esta rodando na VM1?")
        sys.exit(1)
    except socket.timeout:
        print("ERRO: tempo esgotado aguardando o servidor.")
        sys.exit(1)
    except OSError as e:
        print(f"ERRO de rede: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuario.")


if __name__ == "__main__":
    main()
