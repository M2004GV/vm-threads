# SMAD-RPC — Trabalho 02 de Sistemas Distribuídos

RPC **síncrona** e **assíncrona**, ambas com servidor **multithread**, sobre a
mesma infraestrutura virtualizada da Unidade I (3 VMs em dois segmentos de rede).

---

## 1. Arquitetura

```
        Internet
            |
     [Rede A - NAT do hypervisor]
            |
   +--------+--------+
   |   VM1-Gateway   |  enp0s3: NAT            (Rede A - externa)
   |  Roteador NAT   |  enp0s8: 192.168.50.1   (Rede B - interna)
   |  Servidor DHCP  |
   |  Servidores RPC |  servidor_sincrono.py    :5002
   |                 |  servidor_assincrono.py  :5003
   +--------+--------+
            |
   [Rede B - 192.168.50.0/24 - isolada]
            |
     +------+------+
     |             |
+----+-----+  +----+-----+
| VM2      |  | VM3      |   IP via DHCP na Rede B
| Cliente 1|  | Cliente 2|   cliente_sincrono.py / cliente_assincrono.py
+----------+  +----------+
```

VM2 e VM3 têm **uma única interface**, na Rede B, e só alcançam a internet
através do NAT da VM1. A infraestrutura (netplan, `ip_forward`, iptables e
`isc-dhcp-server`) é a mesma entregue na Unidade I, em `infra/setup_vm1.sh`.

---

## 2. As três operações remotas

Estão em `servidor/operacoes.py` e são **importadas pelos dois servidores**.
Isso é proposital: o trabalho executado é idêntico nos dois modelos, só muda
quem espera por quem.

| Operação | Tipo | Parâmetro | Custo |
|---|---|---|---|
| `calcular_indice_mofo(temp, umid)` | cálculo simples | dois números | ~0s |
| `gerar_relatorio(dias)` | processamento demorado | `dias` | **1s por dia** → `gerar_relatorio(10)` = 10s |
| `analisar_colecao(leituras)` | processamento de coleção | lista de valores | **0,5s por leitura** → 10 leituras = 5s |

`analisar_colecao` devolve média, maior, menor, amplitude e desvio padrão.
Os tempos foram escolhidos para reproduzir exatamente o cenário cobrado na
avaliação: **uma operação de 10s e outra de 5s chegando ao mesmo tempo**.

---

## 3. Os dois modelos de chamada

### Parte I — RPC síncrona (`:5002`)

XML-RPC sobre HTTP com `ThreadingMixIn`: **uma thread por requisição**.
O cliente invoca o método e fica bloqueado até a resposta chegar.

```
cliente ──── chamada ────► servidor  [thread Worker-SYNC-4 processa 10s]
   (bloqueado, sem fazer nada)
cliente ◄─── resposta ────┘
```

### Parte II — RPC assíncrona (`:5003`)

Padrão *deferred synchronous RPC* (ticket), em três métodos remotos:

| Método | O que faz |
|---|---|
| `submeter(operacao, argumentos)` | aceita a chamada, joga no `ThreadPoolExecutor` e **devolve na hora** um `job_id` |
| `consultar(job_id)` | devolve o estado (`PENDENTE` / `EXECUTANDO` / `CONCLUIDO` / `ERRO`) e o resultado, se houver |
| `listar_jobs()` | visão geral da fila |

Do lado do cliente, a classe `FuturoRPC` (em `cliente/comum.py`) embrulha o
ticket e expõe `.get()`, reproduzindo o pseudocódigo do enunciado:

```python
futuro = FuturoRPC(proxy, proxy.submeter("gerar_relatorio", [10]))
executar_atividades_locais()          # o cliente continua trabalhando
resultado = futuro.get()              # só aqui ele espera
```

---

## 4. Arquivos

| Arquivo | Onde roda | Função |
|---|---|---|
| `servidor/operacoes.py` | VM1 | as três operações remotas (compartilhadas) |
| `servidor/servidor_sincrono.py` | VM1 | servidor síncrono multithread, porta 5002 |
| `servidor/servidor_assincrono.py` | VM1 | servidor assíncrono com pool, porta 5003 |
| `cliente/comum.py` | VM2 e VM3 | log, parsing de argumentos e `FuturoRPC` |
| `cliente/cliente_sincrono.py` | VM2 e VM3 | cliente da Parte I |
| `cliente/cliente_assincrono.py` | VM2 e VM3 | cliente da Parte II |

Só a biblioteca padrão do Python 3 (`xmlrpc`, `threading`,
`concurrent.futures`). **Nenhuma dependência para instalar.**

---

## 5. Instalação

Em cada VM, com o Linux já instalado:

```bash
sudo apt update && sudo apt install -y python3 git
git clone https://github.com/M2004GV/<repositorio>.git
cd <repositorio>/projeto-rpc-smad
```

Na VM1, liberar as portas caso o firewall esteja ativo:

```bash
sudo ufw status                       # se estiver "inactive", não precisa fazer nada
sudo ufw allow 5002/tcp
sudo ufw allow 5003/tcp
```

Conferir a rede antes de executar:

```bash
# nos clientes (VM2 / VM3)
ip -br a                     # IP recebido do DHCP na Rede B (192.168.50.0/24)
ip route | grep default      # default via 192.168.50.1
ping -c 2 192.168.50.1       # gateway responde
ping -c 2 8.8.8.8            # prova o NAT da VM1
```

Se a VM1 usar outro IP na Rede B, basta passar `--servidor <ip>` nos clientes.

---

## 6. Execução

### Parte I — síncrona

**VM1** (um terminal):
```bash
cd servidor && python3 servidor_sincrono.py
```

**VM2 e VM3** — disparar ao mesmo tempo, é isso que mostra a concorrência:
```bash
cd cliente && python3 cliente_sincrono.py --nome CLIENTE-1    # na VM2
cd cliente && python3 cliente_sincrono.py --nome CLIENTE-2    # na VM3
```

### Parte II — assíncrona

**VM1** (outro terminal):
```bash
cd servidor && python3 servidor_assincrono.py
```

**VM2 e VM3**, novamente juntos:
```bash
cd cliente && python3 cliente_assincrono.py --nome CLIENTE-1  # na VM2
cd cliente && python3 cliente_assincrono.py --nome CLIENTE-2  # na VM3
```

### Modos de demonstração

Existem para responder, ao vivo, duas perguntas da avaliação:

```bash
python3 servidor_sincrono.py --sequencial     # servidor com UMA thread
python3 servidor_assincrono.py --workers 1    # pool com UMA thread
```

Com uma thread só, as requisições **entram em fila**: o segundo cliente só
começa a ser atendido quando o primeiro termina.

### Parâmetros dos clientes

```
--servidor IP    IP da VM1 na Rede B      (padrão 192.168.50.1)
--porta N        5002 síncrono, 5003 assíncrono
--nome TEXTO     identificação nos logs   (padrão: hostname)
--dias N         operação demorada, 1s por dia       (padrão 10 → 10s)
--leituras N     tamanho da coleção, 0,5s por item   (padrão 10 → 5s)
```

---

## 7. O que observar

### No cliente síncrono — o buraco na linha do tempo

```
12:22:05 - Enviando requisição RPC
12:22:05 - Operação solicitada: gerar_relatorio(10)
12:22:15 - Resposta recebida
12:22:15 - Tempo total: 10.01 segundos
```

Dez segundos sem uma única linha: o cliente não fez absolutamente nada.

### No cliente assíncrono — o intervalo preenchido

```
12:19:16 - Requisição assíncrona enviada: gerar_relatorio(10)
12:19:16 - Ticket recebido na hora: bff01396
12:19:16 - Cliente continuou sua execução
12:19:16 - Executando atividade local 1: Calibrando sensor de temperatura
12:19:18 - Executando atividade local 2: Verificando bateria da estação
12:19:20 - Executando atividade local 3: Gravando buffer local em disco
12:19:22 - Executando atividade local 4: Checando rota até o gateway
12:19:26 - Resultado RPC disponível
```

### No servidor — a prova do multithreading

```
[12:22:05.827] [Worker-SYNC-4] gerar_relatorio(10 dias) - inicio, vai levar 10s
[12:22:05.829] [Worker-SYNC-6] gerar_relatorio(10 dias) - inicio, vai levar 10s   <- ao mesmo tempo
[12:22:15.830] [Worker-SYNC-4] gerar_relatorio(10) - CONCLUIDO em 10.0s
[12:22:15.832] [Worker-SYNC-6] gerar_relatorio(10) - CONCLUIDO em 10.0s           <- ambos em 10s
```

Com servidor de uma thread só, o segundo terminaria aos 20s.

---

## 8. Resultados medidos

Dois clientes simultâneos, `--dias 10 --leituras 10` (10s + 5s + ~0s de
processamento remoto por cliente):

| | Tempo total do cliente | Trabalho local feito durante a espera |
|---|---|---|
| **Síncrono** | 15,01 s | nenhum |
| **Assíncrono** | 10,28 s | 8 s |

Os dois clientes mediram o mesmo tempo nas duas rodadas, o que confirma que
nenhum deles ficou esperando o outro: o servidor atendeu VM2 e VM3 em paralelo
nos dois modelos.

Observe que o servidor gastou **exatamente os mesmos 15s de processamento**
nos dois casos. O que mudou foi o aproveitamento do tempo do cliente.

A comparação completa e as respostas às perguntas da avaliação estão em
[`RESPOSTAS.md`](RESPOSTAS.md).
