# Lessons

- A capacidade por conta usa `floor(créditos_diários / custo_do_clipe) - reserva`; o planejamento
  calcula uma tentativa esperada e o pior caso configurado. Contas são apelidos manuais, nunca
  acessadas pela ferramenta.
- Custos não conferidos recentemente devem ser revisados na interface do Flow. Um custo `null`
  bloqueia o planejamento para evitar estimativas inventadas.
- `studio plan` deve ser conferido antes dos vídeos e `studio session` organiza imagens, anexos e
  vídeos por conta sem fazer login ou chamadas externas.
- O pacote simples trata o YAML como plano e o filesystem como aprovação: somente o arquivo com
  nome esperado dentro de `assets/images/` ou `assets/videos/` marca um plano como aprovado.
  Downloads externos e `status` não contam.

- Todo clipe carrega fala ou voz off; silêncio só como golpe, no máximo 1 por episódio.
- Um beat abstrato não basta para o modo econômico: cada vídeo precisa de estado inicial,
  ações temporizadas, reação visível, estado final, som e restrições de continuidade.

- Imagens derivadas devem começar com a instrução de referência para preservar rosto, cabelo,
  roupa, sala e iluminação.
- O `lock_block` deve acompanhar exatamente a imagem aprovada e ser copiado literalmente.
- Imagem é gratuita; todos os custos de vídeo, por resolução e duração, vêm exclusivamente de
  `config/production.yaml`. Custo `null` é desconhecido e deve bloquear o cálculo.
- Perfil de produção segue a precedência episódio → série → `active_profile`; a resolução e a
  faixa de duração devem ser verificadas antes de gerar mídia.
- `voice_notes` pode registrar contexto de autoria, mas nunca deve virar instrução no prompt:
  use `delivery` da fala e, como fallback, um único `default_delivery` do personagem; mantenha
  sempre o espelho `_pt`.
- O ritmo econômico precisa bloquear fala curta demais quando configurado: o lint informa quantos
  segundos faltam preencher, valida o gancho antes de 2 s, o cliffhanger e o runtime com cold open.
- `series/revenge_republic` é apenas fixture pausada de testes; a série real ainda não existe.
- A bíblia é contrato verificável: o template não cria conteúdo, mas exige seções completas,
  grade com cliffhanger e nenhuma instrução de placeholder antes de uma série entrar em produção.
- Em personagens 3D estranhos, uma única silhueta geométrica e uma paleta de roupa exclusiva são
  mais fáceis de conferir em 360p do que detalhes realistas; `safety.blocked_terms` ajuda, mas não
  garante detectar toda referência de IP ou semelhança com pessoa real.
