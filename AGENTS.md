 # AGENTS.md — Novelinha Studio

 ## Contexto

 Este repositório é um estúdio de produção de novelinhas verticais feitas por IA. A CLI `studio`
 organiza séries, monta prompts, planeja créditos de vídeo, gera folhas de sessão e controla status.
 Ela NÃO gera imagem/vídeo e NÃO automatiza contas do Google Flow ou de qualquer outra ferramenta.

 Leia `ofcNOVELINHA_STUDIO_SPEC.md` antes de qualquer tarefa.

 ## Regras de trabalho

 1. Implemente apenas a fase do roadmap que o usuário pediu. Não adiante fases.
 2. Python 3.11+, Typer, Pydantic v2, PyYAML, Jinja2, Rich, pytest, ruff.
 3. Escreva testes para toda lógica nova e rode `pytest` e `ruff check` antes de concluir.
 4. Nada específico de gênero pode estar hardcoded em `src/`.
 5. Valores de custo vêm de `config/production.yaml`. Imagem custa 0 créditos; vídeo usa a
    tabela configurável por duração.
 6. Os `lock_block` dos personagens são inseridos literalmente nos prompts.
 7. Nunca grave senhas, e-mails reais ou tokens. Contas são só apelidos.
 8. Não faça chamadas de rede, scraping ou automação de navegador.
 9. Windows first: use `pathlib` e evite dependência de shell Unix.
 10. Mensagens de commit em inglês; documentação para o usuário em português do Brasil.
 11. Se algo estiver ambíguo, escolha a opção mais simples, registre em `docs/LESSONS.md` e siga;
     pergunte só se a dúvida bloquear.

 ## Definição de pronto

 - Comandos implementados e documentados no README.
 - Testes passando.
 - Exemplo funcionando com `series/revenge_republic`.
- Sem regressão nas validações da especificação.

 ## Modo Autoria

 Quando o usuário fornecer uma ideia, brief ou roteiro em português, o agente deve criar ou
 atualizar `series.yaml`, `characters.yaml`, `locations.yaml`, o preset de estilo, `script.md` e
 `shots.yaml` seguindo `docs/AUTHORING_GUIDE.md`. Depois deve rodar `studio validate` e
 `studio lint`, corrigindo os arquivos até não haver erros.

A regra de não fazer chamadas de rede vale para o código do Studio: a CLI continua offline e
não automatiza geração de mídia, contas ou navegador. A autoria é feita pelo agente, que lê e
escreve os arquivos versionados no repositório.

O último passo do Modo Autoria é: rodar `validate`, depois `lint`, corrigir até zerar os erros,
rodar `studio pack <serie> <ep>`, e responder somente com o caminho da pasta `pacote/` e um
resumo de três linhas.
