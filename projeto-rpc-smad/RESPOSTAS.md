# Comparação dos resultados — respostas da avaliação

Todos os números abaixo vieram das execuções registradas em `README.md`,
seção 8: dois clientes simultâneos (VM2 e VM3), `gerar_relatorio(10)` = 10s
e `analisar_colecao(10 leituras)` = 5s.

---

### 1. Qual foi a principal diferença observada entre RPC síncrona e RPC assíncrona?

A diferença está no **fluxo de execução do cliente**, não no servidor.

Na chamada síncrona, a invocação remota e a espera pelo resultado são o mesmo
ato: a linha seguinte do programa só executa quando a resposta chega. Na
assíncrona, esses dois momentos foram separados — `submeter()` devolve um
ticket imediatamente e `futuro.get()` busca o resultado depois. Entre um e
outro, o cliente é dono do seu próprio tempo.

Em números: o cliente síncrono levou **15,01s** e não fez nada além de
esperar. O assíncrono levou **10,28s** e ainda executou **8s de atividades
locais** nesse intervalo. O servidor processou os mesmos 15s de trabalho nos
dois casos.

Vale registrar uma diferença de custo que também apareceu: a chamada
assíncrona exige pelo menos duas idas à rede (submeter e consultar) em vez de
uma. Para a operação de cálculo simples, que termina em milissegundos, esse
overhead é maior que o próprio processamento. Assincronia compensa quando a
operação é longa.

---

### 2. O que aconteceu com o Cliente 1 enquanto aguardava uma chamada síncrona de 10 segundos?

Nada. Ele ficou **bloqueado**, com a thread principal parada dentro da chamada
remota, esperando a resposta chegar pelo socket.

O log mostra isso como um silêncio de dez segundos:

```
12:22:05 - Enviando requisição RPC
12:22:05 - Operação solicitada: gerar_relatorio(10)
12:22:15 - Resposta recebida
12:22:15 - Tempo total: 10.01 segundos
```

Importante não confundir: o cliente estava bloqueado, mas **o servidor não
estava ocioso** — ele processava o pedido do Cliente 2 em outra thread ao
mesmo tempo. O bloqueio é do chamador, não do sistema.

---

### 3. O que o cliente conseguiu realizar durante uma chamada assíncrona?

Executou quatro atividades locais do SMAD, de 2 segundos cada, totalizando 8
segundos de trabalho útil que no modelo síncrono simplesmente não existiriam:

```
12:19:16 - Ticket recebido na hora: bff01396
12:19:16 - Cliente continuou sua execução
12:19:16 - Executando atividade local 1: Calibrando sensor de temperatura
12:19:18 - Executando atividade local 2: Verificando bateria da estação
12:19:20 - Executando atividade local 3: Gravando buffer local em disco
12:19:22 - Executando atividade local 4: Checando rota até o gateway
12:19:24 - Estado dos jobs no servidor: bff01396=EXECUTANDO | c7f4a814=CONCLUIDO
12:19:26 - Resultado RPC disponível
```

Além do trabalho local, ele conseguiu **submeter a segunda operação remota
antes de a primeira terminar** e consultar o estado dos dois jobs no meio do
caminho. As duas operações ficaram rodando em paralelo no servidor justamente
porque o cliente não parou na primeira.

---

### 4. Qual é a vantagem de utilizar um servidor multithread neste cenário?

Um cliente lento deixa de atrapalhar os outros. Como cada requisição ganha a
sua própria thread, VM2 e VM3 são atendidas ao mesmo tempo:

```
[12:22:05.827] [Worker-SYNC-4] gerar_relatorio(10 dias) - inicio, vai levar 10s
[12:22:05.829] [Worker-SYNC-6] gerar_relatorio(10 dias) - inicio, vai levar 10s
[12:22:15.830] [Worker-SYNC-4] gerar_relatorio(10) - CONCLUIDO em 10.0s
[12:22:15.832] [Worker-SYNC-6] gerar_relatorio(10) - CONCLUIDO em 10.0s
```

Os dois começaram no mesmo milissegundo e terminaram no mesmo milissegundo.
Os dois clientes mediram 15,01s — ou seja, nenhum pagou pela presença do
outro.

A vantagem fica mais clara quando se observa a natureza do custo: as nossas
operações passam o tempo **esperando** (`time.sleep` simulando I/O e
consolidação de dados), não consumindo CPU. Enquanto uma thread espera, as
outras avançam. O ganho vem de ocupar o tempo ocioso, não de ter mais poder
de processamento.

---

### 5. O que aconteceria se o servidor possuísse apenas uma thread e recebesse simultaneamente uma operação de 10 segundos e outra de 5 segundos?

As requisições **entrariam em fila**. O servidor atenderia a primeira até o
fim e só então começaria a segunda — e o tempo de espera de cada cliente
passaria a depender da ordem de chegada e do tamanho do pedido alheio.

Para a pergunta exata: se a de 10s chegasse primeiro, a de 5s terminaria aos
**15s** em vez de aos 5s. Na ordem inversa, a de 10s terminaria aos 15s e a de
5s aos 5s. O total do sistema seria sempre 15s, contra 10s no modelo
multithread.

Isso não é hipótese: reproduzimos ao vivo com `--sequencial`. Com dois
clientes disparados juntos, o primeiro da fila terminou em **7,03s** e o
segundo em **14,04s**, e todo o processamento apareceu no log sob
`[MainThread]`. Em modo multithread, o mesmo cenário dá ~7s para os dois.

Há ainda um efeito colateral que o log evidencia: a operação curta fica
*refém* da longa. Um cálculo que levaria milissegundos pode esperar dez
segundos só porque chegou atrás de um relatório.

---

### 6. RPC assíncrona necessariamente torna o processamento realizado pelo servidor mais rápido? Justifique.

**Não.** O servidor executou exatamente o mesmo código, com exatamente o mesmo
custo, nos dois modelos — e isso está garantido no projeto: as três operações
vivem num módulo único (`operacoes.py`) importado tanto pelo servidor síncrono
quanto pelo assíncrono. `gerar_relatorio(10)` levou 10,0s nas duas rodadas.

Assincronia é uma propriedade de **quem chama**, não de quem processa. Ela
muda o momento em que o cliente vai buscar a resposta; não altera uma linha do
que o servidor precisa fazer para produzi-la.

Na prática, ela até **adiciona** trabalho ao servidor: há um identificador de
job para gerar, uma tabela de estado para manter sob lock e uma requisição
extra a cada `consultar()`. Em operações curtas esse overhead domina — foi o
que vimos no `calcular_indice_mofo`, que de síncrono responde em
milissegundos e de assíncrono custa duas viagens de rede.

O que melhora de fato é o **tempo total percebido pelo cliente** (10,28s
contra 15,01s) e o aproveitamento do sistema como um todo, porque as duas
operações remotas passaram a rodar em paralelo entre si em vez de uma após a
outra. Quem torna o servidor capaz de atender mais em menos tempo é o
**multithreading**, não a assincronia.

---

### 7. Qual é a diferença entre assincronicidade no cliente e concorrência no servidor?

São propriedades de lados opostos da chamada e **independentes entre si**.

Assincronia no cliente diz respeito ao *controle de fluxo de quem chama*: o
programa bloqueia ou não bloqueia enquanto a resposta não chega. Concorrência
no servidor diz respeito à *capacidade de quem atende*: quantas requisições
ele consegue processar ao mesmo tempo.

As quatro combinações existem:

| | Servidor 1 thread | Servidor multithread |
|---|---|---|
| **Cliente síncrono** | tudo em fila; o pior caso | nosso Parte I: cliente bloqueia, mas VM2 e VM3 são atendidas juntas |
| **Cliente assíncrono** | cliente livre, mas o gargalo continua no servidor | nosso Parte II: cliente livre e servidor paralelo |

O nosso próprio trabalho prova a independência: na **Parte I** o cliente é
totalmente síncrono e, ainda assim, os dois clientes foram atendidos em
paralelo — a concorrência do servidor não depende de o cliente ser
assíncrono. E com `--workers 1` no servidor assíncrono acontece o inverso: o
cliente continua livre para trabalhar, mas os jobs se enfileiram no pool.

Em uma frase: assincronia melhora o aproveitamento do **tempo do cliente**;
concorrência melhora a **vazão do servidor**. Resolver um não resolve o outro.

---

### 8. As duas chamadas RPC foram realmente executadas simultaneamente ou concorrentemente? Explique considerando o ambiente utilizado.

A resposta honesta é **as duas coisas, dependendo do trecho** — e o ambiente
decide qual.

Primeiro, o hardware: há paralelismo real de CPU apenas se a VM1 tiver **duas
ou mais vCPUs** atribuídas no VirtualBox (`nproc` confirma dentro da VM). Com
uma única vCPU, nada é fisicamente simultâneo: o escalonador reveza as
threads, e temos concorrência por intercalação.

Segundo, e mais decisivo aqui: os servidores rodam em **CPython, que tem GIL**
(*Global Interpreter Lock*). Duas threads Python do mesmo processo nunca
executam bytecode ao mesmo tempo, mesmo em várias vCPUs. Se as nossas
operações fossem CPU-bound, o multithreading não daria ganho nenhum.

O que salva o cenário é a natureza da carga: o custo das operações é
`time.sleep()`, simulando I/O e consolidação de dados, e **`sleep` libera o
GIL**. Durante a espera, as threads estão de fato paradas ao mesmo tempo, sem
disputar o interpretador. Por isso os dois `gerar_relatorio(10)` começaram em
`12:22:05.827` e `12:22:05.829` e terminaram em `12:22:15.830` e
`12:22:15.832`: dez segundos de espera genuinamente sobrepostos.

Então, com precisão: a **espera** das duas chamadas foi simultânea; os
pequenos trechos de computação real (validação, média, desvio padrão,
serialização XML) foram **concorrentes**, intercalados pelo GIL. Para o
resultado observado isso é indiferente, porque esses trechos são
insignificantes perto dos 10s e 5s de espera — mas a distinção importa, e
seria determinante se a carga fosse de CPU.

Um detalhe do ambiente que reforça o ponto: VM2 e VM3 são **processos em
máquinas diferentes**, então entre elas há paralelismo real, limitado apenas
pelas vCPUs que o hypervisor distribui.
