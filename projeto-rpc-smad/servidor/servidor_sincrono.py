#!/usr/bin/env python3
"""
SMAD-RPC - Servidor RPC sincrono multithread (VM1). Parte I do trabalho.

O cliente bloqueia ate a operacao terminar, mas ThreadingMixIn cria uma thread
por requisicao, entao VM2 e VM3 sao atendidas ao mesmo tempo.

Uso:
    python3 servidor_sincrono.py                 # multithread (padrao)
    python3 servidor_sincrono.py --sequencial    # 1 thread, enfileira
    python3 servidor_sincrono.py --porta 5002
"""

import argparse
import itertools
import threading
from datetime import datetime
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import operacoes
from operacoes import log

HOST = "0.0.0.0"
PORTA_PADRAO = 5002

# Estado compartilhado entre as threads -> protegido por lock.
estatisticas = {"chamadas": 0, "por_operacao": {}, "clientes": set()}
lock = threading.Lock()


class Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2", "/")

    def log_message(self, formato, *args):
        return


class ServidorMultithread(ThreadingMixIn, SimpleXMLRPCServer):
    """Uma thread por requisicao."""
    daemon_threads = True
    allow_reuse_address = True
    _contador = itertools.count(1)

    def process_request_thread(self, request, client_address):
        threading.current_thread().name = f"Worker-SYNC-{next(self._contador)}"
        super().process_request_thread(request, client_address)


class ServidorSequencial(SimpleXMLRPCServer):
    """Sem ThreadingMixIn: uma requisicao por vez. So para a demonstracao."""
    allow_reuse_address = True


def registrar(nome, ip_cliente):
    with lock:
        estatisticas["chamadas"] += 1
        estatisticas["por_operacao"][nome] = (
            estatisticas["por_operacao"].get(nome, 0) + 1
        )
        if ip_cliente:
            estatisticas["clientes"].add(ip_cliente)
        return estatisticas["chamadas"]


def envolver(funcao, nome):
    """Registra entrada/saida e o IP de origem em volta da operacao."""
    def wrapper(*args):
        ip = getattr(CONTEXTO, "ip_cliente", None)
        n = registrar(nome, ip)
        log(f"#{n} RECEBIDA chamada SINCRONA {nome} de {ip or '?'}")
        try:
            resultado = funcao(*args)
            log(f"#{n} RESPONDENDO {nome} para {ip or '?'}")
            return resultado
        except Exception as e:
            log(f"#{n} ERRO em {nome}: {e}")
            raise
    return wrapper


CONTEXTO = threading.local()


class HandlerComIP(Handler):
    def do_POST(self):
        CONTEXTO.ip_cliente = self.client_address[0]
        return super().do_POST()


def status_servidor():
    with lock:
        return {
            "servidor": "SMAD-RPC SINCRONO",
            "modo": MODO,
            "chamadas_atendidas": estatisticas["chamadas"],
            "por_operacao": dict(estatisticas["por_operacao"]),
            "clientes_distintos": len(estatisticas["clientes"]),
            "threads_ativas": threading.active_count(),
            "horario": datetime.now().strftime("%H:%M:%S"),
        }


MODO = "MULTITHREAD"


def main():
    global MODO

    parser = argparse.ArgumentParser(description="Servidor RPC sincrono SMAD")
    parser.add_argument("--porta", type=int, default=PORTA_PADRAO)
    parser.add_argument(
        "--sequencial",
        action="store_true",
        help="roda com uma unica thread (demonstra o enfileiramento)",
    )
    args = parser.parse_args()

    MODO = "SEQUENCIAL (1 thread)" if args.sequencial else "MULTITHREAD"
    Classe = ServidorSequencial if args.sequencial else ServidorMultithread

    servidor = Classe(
        (HOST, args.porta),
        requestHandler=HandlerComIP,
        allow_none=True,
        logRequests=False,
    )
    servidor.register_introspection_functions()

    for nome, funcao in operacoes.OPERACOES.items():
        servidor.register_function(envolver(funcao, nome), nome)
    servidor.register_function(status_servidor, "status_servidor")

    print("=" * 66)
    print(f"  SMAD - SERVIDOR RPC SINCRONO  [{MODO}]")
    print(f"  Escutando em {HOST}:{args.porta}  (XML-RPC sobre HTTP)")
    print("  Operacoes: calcular_indice_mofo | gerar_relatorio | analisar_colecao")
    print("  Ctrl+C para encerrar")
    print("=" * 66, flush=True)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor sincrono...")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
