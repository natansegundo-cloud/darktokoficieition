# Guia de autoria — Novelinha Studio

Este manual define como transformar uma ideia em arquivos de produção. A autoria acontece no
repositório: o agente lê o brief em português, escreve os YAML/Markdown e depois roda a CLI
offline. O Google Flow continua sendo usado manualmente apenas para gerar a mídia.

## Fluxo

1. Escrever um brief em `series/<id>/brief_pt.md` com `studio brief new <id>`.
2. Preencher `series/<id>/bible.md` seguindo `templates/series/bible.md` e rodar
   `studio bible check <id>`.
3. Transformar a premissa em `series.yaml`: título, público, estilo, logline e arco da temporada.
4. Criar os personagens com lock blocks visuais, versões e traduções.
5. Criar os locais com descrição filmável em inglês e espelho em português.
6. Escolher ou criar um preset de estilo contemporâneo, sem inventar época.
7. Escrever o roteiro do episódio em `script.md`, começando as cenas no meio da ação.
8. Quebrar o roteiro em `shots.yaml`, dando a cada plano um beat concreto.
9. Rodar `studio validate <serie> <episódio>` e `studio lint <serie> <episódio>`.
10. Corrigir erros, revisar avisos importantes e só então gerar prompts para o Flow.

## Campos YAML

Todo campo em inglês usado para montar prompt possui um espelho `_pt`. Exemplos:

```yaml
# personagem
lock_block: "Manu, 20-year-old Brazilian woman, brown skin, dark hair in a bun, white t-shirt"
lock_block_pt: "Manu, mulher brasileira de 20 anos, pele marrom, cabelo escuro preso, camiseta branca"

# local
description_en: "small student house kitchen, worn wooden counter"
description_pt: "cozinha pequena de uma casa estudantil, bancada de madeira gasta"
default_light: "late afternoon natural light"
default_light_pt: "luz natural do fim da tarde"

# plano
framing: "medium close-up"
framing_pt: "plano médio fechado"
action: "Duda pushes the gift away"
action_pt: "Duda empurra o presente"
camera: "slow push-in"
camera_pt: "aproximação lenta da câmera"
mood: "tense social gathering"
mood_pt: "encontro social tenso"
beat_pt: "Duda impede que o presente seja aberto"
```

Ao alterar um campo em inglês, altere o espelho português na mesma mudança. Para um
`lock_block`, incremente `lock_version` e registre a decisão em `docs/LESSONS.md`. O lock block
tem uma linha, descreve apenas o que a câmera vê: idade, origem, pele, cabelo, roupa fixa e um
elemento marcante. Não inclui sentimentos nem época.

Campos de estilo seguem a mesma regra: `style_block_pt`, `negative_hints_pt`,
`camera_defaults_pt`, `video_motion_defaults_pt` e `character_rules_pt`.

### `series.yaml`

`id` identifica a pasta; `title` é o nome público; `genre` e `audience` orientam o recorte;
`language` normalmente é `pt-BR`; `aspect_ratio` é `9:16`; `style` aponta para `styles/<id>.yaml`;
`profile` é opcional e sobrescreve o perfil ativo da produção;
`episodes_planned` e `episode_target_seconds` definem o tamanho; `logline`, `synopsis` e
`season_hook` guardam a história; `status` pode ser `idea`, `planning`, `in_production`, `paused`
ou `released`.

```yaml
id: revenge_republic
title: "A República da Vingança"
style: realistic_drama
episodes_planned: 10
episode_target_seconds: [30, 90]
status: planning
```

### `characters.yaml`

Cada personagem tem `id`, `name`, `role`, `age`, `lock_version`, `lock_block` e `lock_block_pt`.
Use `nicknames` com `used_by` para apelidos controlados; `signature_element` deve aparecer no
lock; `hair_color` ajuda a detectar confusão no mesmo plano. `silhouette_hook` e
`silhouette_hook_pt` registram a feature absurda constante; `palette` registra a paleta exclusiva
do personagem. `default_delivery` e `default_delivery_pt` definem um único tom de voz para falas
que não especificarem delivery. `voice_notes`, `bio_pt`, `arc_pt` e `approved_reference`
completam a ficha; `voice_notes` é nota de autoria e nunca entra no prompt.
Para cada personagem falante, preencha `voice_profile` e `voice_profile_pt` com idade aparente,
gênero, registro, timbre, ritmo e sotaque. O perfil deve ser um único som consistente; o prompt
de vídeo usa o perfil apenas quando o personagem fala naquele plano. O preset também define
`audio_style`/`audio_style_pt` para manter diálogo e ambiente coerentes.

## Personagem estranho que se mantém consistente

Para cada personagem, escolha uma única feature absurda e geométrica: um corte de cabelo
impossível, nariz triangular, queixo muito largo ou sobrancelhas angulares. Registre essa feature
em `silhouette_hook`, repita-a literalmente no `lock_block` e preencha seu espelho
`silhouette_hook_pt`. O lint avisa quando a feature não aparece no lock.

Use uma paleta de cor própria para cada personagem, principalmente na roupa e em um acessório
visível. Mantenha constantes as proporções entre cabeça e corpo, o tamanho da feature e o desenho
da silhueta em todos os planos. O estilo 3D estilizado é mais fácil de manter que o realista em
360p porque a forma exagerada continua legível mesmo quando a imagem perde detalhe fino.

O lock_block segue a imagem aprovada: depois de aprovar uma imagem, ajuste o lock para descrever
exatamente cabelo, roupa, proporções e feature que a câmera realmente mostra, incremente
`lock_version` e registre a decisão em `docs/LESSONS.md`.

Não use personagens de IP existente, semelhança com pessoas reais ou celebridades, nomes de
franquias ou logotipos. `safety.blocked_terms` é uma rede de segurança configurável, não uma
garantia de detecção completa.

### `locations.yaml`

Use `id`, `name`, `description_en`, `description_pt`, `default_light` e `default_light_pt`.
A descrição deve conter objetos e posições que a câmera pode mostrar, não uma atmosfera abstrata.

### `styles/<id>.yaml`

Preencha `id`, `name`, `style_block`/`style_block_pt`, `negative_hints`/`negative_hints_pt`,
`camera_defaults`/`camera_defaults_pt`, `video_motion_defaults`/`video_motion_defaults_pt` e
`character_rules`/`character_rules_pt`. `notes` registra limites práticos do preset.

### `episode.yaml`

Use `id`, `title`, `number`, `target_seconds`, `status`, `cliffhanger`, `key_prop`, `profile` e
`notes`. `profile` sobrescreve o perfil da série; a série sobrescreve `active_profile`.
Em `cold_open`, marque `enabled`, `source_shot`, `trim_start_s`, `trim_end_s`, `transition` e
`title_card_pt`. O cold open é reaproveitamento de um clipe, não um novo gasto de vídeo.

### `shots.yaml`

Cada plano precisa de `id`, `order`, `kind`, `role`, `location`, `characters`, `framing`/`framing_pt`,
ação filmável, `beat_pt`, `parent` quando deriva de imagem, `dialogue_pt` ou `voice_over_pt` em
vídeos, `duration_s`, `status` e `files` quando houver mídia. Cada fala pode ter `delivery` e
`delivery_pt`; se faltar, o Studio tenta o default do personagem. Use `intentional_silence` somente
para um golpe narrativo deliberado. `account` e `video_attempts` registram produção manual.

```yaml
dialogue_pt:
  - speaker: duda
    text: "A prova ainda está comigo."
    delivery: "low, cold, controlled"
    delivery_pt: "baixa, fria, controlada"
```

Para vídeos, a direção deve ser concreta nos campos `setup`/`setup_pt`,
`start_state`/`start_state_pt`, `timeline`/`timeline_pt`, `end_state`/`end_state_pt`,
`sound`/`sound_pt` e `must_not`/`must_not_pt`. Cada item de `timeline` tem `at_s`, `action` e
`action_pt`.

```yaml
setup: "The wrapped gift is centered between Rafa and Duda."
setup_pt: "O presente embrulhado fica entre Rafa e Duda."
start_state: "Rafa has one hand near the gift; Duda's hands are on her lap."
start_state_pt: "Rafa mantém uma mão perto do presente; Duda está com as mãos no colo."
timeline:
  - at_s: "0-2s"
    action: "Rafa slides the gift toward Duda."
    action_pt: "Rafa desliza o presente na direção de Duda."
end_state: "The gift remains closed and Duda is one step away from it."
end_state_pt: "O presente permanece fechado e Duda está um passo distante dele."
sound: "Paper friction and one short question."
sound_pt: "Ruído de papel e uma pergunta curta."
must_not: "Do not open the gift or cut away."
must_not_pt: "Não abrir o presente nem cortar para outro plano."
```

A sequência deve caber na duração do clipe e seguir o formato estado inicial → ação → reação →
estado final. Não coloque quatro acontecimentos independentes em oito segundos. O agente deve
escrever tanto a direção em inglês, usada no Flow, quanto o espelho em português, usado para
revisão humana.

## Estilo e ações

O preset ativo define a linguagem visual. Para a série nova, use `weird_toon`: caricatura 3D
estranha, não realista, com proporções exageradas e expressões legíveis. Nunca invente uma época,
como “1990s”, sem que a série peça.
Escreva apenas ações filmáveis: mão abrindo uma gaveta, mensagem aparecendo no celular, objeto
sendo escondido, mudança visível de expressão ou fala. Não descreva sentimento interno sem uma
ação ou fala que o revele.

## Ritmo obrigatório

- Todo clipe tem `dialogue_pt` ou `voice_over_pt`; silêncio é um golpe explícito em
  `intentional_silence` e ocorre no máximo uma vez por episódio.
- Use no máximo duas linhas faladas por clipe, com no máximo 15 palavras por linha.
- `delivery` deve ter um único tom; não use alternativas com `or`, `when` ou `;`. Sempre preencha
  seu espelho `delivery_pt`.
- Cada fala deve trazer conflito ou informação nova, não apenas repetir uma emoção.
- Todo plano tem `beat_pt`; dois planos consecutivos não repetem o mesmo beat.
- Comece cada cena já no meio da ação; não gaste o clipe com personagem entrando ou saindo.
- Prefira elementos visíveis como mensagens, prints, stories, áudios e objetos.
- Use um cold open de aproximadamente três segundos com o maior impacto.
- Termine o episódio em gancho. A revelação principal acontece dentro do último episódio.
- O primeiro clipe ou cold open deve ser `role: hook` e iniciar a fala antes de 2 segundos.
- O episódio precisa de `cliffhanger`, exceto quando `season_finale: true`.
- Revise o runtime estimado e mantenha a diferença em até 10% da meta.

## Checklist de entrega

- [ ] Brief preenchido e conferido com `studio brief check`.
- [ ] Série, personagens, locais e estilo têm os espelhos `_pt`.
- [ ] Cada lock block descreve somente elementos visíveis e está versionado.
- [ ] Cada personagem tem uma `silhouette_hook` absurda, constante e presente no `lock_block`.
- [ ] Cada personagem tem uma paleta de roupa distinta e proporções fixas.
- [ ] Cada plano tem beat novo e ação filmável.
- [ ] Cada vídeo tem contexto, estado inicial, timeline, estado final e restrições.
- [ ] Cada vídeo tem fala/voz off ou silêncio intencional permitido.
- [ ] Cada fala tem delivery/delivery_pt coerentes, ou usa um default único do personagem.
- [ ] `studio validate` não tem ERROR.
- [ ] `studio lint` não tem ERROR; avisos foram revisados.
- [ ] O roteiro começa as cenas no meio da ação e termina em gancho.

## Gancho e retenção

- [ ] Os primeiros 2 segundos têm estranheza visual e fala ou voz off.
- [ ] A cena começa no meio da ação, sem entrada ou preparação vazia.
- [ ] Cada episódio termina com um cliffhanger preenchido.
- [ ] Existe um bordão ou motivo recorrente reconhecível.
- [ ] A temporada mantém uma pergunta em aberto até a revelação final.
- [ ] `studio bible check <serie>` passa sem ERROR antes da produção.

## Brief para copiar

```markdown
# Brief da série

Use `studio brief new <serie>` para gerar as perguntas da bíblia na ordem correta, incluindo a
imagem mais estranha e memorável e a pergunta do espectador no fim do episódio 1.
```
