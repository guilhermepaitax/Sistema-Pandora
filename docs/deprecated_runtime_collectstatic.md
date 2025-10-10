# Runtime collectstatic (Deprecated)

O processo de executar `collectstatic` no entrypoint foi removido.

Motivos:
- Já coletado no build (Docker multi-stage) garantindo imagem imutável.
- Evita escrita desnecessária em filesystem efêmero do Cloud Run.
- Reduz tempo de cold start.

Variáveis removidas/descontinuadas:
- `RUN_COLLECTSTATIC`

Se precisar forçar nova coleta, basta rebuildar a imagem ou executar manualmente local e incluir os arquivos no contexto.
