# Novelinha Studio

CLI offline para organizar a produção de novelinhas verticais feitas manualmente no Google Flow.
O Studio monta prompts, valida arquivos e mantém o estado da produção; ele não gera mídia,
não chama APIs e não automatiza contas.

O áudio é gerado pelo próprio Google Flow dentro do vídeo. O projeto não usa uma etapa de
áudio externo no fluxo padrão.

## Começo rápido

```text
python -m pip install -e ".[dev]"
studio init
studio validate revenge_republic ep01
studio lint revenge_republic ep01
studio prompts revenge_republic ep01
studio board revenge_republic ep01
studio next revenge_republic ep01
studio plan revenge_republic ep01
studio plan-day --episodes 1
studio session revenge_republic ep01 --account conta1
studio pack revenge_republic ep01
```

O projeto usa a pasta atual como raiz. Dados ficam em YAML/Markdown e mídia fica fora do Git.
Consulte `ofcNOVELINHA_STUDIO_SPEC.md` para a especificação completa.

## Perfis e custos

O perfil ativo vem de `active_profile` em `config/production.yaml`. Use `studio profile show`
para consultar objetivo, resolução, faixa de duração, custos conhecidos e data de conferência.
O arquivo de configuração é a única fonte de verdade para custos; valores `null` são
desconhecidos e bloqueiam comandos que precisem calcular custo.

```text
studio profile show
studio profile set growth
studio profile set monetize
```

O perfil `growth` é destinado a vídeos curtos e baratos; `monetize` usa episódios longos e
resolução 1080p. Antes de monetizar, o comando mostra `config/goals.yaml` se esse arquivo existir.

## Autoria e ritmo

O agente pode trabalhar dentro do projeto a partir de um brief em português:

```text
studio brief new revenge_republic
studio brief check revenge_republic
studio bible check revenge_republic
studio scaffold revenge_republic ep02
studio validate revenge_republic ep01
studio lint revenge_republic ep01
```

`studio lint` calcula a fala estimada, o preenchimento de cada clipe, o silêncio restante,
beats repetidos e traduções `_pt` ausentes. Consulte `docs/AUTHORING_GUIDE.md` antes de criar
uma série ou episódio. A geração de mídia continua manual e offline.

O preset `styles/weird_toon.yaml` é a referência para personagens 3D caricaturais, estranhos e
memoráveis. O lint verifica a silhueta constante, colisões de cabelo/silhueta no mesmo plano e
os termos configurados em `safety.blocked_terms`. Essa lista é uma rede de segurança heurística,
não uma garantia contra IP ou semelhança com pessoas reais.

`studio bible check` verifica se a bíblia tem todas as seções obrigatórias, conteúdo suficiente,
nenhum placeholder e uma grade completa de episódios com cliffhangers. Em séries `idea` ou
`planning`, `validate` e `scaffold` exibem esses problemas como avisos; em `in_production`, eles
bloqueiam a operação.

O lint também valida o tom de voz: `delivery` em inglês e `delivery_pt` em português. A fala
usa seu próprio delivery; na ausência dele, usa o `default_delivery` do personagem. `voice_notes`
fica apenas como nota de autoria e nunca entra no prompt. A tabela Rich mostra o runtime estimado,
comparado à meta do episódio, e o comando retorna erro quando a severidade configurada exigir.
Cada personagem que fala deve ter `voice_profile` e `voice_profile_pt`. O prompt de vídeo lista
somente as vozes dos personagens falantes e aplica o `audio_style` do preset.

Para vídeos, os prompts agora carregam direção por tempo: contexto, estado inicial, ações em
ordem, estado final, som e restrições. Escreva o que a câmera deve ver, não apenas a intenção
dramática.

`series/revenge_republic` é uma fixture funcional de testes, está pausada e não é material de
publicação. A série oficial `amiga_de_mentira` está em planejamento com o episódio 1 autorado.
A estratégia aprovada separa CRESCIMENTO, com vídeos curtos e baratos, de MONETIZAÇÃO, com
episódios acima de 60 segundos em 1080p.

## Fase 1.7 — Endurecimento de ritmo e fala

Esta fase adiciona delivery sem tons contraditórios, enforcement configurável para preenchimento
e silêncio, validação de gancho e cliffhanger, runtime estimado com cold open e cobertura completa
de testes. Créditos, sessão, métricas e publicação continuam fora do escopo.

## Fase 1.8 — Perfis de produção

O episódio pode sobrescrever o perfil da série, que sobrescreve `active_profile`. O lint compara
o runtime com a faixa do perfil e avisa quando a resolução declarada do plano diverge. Custos
desatualizados geram aviso no `validate`; a configuração nunca inventa custo desconhecido.

## Fase 1.9 — Preset de estilo e personagem estranho

Foi adicionado o preset `weird_toon`, com todos os espelhos `_pt`, além de `silhouette_hook`,
`palette` e regras de consistência visual. A direção exige caricatura 3D não realista, sem IP,
celebridades ou pessoas reais. Créditos, sessão e métricas continuam fora do escopo.

## Fase 1.10 — Bíblia de série verificável

`templates/series/bible.md` define a estrutura da bíblia sem inventar premissa, personagens ou
enredo. `studio bible check` valida seções, placeholders, grade de episódios e cliffhangers.
`studio brief new` gera perguntas nessa mesma ordem e acrescenta a imagem mais estranha da série
e a pergunta que fica no fim do episódio 1. Sessão, métricas e publicação continuam fora do
escopo.

## Fase 2 — Créditos, contas e sessão

O Studio calcula custos somente para vídeos, usando `video.costs` da resolução do perfil ativo;
imagens usam `image.credits`. `studio plan` mostra o caso esperado, o pior caso de tentativas,
contas sugeridas, dias e saldo. `studio plan-day` estima episódios e vídeos por dia.

```text
studio plan revenge_republic ep01
studio plan-day --episodes 1
studio session revenge_republic ep01 [--account conta1]
studio next revenge_republic ep01
```

`studio session` gera uma folha Markdown offline em `episodes/<ep>/prompts/session_sheet.md`, com
imagens primeiro, anexos, prompts, destino, conta e custo. Contas são apenas apelidos: o Studio
nunca faz login nem automatiza o Flow. Custos `null` bloqueiam cálculos; custos antigos geram
aviso. O aviso de termos de uso da primeira execução fica em `.studio_state.json`, ignorado pelo
Git. Esta fase não implementa métricas nem publicação.

## Fase 3 — Pacote simples

Depois de preencher e revisar o episódio, o fluxo curto é:

```text
studio validate <series> <episode>
studio lint <series> <episode>
studio pack <series> <episode>
```

O `pack` gera `pacote/0_PERSONAGENS.md`, `pacote/1_ROTEIRO.md`, `pacote/2_IMAGENS.md` e
`pacote/3_VIDEOS.md`. O primeiro documento gera rosto e corpo dos personagens que aparecem no
episódio; os arquivos aprovados ficam em `series/<id>/assets/characters/`. Ele também cria
`assets/images/` e `assets/videos/`; o usuário move os arquivos aprovados para essas pastas. A aprovação depende exclusivamente do arquivo
existir com o nome esperado, não do `status` no YAML. O pacote não mostra contas, créditos ou
sessão. Se `validate` tiver ERROR, nada é gerado.

O fluxo oficial atual está em `series/amiga_de_mentira`: oito episódios planejados, perfil `growth`,
estilo `weird_toon` e episódio 1 pronto para revisar com `studio validate`, `studio lint` e `studio pack`.

## Fase 1

Esta primeira implementação cobre estrutura, modelos, criação de séries e episódios, validação
geração de prompts e acompanhamento visual da produção. Créditos/alocação, sessão completa,
tentativas avançadas, métricas e publicação ficam para fases posteriores.
