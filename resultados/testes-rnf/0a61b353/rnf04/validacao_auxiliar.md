# Validação auxiliar do ambiente

Após a campanha do RNF04, foram executadas as suítes focadas nas duas
fronteiras usadas pelo instrumento:

```text
python -m unittest tests.test_chat_api tests.test_voice_api -q
Ran 41 tests in 0.095s
OK
```

Resultado: **41/41 testes aprovados**. Isso confirma que a ausência de trilha
para voz e para os dois erros controlados não decorreu de uma quebra geral das
rotas no ambiente de execução.
