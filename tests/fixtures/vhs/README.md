# Gravações do módulo VHS

Raiz das fitas usadas pelas suítes de integração. O módulo que lê e escreve
aqui é [`tests/vhs/`](../../vhs); o contrato está na Seção 6.4.3 do
`docs/Projeto.md`.

## O que pode ser versionado

Apenas **amostra sintética, sanitizada e selecionada para regressão**, junto do
`manifesto.json` revisado — item 8 do contrato. Fora isso:

- nada de token, cookie, URL assinada, URI de banco ou resposta corporativa;
- áudio e registros com restrição de retenção ficam em armazenamento de teste,
  com acesso e expurgo definidos pela equipe, e não no histórico do Git;
- gravação temporária de campanha sai no encerramento
  (`Manifesto.encerrar_campanha`), e não deve chegar ao commit.

A sanitização é automática — `tests/vhs/sanitizacao.py` remove os cabeçalhos e
parâmetros de credencial nos dois sentidos —, e ainda assim a revisão do diff
antes do commit é obrigatória: a lista de nomes proibidos cobre o previsto, não
o que um provedor novo invente.

## Organização

```
<provedor>/<modelo>/<cenario>/<versao_contrato>/<digest>.yaml
```

O `digest` resume o que distingue semanticamente a chamada — para STT, hash do
áudio, idioma e termos; para chat, mensagem, instrução e parâmetros; para TTS,
texto, voz e formato; para embeddings, texto e dimensão. Mudou qualquer um
deles, é outra fita (TI-52).

Arquivos `*.candidato.yaml` são versões geradas em modo `atualizar`, à espera
de revisão do diff. Eles não são versionados: ou são promovidos com
`Vhs.promover_candidato`, ou descartados.

## Comandos

```bash
python -m unittest tests.test_integracao_vhs -v
```
