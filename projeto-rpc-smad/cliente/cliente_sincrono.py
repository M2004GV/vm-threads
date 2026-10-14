#!/usr/bin/env python3
"""
SMAD-RPC - Cliente RPC sincrono (VM2 e VM3). Parte I do trabalho.

Cada chamada remota bloqueia: a linha seguinte so executa depois da resposta.

Uso:
    python3 cliente_sincrono.py
    python3 cliente_sincrono.py --nome CLIENTE-1 --dias 10
    python3 cliente_sincrono.py --servidor 192.168.50.1 --porta 5002
"""

import time
from xmlrpc.client import Fault

import comum
from comum import log, resumo, separador


def chamada_sincrona(proxy, metodo, args, rotulo):
    log("Enviando requisição RPC")
    log(f"Operação solicitada: {rotulo}")
    inicio = time.time()

    try:
        resultado = getattr(proxy, metodo)(*args)
    except Fault as e:
        log(f"Falha remota: {e.faultString}")
        return None

    decorrido = time.time() - inicio
    log("Resposta recebida")
    log(f"Tempo total: {decorrido:.2f} segundos")
    log(f"Resultado: {resumo(resultado)}")
    separador()
    return resultado


def main():
    args = comum.argumentos(
        "Cliente RPC SÍNCRONO do SMAD", comum.PORTA_SINCRONA
    )
    proxy, status, url = comum.conectar(args)

    separador(f"CLIENTE {args.nome}  —  RPC SÍNCRONA  —  {url}")
    print(f"  Servidor: {status['servidor']}  [{status.get('modo', '?')}]")
    print("  Este cliente vai BLOQUEAR em cada chamada remota.\n", flush=True)

    comum.iniciar_cronometro()
    inicio_geral = time.time()

    chamada_sincrona(
        proxy, "calcular_indice_mofo", [26.5, 82.0],
        "calcular_indice_mofo(26.5, 82.0)",
    )

    log(f">>> A próxima chamada leva ~{args.dias}s. "
        f"Repare que NADA acontece aqui no cliente enquanto isso.")
    chamada_sincrona(
        proxy, "gerar_relatorio", [args.dias],
        f"gerar_relatorio({args.dias})",
    )

    leituras = comum.leituras_simuladas(args.leituras)
    chamada_sincrona(
        proxy, "analisar_colecao", [leituras],
        f"analisar_colecao({args.leituras} leituras)",
    )

    total = time.time() - inicio_geral
    separador("ENCERRAMENTO")
    print(f"  Tempo total do cliente {args.nome}: {total:.2f}s")
    print("  Atividades locais executadas durante as esperas: NENHUMA")
    print("  O tempo do cliente é a SOMA dos tempos das operações remotas.")
    print("=" * 86, flush=True)


if __name__ == "__main__":
    main()
