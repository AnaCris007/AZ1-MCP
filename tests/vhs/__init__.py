"""Módulo VHS — gravação e reprodução de interações externas na suíte.

Implementa o mecanismo descrito na Seção 3.8.10 e especificado no contrato da
Seção 6.4.3 do artefato: preservar uma interação real com o provedor e
reproduzi-la depois, para que os testes de integração não repitam requisições
externas a cada execução nem dependam da disponibilidade do serviço.

A biblioteca escolhida no plano é o VCR.py; o que este módulo acrescenta em
volta dela é o que a biblioteca não faz — chave sensível ao conteúdo semântico,
sanitização em ambos os sentidos, manifesto com validade e orçamento de
chamadas reais, e bloqueio de rede durante o replay.

Uso típico em um teste:

    vhs = Vhs(raiz=RAIZ, modo=Modo.REPRODUZIR, versao_sdk=versao_de_pacote("deepgram-sdk"))
    chave = chave_stt(audio=audio, idioma="pt-BR", modelo="nova-3", termos=TERMOS, cenario="sucesso")

    with vhs.fita(chave):
        resultado = await transcrever(audio)

O que o replay NÃO prova, e o plano faz questão de registrar: contrato atual do
provedor, qualidade do modelo atual e latência de produção. Para isso existe o
modo `desligado`, que vai ao serviço real.
"""

from __future__ import annotations

from tests.vhs.chave import (
    VERSAO_CONTRATO_PADRAO,
    ChaveVhs,
    chave_chat,
    chave_embedding,
    chave_stt,
    chave_tts,
)
from tests.vhs.erros import (
    CampanhaEmAndamento,
    CampanhaEncerrada,
    ErroVhs,
    LimiteDeChamadasReais,
    RedeBloqueada,
    RegistroAusente,
    RegistroCorrompido,
    RegistroVencido,
)
from tests.vhs.fita import CRITERIO_DE_CORRESPONDENCIA, Vhs, versao_de_pacote
from tests.vhs.manifesto import (
    ORIGEM_REAL,
    ORIGEM_SIMULADA,
    VALIDADE_PADRAO_DIAS,
    Campanha,
    Manifesto,
    Registro,
)
from tests.vhs.modos import Modo
from tests.vhs.rede import ContadorDeRede, contador_de_conexoes, rede_bloqueada
from tests.vhs.sanitizacao import MARCA, segredos_do_ambiente, varrer_segredos

__all__ = [
    "CRITERIO_DE_CORRESPONDENCIA",
    "MARCA",
    "ORIGEM_REAL",
    "ORIGEM_SIMULADA",
    "VALIDADE_PADRAO_DIAS",
    "VERSAO_CONTRATO_PADRAO",
    "Campanha",
    "CampanhaEmAndamento",
    "CampanhaEncerrada",
    "ChaveVhs",
    "ContadorDeRede",
    "ErroVhs",
    "LimiteDeChamadasReais",
    "Manifesto",
    "Modo",
    "RedeBloqueada",
    "Registro",
    "RegistroAusente",
    "RegistroCorrompido",
    "RegistroVencido",
    "Vhs",
    "chave_chat",
    "chave_embedding",
    "chave_stt",
    "chave_tts",
    "contador_de_conexoes",
    "rede_bloqueada",
    "segredos_do_ambiente",
    "varrer_segredos",
    "versao_de_pacote",
]
