# Fluxo simples

O fluxo principal é preparar o episódio e gerar um pacote pequeno para copiar e colar no Google
Flow. O Studio continua offline: ele não abre navegador, não faz login e não move arquivos.

1. Escreva o roteiro em `script.md` e quebre o episódio em `shots.yaml`.
2. Rode `studio validate <series> <episode>`.
3. Rode `studio lint <series> <episode>` e corrija todos os erros.
4. Rode `studio pack <series> <episode>`.
5. Gere as imagens na ordem de `pacote/2_IMAGENS.md` e mova os resultados aprovados para
   `assets/images/` com o nome esperado.
6. Gere os vídeos na ordem de `pacote/3_VIDEOS.md`, sempre anexando a imagem aprovada, e mova os
   resultados para `assets/videos/`.
7. Rode `studio pack` novamente para atualizar os três documentos e os marcadores de aprovação.

O comando `pack` nunca move, renomeia ou apaga arquivos em `assets/`. Ele sobrescreve somente a
pasta `pacote/`. Um arquivo em Downloads não aprova um plano; o arquivo precisa estar na pasta
de assets do episódio e ter o nome esperado, com uma extensão aceita.

## Modo avançado

Para acompanhar custos, contas e uma fila detalhada, ainda existem os comandos avançados:

```text
studio board <series> <episode>
studio next <series> <episode>
studio plan <series> <episode>
studio plan-day --episodes 1
studio session <series> <episode> [--account conta1]
```

Eles continuam disponíveis, mas não fazem parte do pacote simples. O Studio não acessa contas,
não gera mídia e não faz chamadas de rede.
