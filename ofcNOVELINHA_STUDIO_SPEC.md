# NOVELINHA STUDIO — ESPECIFICAÇÃO DO PROJETO (para desenvolvimento no Codex)

> Versão 1.1. Documento único de referência: visão, restrições reais de produção, estrutura de pastas, modelos de dados, motor de prompts, planejador de créditos, CLI, roadmap e regras para o agente. Idioma: documentação em português do Brasil. Código, nomes de arquivos, pastas, chaves YAML e mensagens de commit em inglês.

**Mudanças da v1.0 para a v1.1 (aprendidas em produção real):**

- Geração de **imagem é gratuita** no Flow; **só vídeo gasta créditos**. Custos por resolução e
  duração vêm exclusivamente de `config/production.yaml`.
- Novo conceito de **cold open** (teaser de abertura de \~3 s reaproveitado de um clipe já gerado, custo zero) com transição.  
- Novo **modo de ritmo de produção**: imagens em lote primeiro (grátis, com várias tentativas) e vídeos depois, ou sequencial plano a plano.  
- **Apelidos de personagem** (ex.: a Manu chama Duda de "Dudu") e regra "o lock\_block segue a imagem aprovada".  
- **Controle de tentativas de vídeo** (máximo 2 por plano) e modo de voz (`native` ou `post`).  
- Novos comandos `studio next` e `studio session` (folha de sessão para copiar e colar no Flow).  
- Série de exemplo e estado atual atualizados com o episódio 1 real.

---

## 0\. COMO USAR ESTE DOCUMENTO

1. Cria um repositório vazio chamado `novelinha-studio`.  
2. Coloca este arquivo em `docs/SPEC.md`.  
3. Copia a seção 15 (AGENTS.md) para a raiz do repositório como `AGENTS.md`.  
4. Pede ao Codex: "Leia `docs/SPEC.md` e `AGENTS.md`. Implemente a Fase 1 do roadmap (seção 13). Não avance para a fase seguinte sem eu aprovar."  
5. Depois de cada fase, atualiza a seção 16 (Estado atual).

---

## 1\. VISÃO

Um **estúdio de produção de novelinhas (dramas curtos verticais) feitas por IA**, organizado como um repositório de arquivos \+ uma CLI em Python. Ele **não gera imagem nem vídeo**. Quem gera é o Google Flow (ou outra ferramenta), operado manualmente pelo criador em várias contas gratuitas. O criador copia os prompts prontos que o Studio gera e cola no Flow.

O que o Studio faz:

- Guarda a **bíblia de cada série** (personagens, cenários, estilo, episódios) em arquivos estruturados.  
- **Monta os prompts** de imagem e de vídeo automaticamente, sempre com os blocos de personagem travados e o bloco de estilo, evitando erro de copiar e colar.  
- **Planeja os créditos** (que hoje só são gastos em vídeo) e distribui os vídeos entre as contas.  
- Gera uma **folha de sessão**: a lista, em ordem, do que gerar, o que anexar e o prompt pronto para copiar.  
- **Controla o status** de cada plano (prompt pronto, imagem aprovada, vídeo aprovado, editado, postado).  
- Padroniza **nomes de arquivos e pastas** para nada se perder entre contas.  
- Serve para **qualquer estilo**: drama realista hoje, frutinhas humanas amanhã, animação, terror, comédia etc. O estilo é um "preset" trocável.

O que o Studio NÃO faz (fora de escopo):

- Não chama API de geração de imagem/vídeo. Não automatiza login, criação de contas nem qualquer uso do Flow.  
- Não escreve o roteiro sozinho (o roteiro vem do Claude ou de outro gerador e é salvo nos arquivos da série).  
- Não edita vídeo (edição é no CapCut). Só registra as instruções de edição (cold open, transições, legendas).

## 2\. PRINCÍPIOS DE DESIGN

1. **Arquivos são a fonte da verdade.** Tudo em YAML/Markdown versionável no Git. Sem banco de dados no MVP.  
2. **Uma série \= uma pasta autocontida.** Copiar a pasta para outra máquina deve bastar.  
3. **Estilo desacoplado da história.** Trocar o preset de estilo não deve exigir reescrever roteiro nem personagens.  
4. **Crédito de vídeo é o gargalo.** Imagem é grátis: iterar à vontade em imagem, gastar vídeo só depois de aprovar a imagem.  
5. **Texto travado, mas fiel à imagem aprovada.** A descrição de cada personagem é uma linha fixa reutilizada literalmente em todo prompt. Depois que uma imagem com o personagem é aprovada, o `lock_block` deve ser ajustado para descrever exatamente o que a IA gerou (roupa, cabelo, detalhes), não o que se imaginava antes.  
6. **Portável.** Python puro, poucas dependências, roda em Windows (o usuário usa Windows).  
7. **Humano no loop.** O Studio gera o texto para colar; o humano gera a mídia, aprova e marca o status.

## 3\. RESTRIÇÕES REAIS DE PRODUÇÃO (VÃO PARA `config/production.yaml`)

Valores atuais informados pelo usuário (devem ser configuráveis, nunca hardcoded):

| Parâmetro | Valor atual | Observação |
| :---- | :---- | :---- |
| Ferramenta de geração | Google Flow | modelo mais recente |
| Formato | 9:16 vertical |  |
| Resolução de vídeo | perfil ativo | escolhida pelo perfil em `config/production.yaml` |
| Duração de clipe de vídeo | `video.default_duration_s` |  |
| Custo de vídeo | `config/production.yaml` | `null` significa custo desconhecido |
| Custo de imagem | **0 créditos** | geração de imagem é gratuita |
| Créditos por conta por dia | 50 |  |
| Vídeos por conta por dia | calculado pelo config | futuro planner usa custos conhecidos |
| Número de contas | 5 |  |
| Vídeos por dia (todas as contas) | 35 |  |
| Reserva de segurança | 1 vídeo por conta | para retentativa |
| Máximo de tentativas de vídeo por plano | 2 |  |
| Modo de voz padrão | `native` | se falhar, `post` (voz colocada no CapCut) |

Notas:

- O Flow não compartilha imagens entre contas. A consistência entre contas depende de baixar as imagens e vídeos aprovados e subi-los como referência em outras contas (ver seção 9).  
- Usar várias contas gratuitas pode violar os termos de uso da ferramenta e gerar bloqueio. O usuário assume esse risco. O Studio deve mostrar um aviso curto na primeira execução da CLI e nunca automatizar acesso às contas.  
- Antes de postar, checar as regras vigentes da plataforma sobre rotulagem de conteúdo gerado por IA e os requisitos de monetização (mudam com frequência). O comando `studio caption` deve incluir esse lembrete.

## 4\. ESTRUTURA DE PASTAS

novelinha-studio/

├── AGENTS.md                      \# regras para o Codex (seção 15\)

├── README.md                      \# resumo curto e comandos principais

├── pyproject.toml                 \# dependências e entry point da CLI

├── docs/

│   ├── SPEC.md                    \# este documento

│   ├── WORKFLOW.md                \# passo a passo humano (seção 10 expandida)

│   └── LESSONS.md                 \# lições aprendidas de produção (prompts que funcionaram/falharam)

├── config/

│   ├── production.yaml            \# custos, créditos, contas, reserva, modo de ritmo (seção 3\)

│   └── accounts.yaml              \# lista das contas (apelidos, sem senhas)

├── styles/                        \# presets de estilo, independentes de série

│   ├── \_template.yaml

│   ├── realistic\_drama.yaml

│   └── fruit\_humans.yaml

├── templates/                     \# modelos usados para criar séries/episódios/prompts

│   ├── series/

│   │   ├── series.yaml

│   │   ├── characters.yaml

│   │   ├── locations.yaml

│   │   └── bible.md

│   ├── episode/

│   │   ├── episode.yaml

│   │   ├── script.md

│   │   └── shots.yaml

│   └── prompts/                   \# templates Jinja2 do motor de prompts

│       ├── image\_anchor.j2

│       ├── image\_derivative.j2

│       ├── video\_from\_image.j2

│       ├── video\_expression\_only.j2

│       ├── session\_sheet.j2

│       └── post\_caption.j2

├── series/                        \# UMA PASTA POR SÉRIE

│   └── revenge\_republic/          \# exemplo real (seção 14\)

│       ├── series.yaml

│       ├── characters.yaml

│       ├── locations.yaml

│       ├── bible.md

│       ├── references/            \# material de referência (roteiros originais, prints)

│       ├── episodes/

│       │   └── ep01/

│       │       ├── episode.yaml   \# metadados e status geral

│       │       ├── script.md      \# roteiro final enxuto (pt-BR)

│       │       ├── shots.yaml     \# lista de planos (fonte da verdade)

│       │       ├── prompts/       \# prompts gerados (um .md por plano) \+ session\_sheet.md

│       │       ├── assets/

│       │       │   ├── images/    \# imagens aprovadas (EP01\_P01\_image.jpg)

│       │       │   ├── videos/    \# vídeos aprovados (EP01\_P01\_video.mp4)

│       │       │   └── audio/     \# vozes e músicas

│       │       ├── edit/          \# projeto do CapCut, legendas .srt

│       │       └── export/        \# vídeo final do episódio \+ capa \+ legenda de post

│       └── shared\_assets/         \# referências reutilizáveis da série

│           ├── anchors/           \# imagens âncora (personagens \+ cenário)

│           └── characters/        \# fotos de referência de rosto, se houver

├── src/

│   └── studio/

│       ├── \_\_init\_\_.py

│       ├── cli.py                 \# comandos Typer

│       ├── config.py              \# carrega config/production.yaml

│       ├── models.py              \# modelos Pydantic (seção 5\)

│       ├── loader.py              \# carrega/valida série, episódio, shots

│       ├── prompts.py             \# motor de prompts (seção 7\)

│       ├── credits.py             \# planejador de créditos (seção 8\)

│       ├── allocator.py           \# distribuição de vídeos entre contas (seção 8\)

│       ├── session.py             \# folha de sessão e comando "next"

│       ├── naming.py              \# convenção de nomes e validação (seção 9\)

│       ├── status.py              \# controle de status e relatório

│       └── scaffold.py            \# cria séries/episódios a partir de templates

├── tests/

│   ├── test\_models.py

│   ├── test\_prompts.py

│   ├── test\_credits.py

│   ├── test\_allocator.py

│   ├── test\_session.py

│   ├── test\_naming.py

│   └── fixtures/

│       └── series\_minimal/

└── output/                        \# relatórios gerados (não versionar)

    └── .gitkeep

Regras de estrutura:

- Nada de senha, token ou e-mail real das contas em nenhum arquivo. Só apelidos (`conta1`, `conta2`).  
- Arquivos de mídia (`assets/`, `export/`) ficam no `.gitignore`. Versionar apenas YAML, Markdown e templates. Prompts gerados podem ser versionados.

## 5\. MODELOS DE DADOS (YAML \+ PYDANTIC)

### 5.1 `series.yaml`

id: revenge\_republic

title: "Nome da série"

genre: "drama de vingança e college"

audience: "jovens 18-24"

language: pt-BR

aspect\_ratio: "9:16"

style: realistic\_drama          \# id do preset em /styles

episodes\_planned: 10

episode\_target\_seconds: \[30, 90\]

logline: "Uma frase que vende a série."

synopsis: "Resumo completo."

season\_hook: "Gancho da próxima temporada."

status: in\_production           \# idea | planning | in\_production | paused | released

profile: null                    \# sobrescreve active_profile quando preenchido

### 5.2 `characters.yaml`

characters:

  \- id: duda

    name: Duda

    full\_name: Eduarda

    nicknames:

      \- name: Dudu

        used\_by: \[manu\]          \# só a Manu chama assim

    role: villain                \# protagonist | villain | ally | love\_interest | support

    age: 20

    lock\_version: 2

    lock\_block: \>-               \# UMA linha em inglês, copiada LITERALMENTE em todo prompt

      Duda, 20-year-old Brazilian woman, straight blonde hair, big eyes,

      flawless makeup, pastel pink V-neck knit top, two thin gold necklaces, black pants

    signature\_element: "gold necklaces"

    hair\_color: blonde

    silhouette\_hook: "geometric triangular nose"

    silhouette\_hook\_pt: "nariz triangular geométrico"

    palette: "pastel pink, gold and black"

    voice\_notes: "voz suave e doce em público; baixa e fria quando está sozinha"

    default\_delivery: "low, cold, controlled"

    default\_delivery\_pt: "baixa, fria, controlada"

    bio\_pt: "Descrição em português (personalidade, falha, arco)."

    arc\_pt: "De X para Y."

    approved\_reference: shared\_assets/anchors/EP01\_P02\_image.jpg   \# imagem em que o rosto foi aprovado

Regras de validação:

- `lock_block` obrigatório, uma única linha lógica em inglês.  
- Aviso se dois personagens com `hair_color` igual aparecerem no mesmo plano.  
- Aviso: personagem sem `silhouette_hook` quando `character_rules` do estilo exige silhueta.
- Aviso: `silhouette_hook` ausente do `lock_block`.
- Aviso: dois personagens no mesmo plano com `silhouette_hook` ou `hair_color` iguais.
- Erro: termo em `safety.blocked_terms` encontrado em `lock_block`, `style_block` ou `action`. A
  lista é uma rede de segurança heurística, não uma garantia contra IP ou semelhança.
- Aviso se `signature_element` não aparecer dentro do `lock_block`.  
- O `lock_block` só muda com incremento de `lock_version` e nota em `docs/LESSONS.md`. Mudança de `lock_version` deve gerar aviso de que planos já aprovados usam a versão antiga.  
- `nicknames` alimentam as falas: o Studio avisa se um personagem que não está em `used_by` usa o apelido no `dialogue_pt`.

### 5.3 `locations.yaml`

locations:

  \- id: kitchen

    name: "Cozinha da república"

    description\_en: "small student house kitchen, cluttered shelves, window on the left, worn wooden counter"

    default\_light: "late afternoon golden light"

  \- id: living\_room

    description\_en: "student house living room, wooden table, newspapers and notebooks"

    default\_light: "night, warm lamp light"

### 5.4 `styles/<id>.yaml` (preset de estilo)

id: realistic\_drama

name: "Drama realista"

style\_block: \>-

  Realistic cinematic style, soft natural lighting, shallow depth of field,

  film look, vertical 9:16

negative\_hints: "no text, no watermark, no extra fingers"

camera\_defaults: "slight handheld feel"

video\_motion\_defaults: "subtle natural motion"

notes: "Bom para drama, vingança, romance. Evitar movimento exagerado em rostos."

character\_rules: "Descrever pessoas com traços realistas e figurino simples."

Presets obrigatórios como dados: `realistic_drama` e `fruit_humans`. A estrutura deve ser idêntica para o motor de prompts funcionar sem mudança de código.

### 5.5 `episodes/epNN/episode.yaml`

id: ep01

title: "Título do episódio"

number: 1

target\_seconds: 60

cold\_open:

  enabled: true

  source\_shot: P01              \# plano de onde sai o teaser

  trim\_start\_s: 0.0

  trim\_end\_s: 3.5               \# cortar no ponto de maior curiosidade (deixar a frase no ar)

  transition: "white flash \+ impact sound"

  title\_card\_pt: "Horas antes..."

cliffhanger: "Descrição do cliffhanger final."

season\_finale: false

profile: null                    \# sobrescreve o perfil da série

key\_prop: "objeto-chave do episódio"

status: generating     \# planning | scripted | prompts\_ready | generating | editing | ready | posted

metrics: {}            \# preencher após postar: views, retenção 3s, % assistido, comentários pedindo parte 2

notes: ""

Cálculo de duração do lint: `estimated_runtime_s = soma das durações dos vídeos aprovados ou
planejados + (cold_open.trim_end_s - cold_open.trim_start_s)`. O Studio compara com
`target_seconds` e avisa quando a diferença passa de 10%.

### 5.6 `episodes/epNN/shots.yaml` (fonte da verdade da produção)

shots:

  \- id: P01

    order: 0

    kind: video\_from\_image          \# anchor\_image | derived\_image | video\_from\_image

    role: hook                      \# hook | body | cliffhanger

    location: kitchen

    characters: \[duda\]

    framing: "extreme close-up"

    action: "sweet fragile expression drops into a cold calculating smirk"

    camera: "very slow push-in"

    gaze: "off-camera toward a mirror"   \# opcional; evita olhar direto para a câmera quando não for desejado

    parent: P01i                    \# plano de imagem de origem

    dialogue\_pt:

      \- speaker: duda

        text: "Se ele chegar perto demais... eu conto que ela tá com outro."

        delivery: "low, cold, controlled"

        delivery\_pt: "baixa, fria, controlada"

    voice\_over\_pt: []

    intentional\_silence: false

    beat\_pt: "Duda transforma a ameaça em plano de chantagem."

    voice\_mode: native              \# native | post

    duration\_s: 8

    account: conta1

    status: approved                \# todo | prompt\_ready | generated | approved | rejected | edited

    video\_attempts: 1

    files:

      video: assets/videos/EP01\_P01\_video.mp4

    notes: "usado como cold open (0 a 3,5 s)"

Regras:

- `anchor_image`: imagem nova com todos os personagens do cenário. Pode receber **imagem de referência de outro plano** (`reference_from: P02i`) para herdar o rosto de personagens já aprovados.  
- `derived_image`: imagem derivada de uma âncora (`parent` obrigatório).  
- `video_from_image`: vídeo animado a partir de uma imagem aprovada (`parent` obrigatório). Máximo de 1 ação principal por clipe.  
- No máximo 2 falas (dois `dialogue_pt`) por clipe de 8 s. Aviso acima disso.  
- `video_attempts` \> `max_video_attempts` gera aviso e sugestão de trocar `voice_mode` para `post` ou reescrever o prompt.  
- Custo vem de `config/production.yaml` por `kind` (imagem \= 0).

### 5.7 `config/production.yaml`

tool: google\_flow

aspect\_ratio: "9:16"

video:

  costs_verified_on: null

  costs_max_age_days: 30

  costs:

    360p: {6: 5, 8: 6, 10: 7}

    1080p: {6: null, 8: null, 10: null}

  max\_attempts: 2

image:

  credits: 0

accounts:

  count: 5

  daily\_credits\_per\_account: 50

  reserve\_videos\_per\_account: 1

workflow:

  mode: images\_first            \# images\_first | sequential

pacing:

  words_per_second: 2.5

  min_speech_fill: 0.6

  max_silence_s: 1.5

  max_dialogue_lines: 2

  max_words_per_line: 15

  max_intentional_silences_per_episode: 1

  delivery_forbidden_markers: [" or ", ";", " when "]

  enforcement:

    low_fill: error

    excess_silence: error

    missing_hook: warning

    profile_duration: error

bible:

  min_section_chars: 80

  placeholder_markers: ["TODO", "Describe", "Descreva", "XXX"]

safety:

  blocked_terms: []                 \# exemplo: ["nome de franquia", "celebridade"]

active_profile: growth

profiles:

  growth:

    purpose_pt: "Ganhar seguidores e views rápido com muitos episódios curtos e baratos."

    resolution: 360p

    episode_seconds: {min: 20, max: 45}

    cold_open: true

  monetize:

    purpose_pt: "Episódios longos e de maior qualidade para o programa de recompensas."

    resolution: 1080p

    episode_seconds: {min: 61, max: 180}

    cold_open: true

### 5.8 `config/accounts.yaml`

accounts:

  \- id: conta1

  \- id: conta2

  \- id: conta3

  \- id: conta4

  \- id: conta5

## 6\. SISTEMA DE ESTILOS (MULTI-GÊNERO)

- Um preset em `styles/` define o "look". A série escolhe um via `series.yaml -> style`.  
- Para criar um estilo novo: `studio style new <id>` copia `styles/_template.yaml`. O usuário ou o Claude preenchem os campos.  
- O motor de prompts sempre injeta `style_block` no fim de todo prompt de imagem e `video_motion_defaults` em todo prompt de vídeo.  
- Nenhuma palavra específica de um gênero pode estar hardcoded em `src/`. Tudo específico de gênero vive em `styles/` e `templates/prompts/`.

## 7\. MOTOR DE PROMPTS

### 7.1 Regras

1. Prompts de imagem e de vídeo em **inglês**; falas em **português do Brasil**, entre aspas, dentro do prompt de vídeo, sempre com o **nome de quem fala** e a **ordem** (First X says... Then Y answers...).  
2. Os `lock_block` dos personagens presentes são inseridos **literalmente**, sem paráfrase.  
3. `style_block` sempre no fim do prompt de imagem.  
4. Prompt de derivação sempre começa com: "Use the attached image as reference. Same characters, same faces, same clothes, same room and lighting." e depois `Change only: ...`.  
5. Âncora com personagens já aprovados em outra imagem: começa com "Use the attached image as reference for \[names\]: same faces, same hair, same clothes. New scene: ..." e, se o cenário for novo, inclui a frase `Completely different room from the attached image, no [old location] elements.`  
6. Prompt de vídeo começa com "Animate the attached image." e pede **uma única ação principal** por clipe.  
7. Se `gaze` estiver preenchido, incluir "looking \[gaze\]". Se vazio e o plano for close de vilania/monólogo, sugerir preencher.  
8. Modo `video_expression_only`: mesmo prompt sem falas, com a instrução "no dialogue, mouth closed" e a fala registrada em `audio/` para colocar no CapCut.  
9. Tamanho máximo sugerido do prompt: 1.200 caracteres (aviso, não erro).  
10. Saída em Markdown com bloco de código pronto para copiar, mais cabeçalho com: plano, tipo, conta sugerida, custo (em créditos), arquivo de referência a **anexar**.

### 7.2 Templates (Jinja2) — versões base

`image_anchor.j2`

{{ framing }} in {{ location.description\_en }}, {{ light }}. {% for c in characters %}{{ c.lock\_block }} {{ c.action\_en }}{{ "." if not loop.last else "" }} {% endfor %}{{ mood }}. {{ style.style\_block }}.

`image_derivative.j2`

Use the attached image as reference. Same characters, same faces, same clothes, same room and lighting. Change only: {{ framing }}, {{ action }}{% if expression %}, {{ expression }}{% endif %}. Vertical 9:16.

`video_from_image.j2`

Animate the attached image. {{ framing }}. {{ style.video\_motion\_defaults }}: {{ action }}, {{ camera }}.{% if gaze %} Looking {{ gaze }}.{% endif %}{% for line in dialogue %} {{ "First" if loop.first else "Then" }} {{ line.speaker\_name }} says in Brazilian Portuguese{% if line.delivery %} ({{ line.delivery }}){% endif %}: "{{ line.text }}"{% endfor %} {{ light }}, vertical 9:16, {{ duration\_s }} seconds.

### 7.3 Exemplo de saída esperada (plano da cozinha)

\# EP01 · P02 · video\_from\_image · body

Conta sugerida: conta1 · Custo conforme `config/production.yaml` · Anexar: assets/images/EP01\_P02\_image.jpg

Animate the attached image. Wide-medium shot, keep both characters in frame. Subtle natural

motion: water running from the tap, Manu slowly turning her head toward Duda, Duda's hands

trembling on the thermos. First Duda says softly in Brazilian Portuguese: "Manu... você tá bem?"

Then Manu answers gently, tired: "Tô, Dudu. Só cansada." Warm late-afternoon light, slight

handheld camera feel, no cuts, vertical 9:16, 8 seconds.

### 7.4 Validações do motor

- Erro: personagem citado em `characters` que não existe em `characters.yaml`.  
- Erro: `parent` inexistente ou sem imagem aprovada (para vídeo).  
- Aviso: dois personagens com mesmo `hair_color` no mesmo plano.  
- Aviso: mais de 2 falas ou fala longa (mais de \~18 palavras para 8 segundos).  
- Aviso: mais de uma ação principal na `action` (heurística: mais de duas conjunções "and"/"then").  
- Aviso: apelido usado por quem não está em `used_by`.  
- Aviso: `video_attempts` acima de `video.max_attempts`.
- Erro/aviso configurável: fala abaixo de `min_speech_fill` ou silêncio acima de
  `max_silence_s`; a mensagem informa os segundos que faltam preencher.
- Aviso: `delivery` sem `delivery_pt` (ou o inverso); erro para marcadores de tom duplo
  configurados em `pacing.delivery_forbidden_markers`.
- Aviso configurável: primeiro clipe/cold open sem `role: hook` ou sem fala iniciada antes de 2 s.
- Erro: episódio sem `cliffhanger`, exceto quando `season_finale: true`.
- Aviso: runtime estimado (vídeos mais cold open) com diferença superior a 10% da meta.

## 8\. PLANEJADOR DE CRÉDITOS E ALOCAÇÃO DE CONTAS

### 8.1 Cálculo (só vídeo gasta; fonte: config)

- Custo de imagem = `image.credits`; custo de vídeo = `video.costs[resolução_do_perfil][duração]`.
- O custo do episódio é a soma dos vídeos pendentes. O relatório mostra uma tentativa esperada
  e o pior caso de `video.max_attempts` tentativas por plano.
- Vídeos por conta por dia = calculados pelo custo da duração e resolução configurados.
- Capacidade útil por conta = `floor(daily_credits_per_account / custo_do_clipe)` menos
  `reserve_videos_per_account`; a capacidade total é a soma das contas em `config/accounts.yaml`.
- Custo desconhecido falha com mensagem em português. O cold open reutiliza um clipe e não cria
  uma nova reserva de vídeo.

> **Atualização da Fase 2:** os números ilustrativos acima são legados e não são fonte de
> verdade. O custo é lido de `video.costs[resolução do perfil][duração]`; imagem usa
> `image.credits`. A capacidade é `floor(daily_credits_per_account / custo_do_clipe)` menos
> `reserve_videos_per_account`, somada entre as contas de `config/accounts.yaml`. O relatório
> mostra uma tentativa esperada e o pior caso de `video.max_attempts`. Custo `null` bloqueia o
> cálculo e exige preenchimento em `config/production.yaml`.

### 8.2 Alocador

Entrada: lista de vídeos pendentes \+ contas. Regras:

1. Cada vídeo precisa da **imagem de origem anexada** na conta onde será gerado. O alocador lista quais arquivos precisam ser baixados/subidos para cada conta.  
2. Preferir concentrar um episódio numa única conta (menos arquivos para subir).  
3. Nenhuma conta ultrapassa a capacidade útil.  
4. Saída: tabela `conta → vídeos → créditos → arquivos de referência para anexar`.

Exemplo de relatório esperado (`studio plan revenge_republic ep01`):

Episódio ep01 · 4 vídeos pendentes · custo conforme `config/production.yaml`

conta1 · 4 vídeos (custo conforme config) / capacidade configurada

Anexar na conta1: EP01\_P03\_image.jpg, EP01\_P04\_image.jpg, EP01\_P05\_image.jpg, EP01\_P06\_image.jpg

Vídeos já aprovados: P01 (cold open), P02 (cozinha)

Duração estimada do episódio: calculada pelo lint a partir dos vídeos e do cold open

## 9\. CONVENÇÕES DE NOMES E CONSISTÊNCIA ENTRE CONTAS

- Imagens: `EP{nn}_P{nn}_image.jpg`. Vídeos: `EP{nn}_P{nn}_video.mp4`.  
- Áudio: `EP{nn}_P{nn}_voice.wav`, `EP{nn}_music.mp3`.  
- Retentativas: sufixo `_v2`, `_v3`. A aprovada é indicada em `shots.yaml` (`files:`).  
- Imagens que servem de referência a outros episódios ficam em `shared_assets/anchors/` (pasta mestre): toda conta pega as referências daqui.  
- Regra entre contas: mesmo modelo, mesma resolução (360p), mesma duração (8 s), mesmos `lock_block`, mesmo `style_block`, sempre anexando a imagem de referência.  
- `studio check-names` valida se todos os arquivos seguem o padrão e se cada plano aprovado tem arquivo correspondente.

## 10\. FLUXO DE TRABALHO POR EPISÓDIO (HUMANO \+ CLAUDE \+ STUDIO)

**Modo de ritmo** (`workflow.mode` em `config/production.yaml`):

- `images_first` (padrão recomendado): como imagem é grátis, gerar **todas** as imagens do episódio primeiro, com quantas tentativas quiser, aprovar as melhores, e só depois animar os vídeos em ordem. Vantagens: dá para conferir a consistência do conjunto antes de gastar crédito e o gasto de vídeo fica previsível.  
- `sequential`: gerar imagem, aprovar, animar, e só então ir para o próximo plano. Vantagem: se um vídeo mostrar um problema (por exemplo, rosto mudando), corrige-se o próximo prompt antes de seguir.  
- Não há diferença técnica de qualidade entre os dois modos, porque cada vídeo depende só da sua imagem de origem. A escolha é de conforto. Registrar em `docs/LESSONS.md` qual modo rendeu melhor.

Passo a passo:

1. **Roteiro** (Claude): gerar roteiro do episódio, enxugar para caber em 30 a 90 s, salvar em `script.md`.  
2. **Planos**: quebrar em 5 a 8 planos essenciais; preencher `shots.yaml` (priorizar gancho e cliffhanger). Cortar o que dá para contar com voz \+ edição.  
3. **Cold open**: escolher o momento mais impactante (ou o gancho) e configurar em `episode.yaml`.  
4. `studio prompts <serie> <ep>` gera os prompts. `studio session <serie> <ep>` gera a folha de sessão com a ordem de trabalho.  
5. **Imagens** (grátis): gerar, aprovar, salvar com o nome padrão. Atualizar o `lock_block` dos personagens novos com o que a imagem aprovada realmente mostra.  
6. `studio plan` para conferir créditos e contas.  
7. **Vídeos**: gerar (máx. 2 tentativas por plano), aprovar, salvar. Se a fala sair ruim, usar `voice_mode: post`.  
8. `studio mark <serie> <ep> <plano> approved` (ou editar o YAML).  
9. **Edição no CapCut**: montar na ordem: cold open (trim do clipe do gancho, 3 a 4 s, deixando a frase no ar) → efeito de impacto \+ transição rápida (flash branco/glitch, \~0,2 s) → cartão de texto ("Horas antes...") → clipes do episódio em ordem → cliffhanger. Legenda queimada em toda fala, música de tensão, efeitos sonoros nos ganchos. Imagens paradas com zoom leve para planos de preenchimento.  
10. `studio caption` gera legenda, descrição e hashtags. Lembrete: rotular como conteúdo de IA se a plataforma exigir e conferir regras atuais de monetização.  
11. Postar (TikTok/Shorts/Reels) e registrar métricas em `episode.yaml`.  
12. Registrar em `docs/LESSONS.md` o que funcionou e o que falhou.

## 11\. CLI (COMANDOS)

Framework: Typer. Entry point: `studio`.

studio init                          \# cria estrutura base e config padrão

studio series new \<id\>               \# cria série a partir dos templates

studio series list                   \# lista séries e status

studio style new \<id\>                \# cria preset de estilo

studio style list

studio episode new \<series\> \<nn\>     \# cria episódio (pastas \+ templates)

studio validate \<series\> \[ep\]        \# valida YAML, personagens, parents, avisos

studio brief new \<series\>             \# cria brief_pt.md para autoria dentro do projeto

studio brief check \<series\>           \# avisa seções vazias do brief

studio bible check \<series\>           \# valida a bíblia da série e a grade de episódios

studio scaffold \<series\> \<episode\>    \# cria episódio com schema completo de shots

studio lint \<series\> \<episode\>        \# valida ritmo, beats e espelhos _pt

studio prompts \<series\> \<ep\>         \# gera prompts de todos os planos pendentes

studio prompts \<series\> \<ep\> \--shot P03

studio prompts \<series\> \<ep\> \--phase images|videos

studio session \<series\> \<ep\> \[--account conta1\]   \# folha de sessão: ordem, anexos e prompts

studio pack \<series\> \<ep\>       \# pacote simples com roteiro, imagens e vídeos

studio next \<series\> \<ep\>            \# diz qual é a próxima ação e mostra o prompt pronto

studio plan \<series\> \<ep\>            \# créditos de vídeo e divisão por conta

studio plan-day [--episodes N]        \# capacidade diária do perfil ativo

studio mark \<series\> \<ep\> \<shot\> \<status\>

studio attempt \<series\> \<ep\> \<shot\>  \# registra mais uma tentativa de vídeo

studio status \<series\> \[ep\]          \# painel de status por plano e por episódio

studio check-names \<series\> \<ep\>     \# valida nomes e arquivos

studio caption \<series\> \<ep\>         \# legenda \+ hashtags do post

studio credits                       \# mostra parâmetros atuais de config

Todos os comandos devem funcionar offline, imprimir saída legível no terminal e, quando gerarem arquivos, escrever em pastas previsíveis. `studio session` e `studio next` são o coração do uso diário: o criador roda um deles e só copia e cola.

## 12\. STACK TÉCNICA

- Python 3.11+  
- Typer (CLI), Pydantic v2 (modelos), PyYAML (dados), Jinja2 (templates de prompt), Rich (tabelas no terminal), pytest (testes).  
- Sem banco de dados, sem servidor, sem chamadas de rede.  
- Formatação: ruff. Tipagem: type hints em todo o código.  
- Windows first: caminhos com `pathlib`, sem dependência de shell Unix.

## 13\. ROADMAP EM FASES

**Fase 1 — Núcleo (MVP)**

- Estrutura de pastas e `studio init`.  
- Modelos Pydantic e `loader` para série, personagens (com apelidos), locais, estilo, episódio (com cold open), shots.  
- `studio series new`, `studio episode new`, `studio validate`.  
- Motor de prompts (anchor, derivative, video, expression-only) com validações da seção 7.4.  
- `studio prompts`.  
- Critério de aceite: com a série de exemplo (seção 14), `studio prompts revenge_republic ep01` gera prompts equivalentes aos exemplos da seção 7.3.

**Fase 1.5 — Autoria dentro do projeto**

- Modo Autoria documentado em `AGENTS.md` e `docs/AUTHORING_GUIDE.md`: o agente transforma brief
  ou roteiro em português em YAML/Markdown versionável, sem depender de outra IA ou ferramenta.
- `studio brief new/check` e `studio scaffold` para iniciar a autoria offline.
- Espelhos `_pt` opcionais nos modelos, leitura em português nos prompts e avisos de consistência
  EN/PT; `negative_hints` e `character_rules` entram nos prompts.
- `studio lint` com pacing configurável, voice-over, beats e silêncios intencionais; chamado por
  `studio validate`. A geração de mídia continua manual.
- Esta fase não inclui créditos, alocação, sessão, status ou publicação.

**Fase 1.6 — Direção de cena para geração econômica**

- Cada vídeo recebe contexto, estado inicial, timeline com ações visíveis, estado final, som e
  restrições de continuidade, todos com espelho EN/PT.
- Os templates transformam a sequência em instruções ordenadas para o Flow: setup → starting
  state → timed direction → end state → sound → do not.
- O lint avisa quando a direção está incompleta ou sem espelho bilíngue. Esta fase não muda
  créditos, contas, sessão ou publicação.

**Fase 1.7 — Endurecimento de ritmo e fala**

- Falas e voice-over aceitam `delivery`/`delivery_pt`; o prompt usa delivery da fala, depois o
  `default_delivery`/`default_delivery_pt` do personagem, e nunca usa `voice_notes`.
- Marcadores de tom duplo, preenchimento baixo e silêncio excessivo têm regras e severidades
  configuráveis em `config/production.yaml`, com compatibilidade padrão em `warning`.
- O lint calcula runtime com cold open, valida o gancho antes de 2 s, `cliffhanger` e
  `season_finale`, e exibe tabela Rich por plano com resumo do episódio.
- A fixture `revenge_republic` permanece pausada, funcional e não publicável; a série real ainda
  não existe. Esta fase não inclui créditos, sessão, métricas ou publicação.

**Fase 1.8 — Perfis de produção**

- `active_profile`, `profiles.growth` e `profiles.monetize` definem objetivo, resolução, faixa de
  duração e cold open; episódio sobrescreve série, que sobrescreve o perfil ativo.
- Custos ficam em `video.costs` por resolução. `null` bloqueia qualquer cálculo de custo e custos
  sem conferência recente geram aviso no `studio validate`.
- `studio profile show/set` consulta e altera o perfil ativo; ao selecionar `monetize`, mostra
  `config/goals.yaml` quando o arquivo existir.
- O lint valida faixa de runtime, resolução do plano e exibe o perfil nos comandos de produção.
  Esta fase não inclui sessão, métricas ou publicação.

**Fase 1.9 — Preset de estilo e personagem estranho**

- `styles/weird_toon.yaml` define caricatura 3D estranha, não realista, com todos os espelhos
  `_pt`, proporções exageradas e uma silhueta constante por personagem.
- Personagens aceitam `silhouette_hook`, `silhouette_hook_pt` e `palette`; o lint avisa ausência,
  divergência do `lock_block` e colisões de silhueta/cabelo no mesmo plano.
- `safety.blocked_terms` bloqueia termos configuráveis em lock blocks, estilo e ação. É uma
  heurística de segurança, não garantia de ausência de IP ou semelhança com pessoa real. Esta fase
  não inclui créditos, sessão ou métricas.

**Fase 1.10 — Bíblia de série verificável**

- `templates/series/bible.md` define cabeçalhos obrigatórios e instruções sem inventar a premissa,
  os personagens ou o enredo da série nova.
- `studio bible check` valida tamanho mínimo configurável, placeholders, grade de episódios e
  cliffhangers; repetições consecutivas geram aviso. `validate` e `scaffold` tratam o resultado
  como aviso em `idea`/`planning` e como erro bloqueante em `in_production`.
- `studio brief new` segue as perguntas da bíblia e acrescenta a imagem mais estranha e a pergunta
  do fim do episódio 1. A fixture pausada permanece aceita. Esta fase não inclui sessão, métricas
  ou publicação.

**Fase 2 — Créditos, contas e sessão**

- `credits.py`, `allocator.py`, `studio plan` (só vídeo gasta).  
- `session.py`, `studio session`, `studio next`.  
- Testes com casos de estouro de capacidade e de tentativas de vídeo.

**Estado da Fase 2:** concluída. O Studio calcula orçamento esperado e pior caso, aloca vídeos
por conta/dia respeitando reservas, gera `plan-day`, cria folhas de sessão offline e faz `next`
respeitar a reserva. Não inclui métricas nem publicação.

**Fase 3 — Pacote simples**

- `studio pack <series> <episode>` gera `pacote/0_PERSONAGENS.md`, `pacote/1_ROTEIRO.md`,
  `pacote/2_IMAGENS.md` e `pacote/3_VIDEOS.md`, com linguagem natural, prompts prontos e ordem
  de produção. O primeiro documento prepara rosto e corpo dos personagens que aparecem no episódio.
- A aprovação no pacote depende somente de arquivos com o nome esperado dentro de
  `assets/images/` e `assets/videos/`; `status` no YAML e arquivos em Downloads são ignorados.
- Imagens são ordenadas topologicamente; vídeos seguem a ordem narrativa. O pacote não inclui
  contas, créditos ou a sessão detalhada. Custo `null` não bloqueia o pacote.
- `validate` com ERROR impede a geração. Reexecutar sobrescreve somente `pacote/` e nunca move,
  renomeia ou apaga assets. Esta fase permanece offline e não implementa métricas ou publicação.

**Extensão da Fase 3 — consistência de personagens e áudio**

- Personagens falantes aceitam `voice_profile`/`voice_profile_pt`; os prompts listam somente as
  vozes que falam no plano e repetem `audio_style`/`audio_style_pt` do preset.
- A pasta `series/<id>/assets/characters/` aprova rosto e corpo apenas por arquivo de imagem com
  nome esperado. Imagens de cena podem anexar esses assets; vídeos anexam somente a imagem da
  cena. `voice_notes` permanece nota de autoria e nunca entra no prompt.

**Fase 4 — Status e arquivos**

- `studio mark`, `studio attempt`, `studio status`, `studio check-names`.  
- Painel de status por episódio e por plano, com duração estimada.

**Fase 5 — Publicação**

- `studio caption` (legenda, hashtags, sugestão de capa, lembretes de política).  
- Registro de métricas em `episode.yaml`.

**Fase 6 — Multi-estilo e conveniência**

- Presets `fruit_humans` e outro à escolha completos.  
- `studio style new` interativo.  
- Opcional: painel web simples (Streamlit) lendo os mesmos arquivos.  
- Opcional: exportar "pacote de sessão" por conta (prompts \+ lista de referências).

## 14\. SÉRIE DE EXEMPLO (DADOS INICIAIS PARA `series/revenge_republic/`)

Serve de teste real e de fixture do MVP.

- **Série:** drama de vingança e college, 10 episódios, público 18-24, estilo `realistic_drama`.  
- **Personagens:** Manu (protagonista), Duda/Eduarda (vilã; a Manu a chama de **Dudu**, os demais de Duda), Théo (aliado), Rafa (namorado, cabelo escuro cacheado para não se confundir com Duda).  
- **Lock blocks oficiais (Manu e Duda foram validados em imagem e vídeo):**  
  - Manu: `Manu, 20-year-old Brazilian woman, brown skin, almond eyes, dark brown hair in a neat bun, white t-shirt and beige cardigan`  
  - Duda: `Duda, 20-year-old Brazilian woman, straight blonde hair, big eyes, flawless makeup, pastel pink V-neck knit top, two thin gold necklaces, black pants`  
  - Théo (rascunho, **ajustar** com o que a imagem aprovada da sala mostra): `Théo, 21-year-old Brazilian man, messy dark hair, rectangular glasses, gray hoodie`  
  - Rafa (rascunho, **ajustar** com o que a imagem aprovada da sala mostra): `Rafa, 21-year-old Brazilian man, dark curly hair, navy polo shirt, athletic build`  
- **Locais:** cozinha da república, sala da república, corredor da república (noite), corredor da faculdade (noite), quarto da Duda (noite).  
- **Episódio 1: plano de produção com status real:**

| Plano | Tipo | Conteúdo | Status |
| :---- | :---- | :---- | :---- |
| P01i | derived\_image | close da Duda, sorriso frio (a partir da cozinha) | aprovada |
| P01 | video\_from\_image | close da Duda com a fala do gancho, 8 s | **aprovado** (vira o cold open, 0 a 3,0 s) |
| P02i | anchor\_image | cozinha, Manu \+ Duda | aprovada |
| P02 | video\_from\_image | cozinha, "Manu... você tá bem?" / "Tô, Dudu. Só cansada." | **aprovado** |
| P03i | anchor\_image | sala com Rafa, Duda, Théo e Manu com o presente | aprovada |
| P03 | video\_from\_image | sala, Rafa irritado, Duda defensiva, Théo desconfiado | **pendente** (custo conforme config) |
| P04i / P04 | derived\_image \+ vídeo | Duda recusa o presente (momento mais forte) | pendente |
| P05i / P05 | derived\_image \+ vídeo | Théo vê o alívio de Duda | pendente |
| P06i / P06 | derived\_image \+ vídeo | Duda sozinha na cama ao telefone (cliffhanger) | pendente |
| — | (cortado) | Théo confronta Rafa no corredor da faculdade | cortado para economizar crédito; contar com fala no CapCut |

- Créditos restantes do episódio: calculados somente com custos conhecidos em `config/production.yaml`.
- Duração estimada: calculada pelo lint e comparada à faixa do perfil ativo.
- Fonte de referência de estrutura: 4 episódios de um drama chinês de "amiga falsa" (guardar em `references/`), usados para extrair ritmo e ganchos, não para copiar a história.

## 15\. AGENTS.md (COPIAR PARA A RAIZ DO REPOSITÓRIO)

\# AGENTS.md — Novelinha Studio

\#\# Contexto

Este repositório é um estúdio de produção de novelinhas verticais feitas por IA. A CLI \`studio\` organiza séries, monta prompts, planeja créditos de vídeo, gera folhas de sessão e controla status. Ela NÃO gera imagem/vídeo e NÃO automatiza contas do Google Flow ou de qualquer outra ferramenta.

Leia \`docs/SPEC.md\` antes de qualquer tarefa.

\#\# Regras de trabalho

1\. Implemente apenas a fase do roadmap que o usuário pediu. Não adiante fases.

2\. Python 3.11+, Typer, Pydantic v2, PyYAML, Jinja2, Rich, pytest, ruff. Não adicione dependências sem justificar.

3\. Escreva testes para toda lógica nova (prompts, créditos, alocação, sessão, nomes). Rode \`pytest\` e \`ruff check\` antes de dizer que terminou.

4\. Nada específico de gênero (drama, frutas etc.) pode estar hardcoded em \`src/\`. Tudo isso vive em \`styles/\` e \`templates/\`.

5\. Valores de custo, créditos, resolução, duração, tentativas e número de contas vêm de \`config/production.yaml\`. Nunca hardcode. Lembre: imagem custa 0 créditos, só vídeo gasta.

6\. Os \`lock\_block\` dos personagens são inseridos literalmente nos prompts. Nunca parafraseie.

7\. Nunca grave senhas, e-mails reais ou tokens. Contas são só apelidos.

8\. Não faça chamadas de rede. Nada de scraping, automação de navegador ou uso de APIs de terceiros.

9\. Windows first: use \`pathlib\`, evite comandos Unix.

10\. Mensagens de commit em inglês, pequenas e descritivas. Documentação para o usuário em português do Brasil.

11\. Se algo na spec estiver ambíguo, escolha a opção mais simples, registre a decisão em \`docs/LESSONS.md\` e siga; pergunte só se a dúvida bloquear.

\#\# Definição de pronto

\- Comando implementado e documentado no README.

\- Testes passando.

\- Exemplo funcionando com \`series/revenge\_republic\`.

\- Sem regressão nas validações da seção 7.4 da SPEC.

## 16\. ESTADO ATUAL DO PROJETO (ATUALIZAR A CADA FASE)

- Fase concluída: **Fase 3 — Pacote simples**. A autoria pode terminar com `validate` → `lint` →
  `pack`; o resultado é uma pasta pequena para copiar prompts no Flow. Aprovação é verificada no
  filesystem de assets, sem depender do status do YAML. As fases de status, métricas e publicação
  continuam fora desta implementação.

- Fase concluída: **Fase 2 — Créditos, contas e sessão**. Créditos vêm exclusivamente do config;
  custos `null` bloqueiam o cálculo, a alocação cobre o pior caso de tentativas e a sessão é
  manual/offline. Métricas e publicação permanecem fora do escopo.

- Ferramenta: Google Flow, 5 contas gratuitas, 50 créditos/dia cada. **Imagem é grátis; custos
  de vídeo são lidos por resolução em `config/production.yaml`**. Custos `null` permanecem sem
  estimativa até conferência humana no Flow.
- Estratégia de consistência aprovada e validada em produção: sem fichas de personagem nem cenários vazios; cada imagem já sai com os personagens dentro do cenário; novas imagens usam a anterior como referência; blocos de personagem copiados literalmente; o `lock_block` acompanha o que a imagem aprovada realmente mostra.  
- Formato de abertura aprovado: **cold open** de \~3 s com o momento de maior impacto, transição e depois o episódio normal.  
- Ritmo de produção: a definir na prática (`images_first` recomendado; `sequential` é a alternativa). Registrar em `LESSONS.md` qual funciona melhor.  
- Episódio 1 (série `revenge_republic`): cold open (close da Duda) e cozinha já em vídeo e aprovados; imagem da sala aprovada, vídeo pendente; faltam recusa do presente, Théo e cliffhanger (ver tabela da seção 14).  
- Apelido: Manu chama Duda de "Dudu".  
- Qualidade: o perfil `growth` usa 360p e o perfil `monetize` usa 1080p; custos de 1080p ainda
  precisam ser conferidos na interface do Flow.
- A série `revenge_republic` é somente fixture funcional de testes, está com `status: paused` e
  não será publicada. A série oficial `amiga_de_mentira` está em planejamento com o episódio 1
  autorado.
- O estilo da série oficial é estilizado e estranho: caricatura 3D com proporções exageradas,
  não realista.
- A estratégia aprovada tem duas etapas: CRESCIMENTO com vídeos curtos e baratos até a
  qualificação; MONETIZAÇÃO com episódios acima de 60 s e resolução 1080p.
- Perfil ativo: `growth`, com episódios de 20 a 45 segundos e cold open configurado.
- Fase de desenvolvimento do Studio: **Fases 1.9, 1.10 e extensão do pacote concluídas**. O
  Studio tem preset `weird_toon`, lint de silhueta/termos bloqueados, bíblia verificável, perfis,
  ritmo, pacote de personagens e perfis de voz. A série oficial `amiga_de_mentira` foi criada
  em planejamento com o episódio 1 autorado; métricas e publicação continuam fora do escopo.

## 17\. LIÇÕES INICIAIS (COPIAR PARA `docs/LESSONS.md`)

- Imagens derivadas a partir de uma âncora mantêm rosto, cabelo e figurino muito bem quando o prompt começa com "Use the attached image as reference. Same characters, same faces, same clothes...".  
- Nova imagem com personagens já aprovados \+ personagens novos funcionou: os rostos antigos se mantiveram e os novos ficaram coerentes.  
- Close de rosto animado ficou consistente por 8 s, mas o olhar ficou direto na câmera. Para monólogos "para si mesmo", pedir olhar fora da câmera (campo `gaze`).  
- Fala com duas pessoas em 8 s funcionou; manter falas curtas e nomear quem fala e em que ordem.  
- O modelo pode alterar nomes/apelidos ditos nas falas. Aceitar a variação se combinar com a história (ex.: "Dudu") e registrar como apelido oficial.  
- Imagem é grátis: iterar em imagem e gastar vídeo só depois de aprovar.

## 18\. IDEIAS FUTURAS (NÃO IMPLEMENTAR SEM PEDIDO)

- Biblioteca de ganchos e cold opens testados por gênero, com métricas reais de retenção.  
- Análise de referências: colar roteiro/prints de uma série e o Studio extrair beat sheet e ritmo (com auxílio do Claude, fora do código).  
- Calendário de postagem por série.  
- Relatório de métricas por episódio (retenção, % assistido, comentários pedindo parte 2\) para decidir investimento em ferramentas pagas.
