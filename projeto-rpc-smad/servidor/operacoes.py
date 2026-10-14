#!/usr/bin/env python3
"""Operacoes remotas do SMAD, compartilhadas pelos servidores sincrono e assincrono."""

import sys
import threading
import time
from datetime import datetime

_lock_log = threading.Lock()

# Custos artificiais: gerar_relatorio(10) = 10s, analisar_colecao(10) = 5s.
SEGUNDOS_POR_DIA = 1.0
SEGUNDOS_POR_LEITURA = 0.5


def log(msg):
    agora = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    linha = f"[{agora}] [{threading.current_thread().name}] {msg}\n"
    with _lock_log:
        sys.stdout.write(linha)
        sys.stdout.flush()


def calcular_indice_mofo(temperatura, umidade):
    """Calculo simples, retorno praticamente instantaneo."""
    temperatura = float(temperatura)
    umidade = float(umidade)
    log(f"calcular_indice_mofo(T={temperatura}, U={umidade}) - inicio")

    if not (-50 <= temperatura <= 80):
        raise ValueError(f"temperatura fora de faixa: {temperatura}")
    if not (0 <= umidade <= 100):
        raise ValueError(f"umidade fora de faixa: {umidade}")

    if umidade < 60:
        indice = 0.0
    else:
        fator_umidade = (umidade - 60) / 40.0
        fator_temp = 1.0 if 20 <= temperatura <= 30 else 0.5
        indice = round(fator_umidade * fator_temp, 2)

    if indice >= 0.7:
        nivel = "CRITICO"
    elif indice >= 0.4:
        nivel = "ALERTA"
    else:
        nivel = "NORMAL"

    log(f"calcular_indice_mofo -> indice={indice} nivel={nivel}")
    return {
        "operacao": "calcular_indice_mofo",
        "temperatura": temperatura,
        "umidade": umidade,
        "indice_risco_mofo": indice,
        "nivel_alerta": nivel,
        "thread_servidor": threading.current_thread().name,
        "concluido_em": datetime.now().strftime("%H:%M:%S"),
    }


def gerar_relatorio(dias):
    """Operacao demorada: 1s por dia de historico. O sleep ocupa a thread, nao a CPU."""
    dias = int(dias)
    if not (1 <= dias <= 120):
        raise ValueError(f"periodo invalido: {dias} (esperado entre 1 e 120)")

    duracao = dias * SEGUNDOS_POR_DIA
    inicio = time.time()
    log(f"gerar_relatorio({dias} dias) - inicio, vai levar {duracao:.0f}s")

    # Em blocos para que o log mostre progresso durante a espera.
    passos = max(1, int(duracao))
    for passo in range(1, passos + 1):
        time.sleep(duracao / passos)
        log(f"gerar_relatorio({dias}) - consolidando dia {passo}/{passos}")

    decorrido = round(time.time() - inicio, 2)
    log(f"gerar_relatorio({dias}) - CONCLUIDO em {decorrido}s")
    return {
        "operacao": "gerar_relatorio",
        "periodo_dias": dias,
        "registros_consolidados": dias * 24,
        "duracao_segundos": decorrido,
        "thread_servidor": threading.current_thread().name,
        "concluido_em": datetime.now().strftime("%H:%M:%S"),
    }


def analisar_colecao(leituras):
    """Estatisticas de uma colecao, com custo de 0.5s por leitura."""
    if not leituras:
        raise ValueError("colecao vazia")

    valores = [float(v) for v in leituras]
    duracao = len(valores) * SEGUNDOS_POR_LEITURA
    inicio = time.time()
    log(f"analisar_colecao({len(valores)} leituras) - inicio, ~{duracao:.1f}s")

    for i, _ in enumerate(valores, start=1):
        time.sleep(SEGUNDOS_POR_LEITURA)
        if i % 5 == 0 or i == len(valores):
            log(f"analisar_colecao - {i}/{len(valores)} leituras processadas")

    media = sum(valores) / len(valores)
    variancia = sum((v - media) ** 2 for v in valores) / len(valores)
    decorrido = round(time.time() - inicio, 2)

    log(f"analisar_colecao - CONCLUIDO em {decorrido}s (media={media:.2f})")
    return {
        "operacao": "analisar_colecao",
        "total_leituras": len(valores),
        "media": round(media, 2),
        "maior": max(valores),
        "menor": min(valores),
        "amplitude": round(max(valores) - min(valores), 2),
        "desvio_padrao": round(variancia ** 0.5, 2),
        "duracao_segundos": decorrido,
        "thread_servidor": threading.current_thread().name,
        "concluido_em": datetime.now().strftime("%H:%M:%S"),
    }


OPERACOES = {
    "calcular_indice_mofo": calcular_indice_mofo,
    "gerar_relatorio": gerar_relatorio,
    "analisar_colecao": analisar_colecao,
}
