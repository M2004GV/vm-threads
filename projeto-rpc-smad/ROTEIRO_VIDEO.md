# Roteiro da gravação — Trabalho 02

**Duração alvo: 18 a 22 minutos.** O enunciado exige ver **os dois discentes**
explicando, com um responsável por cada protocolo. A divisão sugerida:

- **Aluno A** → infraestrutura de rede + **RPC síncrona**
- **Aluno B** → **RPC assíncrona** + demonstração do servidor de uma thread
- **Os dois** → as perguntas da avaliação, alternando

---

## Antes de gravar — checklist

Deixe tudo pronto e testado **antes** de apertar o REC. Gravar e configurar ao
mesmo tempo é o jeito mais rápido de perder meia hora.

- [ ] As três VMs ligadas, VM2 e VM3 com IP do DHCP (`ip -br a`)
- [ ] `ping 192.168.10.1` e `ping 8.8.8.8` funcionando nos dois clientes
- [ ] Repositório clonado nas três VMs, na mesma pasta
- [ ] Teste completo rodado uma vez, do começo ao fim, sem gravar
- [ ] Portas 5002 e 5003 liberadas na VM1 (`sudo ufw status`)
- [ ] Janelas organizadas: VM1 ocupando metade da tela, VM2 e VM3 empilhadas
      na outra metade — o servidor e os dois clientes precisam aparecer juntos
- [ ] Fonte do terminal aumentada (Ctrl + Shift + `+`); o professor vai assistir
      num vídeo comprimido
- [ ] Microfone testado e rosto/voz dos dois identificáveis
- [ ] Relógio das VMs sincronizado (`timedatectl`) — os timestamps são a prova

**Truque para disparar os clientes juntos:** digite o comando nas duas VMs sem
apertar Enter, conte "3, 2, 1" em voz alta e aperte nas duas. Os timestamps
ficam alinhados e a evidência fica limpa.

---

## Bloco 0 — Abertura (ambos) · ~1 min

Os dois na câmera. Nome completo, disciplina, e quem vai falar de quê.

> "Trabalho 2 de Sistemas Distribuídos. Mantivemos o mesmo cenário da Unidade I:
> três VMs no VirtualBox, uma gateway com duas interfaces e duas clientes numa
> rede interna isolada. Sobre essa infraestrutura implementamos RPC síncrona e
> assíncrona, as duas com servidor multithread."

---

## Bloco 1 — Infraestrutura (Aluno A) · ~5 min

### 1.1 VirtualBox, com as janelas de configuração abertas

Mostre em **Configurações → Rede** de cada VM:

- **VM1**: Adaptador 1 em **NAT** (Rede A) e Adaptador 2 em **Rede Interna**,
  nome `redeB` (Rede B)
- **VM2** e **VM3**: adaptador único em **Rede Interna** `redeB`

> "A VM1 é o único ponto de contato com o mundo externo. VM2 e VM3 têm uma
> interface só, na rede interna — elas fisicamente não alcançam a internet a
> não ser passando pela VM1. É isso que caracteriza a zona protegida."

### 1.2 Na VM1 — mostre a configuração funcionando

```bash
ip -br a                                   # enp0s3 (NAT) e enp0s8 (192.168.10.1)
cat /etc/netplan/*.yaml                    # IP estático da interface interna
sysctl net.ipv4.ip_forward                 # deve retornar 1
sudo iptables -t nat -L POSTROUTING -n -v  # a regra MASQUERADE e os contadores
systemctl status isc-dhcp-server --no-pager | head -5
cat /var/lib/dhcp/dhcpd.leases | tail -20  # as concessões entregues a VM2 e VM3
```

Explique cada peça ao passar por ela: `ip_forward` liga o roteamento,
MASQUERADE reescreve o endereço de origem na saída, o DHCP entrega IP, gateway
e DNS para a Rede B.

### 1.3 Nos clientes — os testes de conexão

```bash
ip -br a                     # IP na faixa 192.168.10.100-200
ip route | grep default      # default via 192.168.10.1
ping -c 3 192.168.10.1       # alcança o gateway
ping -c 3 192.168.10.<ip-da-outra-vm>   # VM2 e VM3 se enxergam na Rede B
ping -c 3 8.8.8.8            # prova o NAT
ping -c 3 google.com         # prova o DNS vindo do DHCP
```

> "Os contadores do MASQUERADE subiram durante o ping — é o tráfego de VM2
> saindo com o endereço da VM1."

---

## Bloco 2 — Código síncrono (Aluno A) · ~4 min

### 2.1 `servidor/operacoes.py`

Abra primeiro, porque é a base das duas partes.

> "As três operações ficam num módulo único, importado pelos dois servidores.
> Isso é intencional: garante que o trabalho executado é idêntico nos dois
> modelos. Quando a gente disser que a RPC assíncrona não deixa o servidor
> mais rápido, é esse arquivo que prova."

Percorra: `calcular_indice_mofo` é instantâneo; `gerar_relatorio` custa 1s por
dia, então `gerar_relatorio(10)` leva 10s; `analisar_colecao` custa 0,5s por
leitura, então 10 leituras dão 5s. Diga por que esses números: reproduzem o
cenário de 10s e 5s que a avaliação pergunta.

### 2.2 `servidor/servidor_sincrono.py`

Aponte para a linha que carrega o trabalho inteiro:

```python
class ServidorMultithread(ThreadingMixIn, SimpleXMLRPCServer):
```

> "`ThreadingMixIn` faz o servidor criar uma thread por requisição. Sem ele,
> seria uma fila. Renomeamos a thread para `Worker-SYNC-N` para que o log
> mostre quem está processando o quê."

Mostre também o `lock` protegendo o dicionário de estatísticas e explique por
que ele é necessário quando várias threads escrevem na mesma estrutura.

### 2.3 `cliente/cliente_sincrono.py`

```python
resultado = getattr(proxy, metodo)(*args)   # aqui o cliente para
```

> "Essa linha é a chamada remota. O programa não passa dela enquanto a
> resposta não chegar. É o comportamento da Parte I."

---

## Bloco 3 — Execução síncrona ao vivo (Aluno A) · ~3 min

**VM1:**
```bash
cd servidor && python3 servidor_sincrono.py
```

**VM2 e VM3, ao mesmo tempo:**
```bash
cd cliente && python3 cliente_sincrono.py --nome CLIENTE-1
cd cliente && python3 cliente_sincrono.py --nome CLIENTE-2
```

Enquanto roda, narre **apontando para a tela**:

1. A operação rápida responde em 0,00s.
2. Começa `gerar_relatorio(10)` — **fique em silêncio alguns segundos de
   propósito** e depois diga: *"repare que o cliente não imprimiu nada, ele
   está bloqueado"*.
3. No servidor, mostre `Worker-SYNC-4` e `Worker-SYNC-6` iniciando no mesmo
   milissegundo e terminando no mesmo milissegundo.
4. No fim: *"os dois clientes mediram 15 segundos. Nenhum esperou pelo outro —
   o servidor é multithread. Mas cada um dos dois ficou 15 segundos sem fazer
   nada."*

---

## Bloco 4 — Código assíncrono (Aluno B) · ~4 min

### 4.1 O desenho da solução

Explique **antes** de abrir o código:

> "RPC assíncrona precisa separar dois momentos que na síncrona são um só:
> pedir e receber. Implementamos o padrão de ticket. O cliente chama
> `submeter`, o servidor registra o job, joga num pool de threads e devolve na
> hora um identificador. Depois o cliente chama `consultar` com esse
> identificador para pegar o resultado."

### 4.2 `servidor/servidor_assincrono.py`

Mostre `submeter()` e destaque:

```python
executor.submit(_executar, job_id, nome, argumentos)
return job_id          # devolve o ticket sem esperar o processamento
```

> "Essas duas linhas são o coração da Parte II. `executor.submit` agenda; o
> `return` sai imediatamente. A operação em si roda depois, numa thread do
> pool, e o resultado fica guardado na tabela de jobs."

Mostre a tabela `jobs`, o `lock` que a protege e os quatro estados
(`PENDENTE`, `EXECUTANDO`, `CONCLUIDO`, `ERRO`).

### 4.3 `cliente/comum.py` — a classe `FuturoRPC`

> "Do lado do cliente embrulhamos o ticket num *future*. O `.get()` é o único
> ponto onde o cliente bloqueia — e só depois de já ter feito o trabalho dele.
> O intervalo entre consultas começa em 50ms e vai dobrando, para não martelar
> o servidor."

### 4.4 `cliente/cliente_assincrono.py`

Mostre que o código espelha o pseudocódigo do enunciado: submete, continua,
executa atividades locais, depois `get()`.

---

## Bloco 5 — Execução assíncrona ao vivo (Aluno B) · ~3 min

**VM1, em outro terminal** (deixe o síncrono rodando, mostra os dois serviços
no ar):
```bash
cd servidor && python3 servidor_assincrono.py
```

**VM2 e VM3, ao mesmo tempo:**
```bash
cd cliente && python3 cliente_assincrono.py --nome CLIENTE-1
cd cliente && python3 cliente_assincrono.py --nome CLIENTE-2
```

Narre:

1. As duas submissões voltam instantaneamente, com os tickets.
2. *"Agora compare com o bloco anterior: ali havia dez segundos de silêncio.
   Aqui o cliente está imprimindo atividade local a cada dois segundos."*
3. Aponte a linha `Estado dos jobs no servidor: ... EXECUTANDO | ... CONCLUIDO`
   — *"a coleção já terminou e o relatório ainda está rodando; o cliente
   consegue saber disso sem bloquear."*
4. No servidor, mostre **quatro workers** processando de uma vez: dois
   relatórios e duas coleções, de dois clientes diferentes.
5. Feche com os números: *"10,28 segundos contra 15,01, e ainda com 8 segundos
   de trabalho local feito."*

---

## Bloco 6 — O servidor de uma thread (Aluno B) · ~2 min

Derruba o servidor síncrono (Ctrl+C) e sobe em modo degradado:

```bash
python3 servidor_sincrono.py --sequencial
```

Dispare os dois clientes juntos de novo.

> "Agora todo o processamento aparece sob `MainThread` e as requisições
> entraram em fila. Um cliente terminou em 7 segundos e o outro em 14. É
> exatamente a pergunta da avaliação: com uma thread só, a operação curta fica
> refém da longa."

Se sobrar tempo, mostre também `python3 servidor_assincrono.py --workers 1`,
onde o cliente continua livre mas os jobs se enfileiram — útil para separar
assincronia de concorrência na pergunta 7.

---

## Bloco 7 — Perguntas da avaliação (ambos, alternando) · ~5 min

As respostas completas estão em `RESPOSTAS.md`. **Não leia o arquivo na
câmera** — use estes ganchos e fale com naturalidade. Alternem: A responde a
1, B a 2, e assim por diante.

| # | Gancho para a resposta |
|---|---|
| 1 | A diferença está no fluxo do cliente, não no servidor: 15,01s sem trabalho local contra 10,28s com 8s aproveitados. |
| 2 | Ficou bloqueado, thread parada no socket. Mas o servidor não estava ocioso — atendia o outro cliente. |
| 3 | 8s de atividades locais, submeteu a segunda operação antes da primeira terminar e consultou o estado dos dois jobs. |
| 4 | Um cliente lento não atrapalha o outro. Os dois `Worker-SYNC` começaram e terminaram no mesmo milissegundo. |
| 5 | Fila. A de 5s terminaria aos 15s se chegasse atrás da de 10s. Mostramos ao vivo: 7,03s e 14,04s. |
| 6 | Não. Mesmo módulo `operacoes.py` nos dois servidores, mesmos 10,0s. A assincronia até adiciona overhead de rede. |
| 7 | Lados opostos da chamada e independentes: nossa Parte I tem cliente síncrono **com** servidor concorrente. |
| 8 | Espera simultânea, computação concorrente. Depende das vCPUs da VM1, e o GIL do CPython só não atrapalha porque `sleep` o libera. |

A pergunta 8 é a que mais distingue uma dupla que entendeu de uma que
decorou. Vale gastar um minuto nela e mencionar `nproc` na VM1.

---

## Bloco 8 — Encerramento (ambos) · ~1 min

Resuma em uma frase cada: o que foi construído, o que ficou comprovado, onde
está o código. Mencione que o `README.md` traz as instruções de instalação e
execução e o `RESPOSTAS.md` a comparação completa.

---

## Publicação

1. Suba o código no GitHub — pode ser no mesmo repositório da Unidade I, numa
   pasta nova, mantendo o histórico do trabalho anterior.
2. Vídeo no Google Drive **com link público de leitura** e o link no
   `README.md` principal, como foi feito na Unidade I. Confira o
   compartilhamento numa janela anônima antes de entregar.
3. No SIGAA, **apenas um dos dois** responde, só com o link do GitHub.
4. Lembre-se de que haverá horário marcado para teste presencial com o
   professor — deixem as VMs no estado em que foram gravadas.
