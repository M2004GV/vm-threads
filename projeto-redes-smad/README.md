# SMAD - Sistema de Monitoramento Ambiental Distribuido

Projeto de redes: infraestrutura virtualizada (roteamento NAT + DHCP) e
aplicacoes cliente-servidor com sockets TCP e UDP multithread.

## Arquitetura

```
        Internet
            |
     [Rede A - NAT]
            |
   +--------+--------+
   |   VM1-Gateway   |  enp0s3: NAT (Rede A)
   |  Roteador NAT   |  enp0s8: 192.168.10.1/24 (Rede B)
   |  Servidor DHCP  |  server_tcp.py :5000
   |  Servidores     |  server_udp.py :5001
   +--------+--------+
            |
   [Rede B - 192.168.10.0/24]
            |
     +------+------+
     |             |
+----+-----+  +----+-----+
| VM2      |  | VM3      |   IP via DHCP (.100 - .200)
| Clientes |  | Clientes |   client_tcp.py / client_udp.py
+----------+  +----------+
```

## Arquivos

| Arquivo | Onde roda | Funcao |
|---|---|---|
| `setup_vm1.sh` | VM1 | netplan + ip_forward + iptables/NAT + isc-dhcp-server |
| `server_tcp.py` | VM1 | Servidor TCP multithread, porta 5000 |
| `server_udp.py` | VM1 | Servidor UDP multithread, porta 5001 |
| `client_tcp.py` | VM2 e VM3 | Estacao de sensores, envia leituras |
| `client_udp.py` | VM2 e VM3 | Consultas rapidas de status/alerta |

## Regra de negocio

Cada cliente simula uma estacao de sensores de temperatura e umidade.

**TCP (porta 5000)** - sessao com estado:
1. o cliente abre UMA conexao e envia varias leituras por ela;
2. o servidor valida a leitura (faixas de temperatura e umidade);
3. calcula o **Indice de Risco de Mofo** — `time.sleep(3)` simula o custo
   desse processamento e evidencia o multithreading;
4. acumula o historico por IP de origem e devolve media, minima, maxima
   e o nivel de alerta (NORMAL / ALERTA / CRITICO).

**UDP (porta 5001)** - consultas sem conexao, `time.sleep(2)`:
- `CONSULTA_STATUS` — uptime, total de requisicoes, clientes distintos;
- `CONSULTA_ALERTA` — avalia uma leitura sem grava-la;
- `PING` — mede latencia.

Cada conexao TCP e cada datagrama UDP e despachado para uma **thread
propria**, entao VM2 e VM3 sao atendidas simultaneamente.

## Como executar

### Na VM1 (dois terminais)

```bash
python3 server_tcp.py     # terminal 1
python3 server_udp.py     # terminal 2
```

### Na VM2 e na VM3 (ao mesmo tempo, para mostrar concorrencia)

```bash
python3 client_tcp.py 5              # 5 leituras
python3 client_udp.py 5              # 5 consultas sequenciais
python3 client_udp.py 6 --paralelo   # 6 consultas simultaneas
```

## O que observar (evidencia do multithreading)

No terminal do servidor, compare os horarios:

```
[16:46:42.097] [Worker-TCP-1] Processando leitura... aguardando 3s
[16:46:42.097] [Worker-TCP-2] Processando leitura... aguardando 3s     <- ao mesmo tempo
[16:46:45.098] [Worker-TCP-1] Resposta enviada -> NORMAL
[16:46:45.098] [Worker-TCP-2] Resposta enviada -> NORMAL               <- ambas em 3s
```

Se o servidor fosse **single-thread**, o segundo cliente so receberia
resposta aos 6 segundos. O fato de os dois terminarem em 3s prova o
processamento paralelo.

## Testes de rede (para o video)

Nos clientes:
```bash
ip -br a                    # IP recebido do DHCP (192.168.10.100-200)
ip route | grep default     # default via 192.168.10.1
ping -c 3 192.168.10.1      # gateway
ping -c 3 8.8.8.8           # prova o NAT
ping -c 3 google.com        # prova o DNS entregue pelo DHCP
```

Na VM1:
```bash
sudo iptables -t nat -L POSTROUTING -n -v     # regra MASQUERADE e contadores
cat /var/lib/dhcp/dhcpd.leases                # concessoes entregues
sudo ss -tulnp | grep -E '5000|5001'          # servidores escutando
```
