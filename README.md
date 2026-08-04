# TwitchPlays: control-credit & mayhem

*(English below; Português mais abaixo)*

Two Twitch-chat-controlled game bots, built on top of DougDoug's original
TwitchPlays template. Chat commands are sent to a **virtual game
controller** rather than emulating the real keyboard/mouse, so the computer
running the bot stays free for normal use while it's running -- nothing
gets typed into whatever window happens to be focused.

There are two variants:

## `control-credit`
- **2 teams** (A and B).
- Team A can send commands at any time, with no waiting. Every 7 commands
  Team A sends, one "turn credit" is banked for Team B to spend.
- Both teams share **one** virtual controller.
- Good for a structured, turn-respecting "chat vs chat" format.

## `mayhem`
- Asks at startup **how many teams you want** (1 to 8, lettered A onward).
- No turn system at all -- anyone registered to a team can send a command
  the instant they type it.
- **Each team gets its own independent virtual controller.**
- Good for total, simultaneous, many-sided chaos (as long as your
  game/emulator actually supports that many players).

Both variants support:
- A **competitors list** -- only registered usernames can ever trigger a
  command, so general chat can talk freely without accidentally doing
  anything.
- **Live roster editing** -- admins (the broadcaster, by default) can add
  competitors and assign them to teams mid-stream via chat commands, no
  restart required.
- Working around Twitch's duplicate-message lock by adding trailing dots
  to a repeated command.

---

## Requirements

- **Windows** (the virtual controller approach relies on the ViGEmBus
  driver, which is Windows-only).
- **Python 3.9+**
- An emulator or game that accepts controller input (e.g. BizHawk,
  RetroArch).

## Installing dependencies

1. Install [Python 3.9+](https://www.python.org/downloads/) (check "Add
   Python to PATH" during setup).
2. Install the [ViGEmBus driver](https://github.com/ViGEm/ViGEmBus/releases)
   -- download the `.msi`, right-click it and **Run as administrator**.
   Reboot afterward if prompted.
3. Install the Python packages:
   ```
   python -m pip install vgamepad requests keyboard
   ```
4. Verify the setup works using `test_vgamepad.py` (see below), and confirm
   the controller(s) show up in Windows' game controller list (`joy.cpl`).

## Testing your setup with `test_vgamepad.py`

Before running either bot for real, use `test_vgamepad.py` to confirm
ViGEmBus/vgamepad are working and to get a feel for how virtual controllers
behave -- no Twitch connection needed.

```
python test_vgamepad.py
```

It's interactive. Example session:

```
How many controllers do you want to queue this round? 3
Controller 1 sequence: b, up (repeat, infinite)
Controller 2 sequence: b, up (repeat, 3x)
Controller 3 sequence: a, down (repeat, infinite)
Delay before executing (seconds, 0 for none): 30
Run controllers simultaneously or in sequence? (simultaneous/sequential): simultaneous
```

- Add `(repeat, 3x)` (or any number) to make a controller repeat that many
  times. Add `(repeat, infinite)` to make it repeat forever in the
  background -- the script still moves on and asks for the next round
  without waiting for it. Leave the directive off entirely to just run the
  sequence once.
- **Delay**: how long to wait, once the whole round is planned out, before
  anything actually starts running -- useful for switching to your
  game/emulator window first.
- **Simultaneous vs sequential**: simultaneous starts every controller at
  once; sequential runs controller 1 first, then controller 2, and so on
  (a controller repeating infinitely can't be waited on, so it just starts
  in the background and the script moves on to the next one immediately).
- In a later round, leaving a controller's line **blank** stops whatever
  it's currently repeating; giving it a **new** sequence instead replaces
  (stops, then restarts) it.
- The whole round -- every controller's sequence, the delay, and the mode
  -- is fully planned out from your answers *before* any virtual
  controller is created or touched, so nothing partially set up sits
  around while you're still answering prompts.
- Recognized button names: `up`, `down`, `left`, `right`, `a`, `b`, `x`,
  `y`, `start`, `select`, `l`, `r` -- same set used in `COMMAND_MAP`.
- Press **Ctrl+C** at any prompt to stop everything and reset all
  controllers cleanly.
- Note: more than 4 controllers still show up fine in `joy.cpl`, but games
  using the XInput API directly will only ever recognize the first 4.

## Running

```
python control-credit.py
```
or
```
python mayhem.py
```

`mayhem.py` first asks how many teams (1-8) you want to use. Both scripts
then prompt (in the terminal) for:
1. The full list of competitors.
2. Usernames for each team.
3. Any additional admins who can add players live.

Then it counts down 5 seconds (switch to your game/emulator during this
window) before connecting to chat.

Edit `TWITCH_CHANNEL` near the top of either script before running, and
adjust `COMMAND_MAP` to match whatever buttons make sense for your game.

## Command list

These are the default chat commands in `COMMAND_MAP`, identical in both
scripts (only the underlying controller type differs internally):

| Chat command | Button        |
|--------------|---------------|
| `up`         | D-pad Up      |
| `down`       | D-pad Down    |
| `left`       | D-pad Left    |
| `right`      | D-pad Right   |
| `a`          | A / Cross     |
| `b`          | B / Circle    |
| `x`          | X / Square    |
| `y`          | Y / Triangle  |
| `start`      | Start/Options |
| `select`     | Select/Share  |
| `l`          | Left shoulder |
| `r`          | Right shoulder|

Edit `COMMAND_MAP` in either script to add, remove, or rename commands.
Only registered competitors on a team can trigger these -- everyone else's
identical text is just ignored.

### Repeating a command (getting around Twitch's duplicate-message lock)

Twitch mutes a user's identical repeated message for about 30 seconds. To
work around this, both scripts strip trailing dots before matching a
command -- so if you need to send the same command again right away, just
add a period (or a few):

```
a
a.
a..
a...
```

All four are treated as the exact same `a` command. This applies to every
entry in `COMMAND_MAP` automatically, no extra configuration needed.

## Adding someone to a team (admin only, live via chat)

Both bots support the same admin commands, typed directly into chat by the
broadcaster (or anyone else listed in `ADMIN_USERS`):

**Register someone as a competitor** (without putting them on a team yet):
```
!addcompetitor username
```
or several at once:
```
!addcompetitor username1; username2; username3
```

**Add someone straight onto a team** (also registers them as a competitor
automatically, if they weren't already):
```
!addteam <letter> username
```
or several at once:
```
!addteam <letter> username1; username2
```

- In **`control-credit`**, `<letter>` must be `A` or `B`.
- In **`mayhem`**, `<letter>` can be any letter used by the number of teams
  you chose at startup (e.g. `A`-`C` if you chose 3 teams).

Example, adding two people to Team B:
```
!addteam B goblin_king; peter_parker
```

**Grant admin rights to someone else** (only an existing admin can do this
-- a regular viewer typing this command has no effect):
```
!addadmin username
```
or several at once:
```
!addadmin username1; username2
```

Anything that isn't sent by an admin, or doesn't match one of these
formats, is just treated as a normal (ignored, if not a recognized game
command) chat message.

## Ending the bot

Press **Shift+Backspace** in the terminal running the script.

---

## Credits

This project is a fork/evolution of **DougDoug's TwitchPlays template**,
itself originally based on:

- **Wituz** -- original ["Twitch Plays" tutorial](http://www.wituz.com/make-your-own-twitch-plays-stream.html)
- **DougDoug** -- the TwitchPlays template this repo builds on
- **DDarknut** -- added YouTube chat support
- **Ottomated** -- helped with the YouTube side of things

The chat-connection code (`TwitchPlays_Connection.py`) and the optional
legacy keyboard-emulation module (`TwitchPlays_KeyCodes.py`) descend
directly from that original project. The team systems, live roster
editing, and virtual-controller-based input (both the single-controller
and multi-controller versions) are new additions built on top of it.

Licensed under the MIT License (see `LICENSE`) -- original copyright
DougDoug, 2024.

<br><br>

---

# TwitchPlays: control-credit & mayhem (Português)

Dois bots que permitem controlar um jogo pelo chat da Twitch, construídos
sobre o template TwitchPlays original do DougDoug. Os comandos do chat são
enviados para um **controle de jogo virtual**, em vez de emular o
teclado/mouse reais -- assim, o computador que executa o bot continua
livre para uso normal enquanto o bot está rodando, já que nada é digitado
na janela que estiver em foco no momento.

Existem duas variantes:

## `control-credit`
- **2 times** (A e B).
- O Time A pode enviar comandos em qualquer momento, sem espera. A cada 7
  comandos enviados pelo Time A, um "crédito de turno" é acumulado para o
  Time B usar.
- Os dois times compartilham **um único** controle virtual.
- Bom para um formato "chat contra chat" mais estruturado, que respeita
  turnos.

## `mayhem`
- Pergunta no início **quantos times você quer usar** (de 1 a 8, com letras
  a partir de A).
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
  durante a live, via comandos no chat, sem precisar reiniciar o script.
- Uma forma de contornar a trava de mensagens repetidas da Twitch,
  adicionando pontos finais a um comando repetido.

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

Ele é interativo. Exemplo de sessão:

```
How many controllers do you want to queue this round? 3
Controller 1 sequence: b, up (repeat, infinite)
Controller 2 sequence: b, up (repeat, 3x)
Controller 3 sequence: a, down (repeat, infinite)
Delay before executing (seconds, 0 for none): 30
Run controllers simultaneously or in sequence? (simultaneous/sequential): simultaneous
```

- Adicione `(repeat, 3x)` (ou qualquer número) para fazer um controle
  repetir aquela quantidade de vezes. Adicione `(repeat, infinite)` para
  fazer o controle repetir para sempre, em segundo plano -- o script
  continua e pergunta pela próxima rodada sem esperar por ele. Não
  adicionar a diretiva faz a sequência rodar apenas uma vez.
- **Delay**: quanto tempo esperar, depois que toda a rodada foi planejada,
  antes de qualquer coisa começar a rodar de fato -- útil para trocar para
  a janela do seu jogo/emulador primeiro.
- **Simultâneo vs sequencial**: simultâneo faz todos os controles
  começarem juntos; sequencial roda o controle 1 primeiro, depois o 2, e
  assim por diante (um controle repetindo infinitamente não pode ser
  esperado, então ele só começa em segundo plano e o script já segue para
  o próximo).
- Em uma rodada posterior, deixar a linha de um controle **em branco** para
  o que estiver repetindo; dar uma **nova** sequência substitui (para,
  depois reinicia) o que estava fazendo antes.
- A rodada inteira -- a sequência de cada controle, o delay e o modo -- é
  totalmente planejada a partir das suas respostas *antes* de qualquer
  controle virtual ser criado ou tocado, então nada fica parcialmente
  configurado enquanto você ainda está respondendo perguntas.
- Nomes de botões reconhecidos: `up`, `down`, `left`, `right`, `a`, `b`,
  `x`, `y`, `start`, `select`, `l`, `r` -- o mesmo conjunto usado no
  `COMMAND_MAP`.
- Pressione **Ctrl+C** em qualquer prompt para parar tudo e resetar todos
  os controles corretamente.
- Observação: mais de 4 controles ainda aparecem normalmente no `joy.cpl`,
  mas jogos que usam a API XInput diretamente só reconhecem os primeiros 4.

## Executando

```
python control-credit.py
```
ou
```
python mayhem.py
```

O `mayhem.py` primeiro pergunta quantos times (1-8) você quer usar. Depois,
os dois scripts perguntam (no terminal):
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

Os dois bots suportam os mesmos comandos de administrador, digitados
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

- No **`control-credit`**, `<letra>` deve ser `A` ou `B`.
- No **`mayhem`**, `<letra>` pode ser qualquer letra dentro da quantidade
  de times escolhida no início (ex: `A`-`C` se você escolheu 3 times).

Exemplo, adicionando duas pessoas ao Time B:
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
diretamente daquele projeto original. Os sistemas de times, a edição de
jogadores em tempo real e a entrada baseada em controle virtual (tanto a
versão de um único controle quanto a de múltiplos controles) são adições
novas construídas em cima dele.

Licenciado sob a licença MIT (veja `LICENSE`) -- direitos autorais
originais de DougDoug, 2024.
