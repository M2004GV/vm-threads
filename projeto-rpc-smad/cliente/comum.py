#!/usr/bin/env python3
"""SMAD-RPC - Utilitarios compartilhados pelos clientes (VM2 e VM3)."""

import argparse
import random
import socket
import sys
import time
from datetime import datetime
from xmlrpc.client import ServerProxy

# Evita UnicodeEncodeError se a VM estiver com locale C/POSIX.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SERVIDOR_PADRAO = "192.168.50.1"   # VM1 na Rede B (interface enp0s8)
PORTA_SINCRONA = 5002
PORTA_ASSINCRONA = 5003

_INICIO = None


def iniciar_cronometro():
    global _INICIO
    _INICIO = time.time()


def log(msg):
    """Formato do enunciado (HH:MM:SS - evento), com o offset desde o inicio."""
    agora = datetime.now().strftime("%H:%M:%S")
    if _INICIO is None:
        print(f"{agora} - {msg}", flush=True)
    else:
        delta = time.time() - _INICIO
        print(f"{agora} - {msg}".ljust(72) + f"(t+{delta:6.2f}s)", flush=True)


def separador(titulo=""):
    if titulo:
        print("\n" + "=" * 86)
        print(f"  {titulo}")
        print("=" * 86, flush=True)
    else:
        print("-" * 86, flush=True)


def argumentos(descricao, porta_padrao):
    parser = argparse.ArgumentParser(description=descricao)
    parser.add_argument("--servidor", default=SERVIDOR_PADRAO,
                        help=f"IP da VM1 (padrão: {SERVIDOR_PADRAO})")
    parser.add_argument("--porta", type=int, default=porta_padrao)
    parser.add_argument("--nome", default=None,
                        help="nome do cliente (padrão: hostname da VM)")
    parser.add_argument("--dias", type=int, default=10,
                        help="parâmetro da operação demorada: 1s por dia")
    parser.add_argument("--leituras", type=int, default=10,
                        help="tamanho da coleção: 0,5s por leitura")
    args = parser.parse_args()
    if not args.nome:
        args.nome = socket.gethostname().upper()
    return args


def conectar(args):
    """Cria o proxy RPC e confirma que o servidor responde."""
    url = f"http://{args.servidor}:{args.porta}/RPC2"
    proxy = ServerProxy(url, allow_none=True)
    try:
        status = proxy.status_servidor()
    except Exception as e:
        print(f"\n[FALHA] Não foi possível falar com {url}")
        print(f"        {type(e).__name__}: {e}")
        print("        Confira: o servidor está rodando na VM1?")
        print(f"        Teste a rota:  ping -c 2 {args.servidor}")
        sys.exit(1)
    return proxy, status, url


def leituras_simuladas(quantidade):
    return [round(random.uniform(18.0, 34.0), 1) for _ in range(quantidade)]


def resumo(resultado):
    if not isinstance(resultado, dict):
        return str(resultado)
    op = resultado.get("operacao")
    if op == "calcular_indice_mofo":
        return (f"índice={resultado['indice_risco_mofo']} "
                f"nível={resultado['nivel_alerta']}")
    if op == "gerar_relatorio":
        return (f"{resultado['registros_consolidados']} registros em "
                f"{resultado['duracao_segundos']}s "
                f"[thread {resultado['thread_servidor']}]")
    if op == "analisar_colecao":
        return (f"n={resultado['total_leituras']} média={resultado['media']} "
                f"máx={resultado['maior']} mín={resultado['menor']} "
                f"desvio={resultado['desvio_padrao']} "
                f"[thread {resultado['thread_servidor']}]")
    return str(resultado)


class FuturoRPC:
    """O "future" do lado do cliente: guarda o ticket e so busca o resultado no get()."""

    def __init__(self, proxy, job_id, descricao=""):
        self.proxy = proxy
        self.job_id = job_id
        self.descricao = descricao
        self.submetido_em = time.time()
        self._resultado = None
        self._concluido = False

    @property
    def curto(self):
        return self.job_id[:8]

    def estado(self):
        if self._concluido:
            return "CONCLUIDO"
        return self.proxy.consultar(self.job_id)["estado"]

    def pronto(self):
        return self.estado() in ("CONCLUIDO", "ERRO")

    def get(self, timeout=180, intervalo=0.05, intervalo_max=0.5):
        """Unico ponto onde o cliente bloqueia. Intervalo dobra ate o teto, para nao martelar o servidor."""
        if self._concluido:
            return self._resultado

        limite = time.time() + timeout
        while time.time() < limite:
            job = self.proxy.consultar(self.job_id)
            if job["estado"] == "CONCLUIDO":
                self._resultado = job["resultado"]
                self._concluido = True
                return self._resultado
            if job["estado"] == "ERRO":
                raise RuntimeError(f"job {self.curto} falhou: {job['erro']}")
            time.sleep(intervalo)
            intervalo = min(intervalo * 2, intervalo_max)
        raise TimeoutError(f"job {self.curto} excedeu {timeout}s")

    def espera_total(self):
        return round(time.time() - self.submetido_em, 2)
