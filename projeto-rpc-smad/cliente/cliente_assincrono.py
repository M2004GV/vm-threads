#!/usr/bin/env python3
"""
SMAD-RPC - Cliente RPC assincrono (VM2 e VM3). Parte II do trabalho.

Espelha o pseudocódigo do enunciado: submete, segue com atividades locais e
só bloqueia no futuro.get(). No log, esse intervalo é preenchido com trabalho
local; no cliente síncrono ele é um buraco vazio.

Uso:
    python3 cliente_assincrono.py
    python3 cliente_assincrono.py --nome CLIENTE-1 --dias 10
    python3 cliente_assincrono.py --servidor 192.168.10.1 --porta 5003
"""

import time

import comum
from comum import FuturoRPC, log, resumo, separador

# Atividades locais do SMAD executadas enquanto o servidor processa.
ATIVIDADES_LOCAIS = [
    ("Calibrando sensor de temperatura", 2.0),
    ("Verificando bateria da estação", 2.0),
    ("Gravando buffer local em disco", 2.0),
    ("Checando rota até o gateway", 2.0),
]


def main():
    args = comum.argumentos(
        "Cliente RPC ASSÍNCRONO do SMAD", comum.PORTA_ASSINCRONA
    )
    proxy, status, url = comum.conectar(args)

    separador(f"CLIENTE {args.nome}  —  RPC ASSÍNCRONA  —  {url}")
    print(f"  Servidor: {status['servidor']}  "
          f"[pool de {status['workers_no_pool']} threads]")
    print("  Este cliente NÃO bloqueia na submissão.\n", flush=True)

    comum.iniciar_cronometro()
    inicio_geral = time.time()

    log("Solicitando processamento...")

    log(f"Requisição assíncrona enviada: gerar_relatorio({args.dias})")
    futuro_relatorio = FuturoRPC(
        proxy,
        proxy.submeter("gerar_relatorio", [args.dias]),
        f"gerar_relatorio({args.dias})",
    )
    log(f"Ticket recebido na hora: {futuro_relatorio.curto} "
        f"(o servidor ainda está processando)")

    leituras = comum.leituras_simuladas(args.leituras)
    log(f"Requisição assíncrona enviada: analisar_colecao({args.leituras})")
    futuro_colecao = FuturoRPC(
        proxy,
        proxy.submeter("analisar_colecao", [leituras]),
        f"analisar_colecao({args.leituras} leituras)",
    )
    log(f"Ticket recebido na hora: {futuro_colecao.curto}")

    separador()
    log("Cliente continuou sua execução")

    for i, (descricao, duracao) in enumerate(ATIVIDADES_LOCAIS, start=1):
        log(f"Executando atividade local {i}: {descricao}")
        time.sleep(duracao)
    log("Atividades locais concluídas")

    log("Estado dos jobs no servidor: "
        f"{futuro_relatorio.curto}={futuro_relatorio.estado()} | "
        f"{futuro_colecao.curto}={futuro_colecao.estado()}")
    separador()

    log(f"Buscando resultado de {futuro_colecao.descricao}")
    resultado_colecao = futuro_colecao.get()
    log("Resultado RPC disponível")
    log(f"Resultado: {resumo(resultado_colecao)}")
    log(f"Espera do cliente após o get(): "
        f"{futuro_colecao.espera_total()}s desde a submissão")
    separador()

    log(f"Buscando resultado de {futuro_relatorio.descricao}")
    resultado_relatorio = futuro_relatorio.get()
    log("Resultado RPC disponível")
    log(f"Resultado: {resumo(resultado_relatorio)}")
    log(f"Espera do cliente após o get(): "
        f"{futuro_relatorio.espera_total()}s desde a submissão")

    separador()
    log("Chamada rápida de encerramento: calcular_indice_mofo(26.5, 82.0)")
    futuro_rapido = FuturoRPC(
        proxy, proxy.submeter("calcular_indice_mofo", [26.5, 82.0])
    )
    log(f"Resultado: {resumo(futuro_rapido.get())}")

    total = time.time() - inicio_geral
    trabalho_local = sum(d for _, d in ATIVIDADES_LOCAIS)
    separador("ENCERRAMENTO")
    print(f"  Tempo total do cliente {args.nome}: {total:.2f}s")
    print(f"  Trabalho local feito durante a espera: {trabalho_local:.0f}s")
    print("  As operações remotas rodaram EM PARALELO com o trabalho local,")
    print("  e entre si, nas threads do pool do servidor.")
    print("=" * 86, flush=True)


if __name__ == "__main__":
    main()
