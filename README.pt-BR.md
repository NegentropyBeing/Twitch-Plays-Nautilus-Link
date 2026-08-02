# TwitchPlays: control-credit & mayhem

Dois bots que permitem controlar um jogo pelo chat da Twitch, construídos
sobre o template TwitchPlays original do DougDoug. Os comandos do chat são
enviados para um **controle de jogo virtual**, em vez de emular o
teclado/mouse reais -- assim, o computador que executa o bot continua
totalmente livre para uso normal enquanto o bot está rodando, já que nada é
digitado na janela que estiver em foco no momento.

Existem duas variantes, para dois estilos diferentes de jogo controlado
pelo chat:

## `control-credit`
- **3 times** (A, B, C).
- O Time A pode enviar comandos em qualquer momento. A cada 7 comandos
  enviados pelo Time A, um "crédito de turno" é acumulado para o lado
  adversário -- tanto o Time B quanto o Time C podem usá-lo, valendo para
  quem enviar um comando primeiro.
- Todos os times compartilham **um único** controle virtual.
- Bom para um formato "chat contra chat" mais estruturado, que respeita
  turnos.

## `mayhem`
- **Até 8 times** (de A a H).
- Sem sistema de turnos -- qualquer pessoa registrada em um time pode
  enviar um comando no instante em que digitar.
- **Cada time tem seu próprio controle virtual independente.**
- Bom para caos total e simultâneo, com vários lados jogando ao mesmo tempo
  (desde que o jogo/emulador realmente suporte esse número de jogadores).

Ambas as variantes possuem:
- Uma **lista de competidores** -- apenas usuários registrados conseguem
  acionar um comando, então o chat geral pode conversar livremente sem
  disparar nada por acidente.
- **Edição da lista de jogadores em tempo real** -- administradores (o
  streamer, por padrão) podem adicionar competidores e atribuí-los a times
  durante a live, via comandos no chat (`!addcompetitor`, `!addteam`), sem
  precisar reiniciar o script.

---

## Requisitos

- **Windows** (a abordagem de controle virtual depende do driver ViGEmBus,
  que funciona apenas no Windows).
- **Python 3.9 ou superior**
- Um emulador ou jogo que aceite entrada por controle (ex: BizHawk,
  RetroArch).

## Instalando as dependências

1. Instale o [Python 3.9+](https://www.python.org/downloads/) (marque a
   opção "Add Python to PATH" durante a instalação).
2. Instale o driver [ViGEmBus](https://github.com/ViGEm/ViGEmBus/releases)
   -- baixe o `.msi`, clique com o botão direito e selecione **Executar
   como administrador**. Reinicie o computador se for solicitado.
3. Instale os pacotes Python:
   ```
   python -m pip install vgamepad requests keyboard
   ```
4. Confirme que tudo está funcionando usando o `test_vgamepad.py` (veja
   abaixo), e verifique se o(s) controle(s) aparecem na lista de controles
   do Windows (`joy.cpl`).

## Testando sua configuração com `test_vgamepad.py`

Antes de rodar qualquer um dos bots de verdade, use o `test_vgamepad.py`
para confirmar que o ViGEmBus/vgamepad estão funcionando e para entender
como os controles virtuais se comportam -- sem precisar de conexão com a
Twitch.

```
python test_vgamepad.py
```

Ele é interativo: pergunta quantos controles virtuais criar, e depois pede
para cada um uma sequência de botões separada por vírgulas. Exemplo:

```
How many controllers do you want to queue this round? 2
Controller 1 sequence: a, b, up, up, down, down
Controller 2 sequence: a, up, up, up, left, left, left, left
```

- Todos os controles executam sua sequência **ao mesmo tempo** (cada um
  toca sua própria sequência em ordem; um controle não espera pelo outro).
- Quando todos os controles terminam sua sequência, ele pergunta pela
  próxima rodada, permitindo enfileirar uma nova sequência sem reiniciar o
  script.
- Nomes de botões reconhecidos: `up`, `down`, `left`, `right`, `a`, `b`,
  `x`, `y`, `start`, `select`, `l`, `r` -- o mesmo conjunto usado no
  `COMMAND_MAP`.
- Pressione **Ctrl+C** em qualquer prompt para parar tudo e resetar todos
  os controles corretamente.
- Observação: mais de 4 controles ainda aparecem normalmente no `joy.cpl`,
  mas jogos que usam a API XInput diretamente só reconhecem os primeiros 4
  -- a mesma limitação já mencionada na seção do `mayhem` acima.

## Executando

```
python control-credit.py
```
ou
```
python mayhem.py
```

Cada script vai perguntar (no terminal):
1. A lista completa de competidores.
2. Os nomes de usuário de cada time.
3. Administradores adicionais que podem adicionar jogadores em tempo real.

Depois disso, uma contagem regressiva de 5 segundos começa (troque para o
seu jogo/emulador durante esse tempo) antes de conectar ao chat.

Edite `TWITCH_CHANNEL` no início de qualquer um dos scripts antes de
executar, e ajuste o `COMMAND_MAP` para corresponder aos botões que fazem
sentido para o seu jogo.

## Lista de comandos

Estes são os comandos padrão do chat em `COMMAND_MAP`, idênticos nos dois
scripts (apenas o tipo de controle usado internamente é diferente):

| Comando no chat | Botão            |
|------------------|-------------------|
| `up`             | Direcional Cima   |
| `down`           | Direcional Baixo  |
| `left`           | Direcional Esquerda |
| `right`          | Direcional Direita |
| `a`              | A / Cross         |
| `b`              | B / Circle        |
| `x`              | X / Square        |
| `y`              | Y / Triangle      |
| `start`          | Start/Options     |
| `select`         | Select/Share      |
| `l`              | Botão traseiro esquerdo |
| `r`              | Botão traseiro direito  |

Edite o `COMMAND_MAP` em qualquer um dos scripts para adicionar, remover ou
renomear comandos. Apenas competidores registrados em um time conseguem
acionar esses comandos -- qualquer outra pessoa digitando o mesmo texto é
simplesmente ignorada.

### Repetindo um comando (contornando a trava de mensagens repetidas da Twitch)

A Twitch silencia mensagens idênticas repetidas por cerca de 30 segundos.
Para contornar isso, os dois scripts removem pontos finais antes de
comparar o comando -- então, se precisar enviar o mesmo comando de novo
rapidamente, basta adicionar um ponto (ou alguns):

```
a
a.
a..
a...
```

Todas essas quatro mensagens são tratadas exatamente como o mesmo comando
`a`. Isso vale automaticamente para qualquer entrada do `COMMAND_MAP`, sem
precisar de configuração extra.

## Adicionando alguém a um time (apenas admin, em tempo real via chat)

Os dois bots suportam os mesmos dois comandos de administrador, digitados
diretamente no chat pelo streamer (ou por qualquer outra pessoa listada em
`ADMIN_USERS`):

**Registrar alguém como competidor** (sem ainda colocá-lo em um time):
```
!addcompetitor usuario
```
ou vários de uma vez:
```
!addcompetitor usuario1; usuario2; usuario3
```

**Adicionar alguém diretamente a um time** (também registra a pessoa como
competidora automaticamente, caso ainda não estivesse):
```
!addteam <letra> usuario
```
ou vários de uma vez:
```
!addteam <letra> usuario1; usuario2
```

- No **`control-credit`**, `<letra>` deve ser `A`, `B` ou `C`.
- No **`mayhem`**, `<letra>` pode ser qualquer uma de `A` a `H`.

Exemplo, adicionando duas pessoas ao Time B no `mayhem`:
```
!addteam B goblin_king; peter_parker
```

**Conceder privilégios de admin a outra pessoa** (apenas um admin já
existente pode fazer isso -- um viewer comum digitando este comando não
tem nenhum efeito):
```
!addadmin usuario
```
ou vários de uma vez:
```
!addadmin usuario1; usuario2
```

Qualquer mensagem que não seja enviada por um admin, ou que não siga um
desses formatos, é tratada como uma mensagem normal do chat (ignorada,
caso não seja um comando de jogo reconhecido).

## Encerrando o bot

Pressione **Shift+Backspace** no terminal onde o script está rodando.

---

## Créditos

Este projeto é uma continuação/fork do **template TwitchPlays do
DougDoug**, que por sua vez foi originalmente baseado em:

- **Wituz** -- [tutorial original "Twitch Plays"](http://www.wituz.com/make-your-own-twitch-plays-stream.html)
- **DougDoug** -- o template TwitchPlays sobre o qual este repositório foi
  construído
- **DDarknut** -- adicionou suporte ao chat do YouTube
- **Ottomated** -- ajudou com a parte do YouTube

O código de conexão com o chat (`TwitchPlays_Connection.py`) e o módulo
opcional legado de emulação de teclado (`TwitchPlays_KeyCodes.py`) vêm
diretamente daquele projeto original. O sistema de times, a edição de
jogadores em tempo real e a entrada baseada em controle virtual (tanto a
versão de um único controle quanto a de 8 controles) são adições novas
construídas em cima dele.

Licenciado sob a licença MIT (veja `LICENSE`) -- direitos autorais
originais de DougDoug, 2024.
