#!/usr/bin/env python3
"""
SMAD-RPC - Servidor RPC assincrono (VM1). Parte II do trabalho.

Padrao ticket: submeter() agenda a operacao no pool de threads e devolve na
hora um job_id, sem esperar o processamento; depois o cliente chama
consultar(job_id) para pegar o resultado. As operacoes sao as mesmas do
servidor sincrono (operacoes.py) e nao ficam mais rapidas por serem assincronas.

Uso:
    python3 servidor_assincrono.py                # pool de 8 threads
    python3 servidor_assincrono.py --workers 1    # pool de 1 thread (demo)
    python3 servidor_assincrono.py --porta 5003
"""

import argparse
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

import operacoes
from operacoes import log

HOST = "0.0.0.0"
PORTA_PADRAO = 5003
WORKERS_PADRAO = 8

PENDENTE = "PENDENTE"
EXECUTANDO = "EXECUTANDO"
CONCLUIDO = "CONCLUIDO"
ERRO = "ERRO"

# Estado compartilhado: tabela de jobs. Varias threads mexem nela -> lock.
jobs = {}
lock = threading.Lock()
executor = None  # criado no main()


class Handler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2", "/")

    def log_message(self, formato, *args):
        return

    def do_POST(self):
        CONTEXTO.ip_cliente = self.client_address[0]
        return super().do_POST()


class ServidorMultithread(ThreadingMixIn, SimpleXMLRPCServer):
    """Uma thread por requisicao: aceitar submissoes nunca enfileira."""
    daemon_threads = True
    allow_reuse_address = True


CONTEXTO = threading.local()


def _executar(job_id, nome, argumentos):
    """Roda dentro de uma thread do pool."""
    with lock:
        jobs[job_id]["estado"] = EXECUTANDO
        jobs[job_id]["iniciado_em"] = datetime.now().strftime("%H:%M:%S")

    log(f"[{job_id[:8]}] INICIANDO {nome}{tuple(argumentos)}")
    try:
        resultado = operacoes.OPERACOES[nome](*argumentos)
        with lock:
            jobs[job_id]["estado"] = CONCLUIDO
            jobs[job_id]["resultado"] = resultado
            jobs[job_id]["concluido_em"] = datetime.now().strftime("%H:%M:%S")
        log(f"[{job_id[:8]}] CONCLUIDO {nome} - resultado disponivel")
    except Exception as e:
        with lock:
            jobs[job_id]["estado"] = ERRO
            jobs[job_id]["erro"] = f"{type(e).__name__}: {e}"
            jobs[job_id]["concluido_em"] = datetime.now().strftime("%H:%M:%S")
        log(f"[{job_id[:8]}] ERRO em {nome}: {e}")


def submeter(nome, argumentos=None):
    """Agenda a operacao no pool e devolve o job_id imediatamente."""
    argumentos = list(argumentos or [])
    if nome not in operacoes.OPERACOES:
        raise ValueError(
            f"operacao desconhecida: {nome}. "
            f"Disponiveis: {', '.join(operacoes.OPERACOES)}"
        )

    ip = getattr(CONTEXTO, "ip_cliente", None)
    job_id = str(uuid.uuid4())

    with lock:
        jobs[job_id] = {
            "job_id": job_id,
            "operacao": nome,
            "argumentos": argumentos,
            "estado": PENDENTE,
            "resultado": None,
            "erro": None,
            "cliente": ip,
            "submetido_em": datetime.now().strftime("%H:%M:%S"),
            "iniciado_em": None,
            "concluido_em": None,
        }

    executor.submit(_executar, job_id, nome, argumentos)
    log(f"[{job_id[:8]}] ACEITA submissao ASSINCRONA de {nome} por {ip or '?'}"
        f" - respondendo o ticket na hora")
    return job_id


def consultar(job_id):
    """Estado atual do job, com o resultado se ja terminou. Nao bloqueia."""
    with lock:
        job = jobs.get(job_id)
        if job is None:
            raise ValueError(f"job desconhecido: {job_id}")
        return dict(job)


def listar_jobs():
    with lock:
        return [
            {
                "job_id": j["job_id"][:8],
                "operacao": j["operacao"],
                "estado": j["estado"],
                "cliente": j["cliente"],
                "submetido_em": j["submetido_em"],
                "concluido_em": j["concluido_em"],
            }
            for j in jobs.values()
        ]


def status_servidor():
    with lock:
        total = len(jobs)
        por_estado = {}
        for j in jobs.values():
            por_estado[j["estado"]] = por_estado.get(j["estado"], 0) + 1
        clientes = {j["cliente"] for j in jobs.values() if j["cliente"]}
    return {
        "servidor": "SMAD-RPC ASSINCRONO",
        "workers_no_pool": WORKERS,
        "jobs_totais": total,
        "por_estado": por_estado,
        "clientes_distintos": len(clientes),
        "threads_ativas": threading.active_count(),
        "horario": datetime.now().strftime("%H:%M:%S"),
    }


WORKERS = WORKERS_PADRAO


def main():
    global executor, WORKERS

    parser = argparse.ArgumentParser(description="Servidor RPC assincrono SMAD")
    parser.add_argument("--porta", type=int, default=PORTA_PADRAO)
    parser.add_argument(
        "--workers",
        type=int,
        default=WORKERS_PADRAO,
        help="threads no pool de execucao (use 1 para demonstrar a fila)",
    )
    args = parser.parse_args()

    WORKERS = args.workers
    executor = ThreadPoolExecutor(
        max_workers=args.workers, thread_name_prefix="Worker-RPC"
    )

    servidor = ServidorMultithread(
        (HOST, args.porta),
        requestHandler=Handler,
        allow_none=True,
        logRequests=False,
    )
    servidor.register_introspection_functions()
    servidor.register_function(submeter, "submeter")
    servidor.register_function(consultar, "consultar")
    servidor.register_function(listar_jobs, "listar_jobs")
    servidor.register_function(status_servidor, "status_servidor")

    print("=" * 66)
    print("  SMAD - SERVIDOR RPC ASSINCRONO  [pool de threads]")
    print(f"  Escutando em {HOST}:{args.porta}  (XML-RPC sobre HTTP)")
    print(f"  Workers no pool: {args.workers}")
    print("  Metodos: submeter | consultar | listar_jobs | status_servidor")
    print("  Ctrl+C para encerrar")
    print("=" * 66, flush=True)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor assincrono...")
    finally:
        executor.shutdown(wait=False)
        servidor.server_close()


if __name__ == "__main__":
    main()
