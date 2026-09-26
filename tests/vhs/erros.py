"""Falhas do módulo VHS.

Cada erro existe para ser distinguível na asserção de um teste. Os casos TI-47 a
TI-49 exigem separar três situações que um `FileNotFoundError` genérico
confundiria: o registro que nunca existiu, o que existe mas foi corrompido, e o
que existe e está íntegro, mas venceu. As três levam à mesma consequência em
modo `reproduzir` — falhar sem rede —, e por motivos diferentes.
"""

from __future__ import annotations


class ErroVhs(Exception):
    """Raiz da hierarquia, para quem quiser capturar qualquer falha do módulo."""


class RegistroAusente(ErroVhs):
    """Não há gravação para a chave: nem no manifesto, nem no disco."""


class RegistroCorrompido(ErroVhs):
    """A gravação existe, e o conteúdo não confere com o hash do manifesto."""


class RegistroVencido(ErroVhs):
    """A gravação existe e está íntegra, e passou da validade declarada.

    O VCR.py não conhece validade — ele só sabe se o arquivo casa com a
    requisição. O prazo é controle deste harness, conforme o item 7 do contrato
    de implementação da Seção 6.4.3.
    """


class RedeBloqueada(ErroVhs):
    """Alguém tentou abrir conexão enquanto a fita rodava em modo `reproduzir`.

    É o que transforma "nenhuma chamada nova" de promessa em asserção: em replay
    o bloqueio está armado, e uma tentativa de sair para a rede levanta aqui em
    vez de passar despercebida.
    """


class LimiteDeChamadasReais(ErroVhs):
    """A campanha atingiu o teto de chamadas reais fixado no manifesto.

    Item 10 da Seção 6.4.3: o número máximo é fixado antes de gravar, e a
    campanha é interrompida ao alcançá-lo.
    """


class CampanhaEncerrada(ErroVhs):
    """A campanha foi encerrada; gravar de novo exige abrir outra."""


class CampanhaEmAndamento(ErroVhs):
    """Pediram para abrir campanha sobre outra que já gastou chamadas reais.

    Abrir zera o contador. Se isso acontecer sem querer — rodar o roteiro de
    gravação duas vezes, por exemplo —, o teto do item 10 deixa de limitar
    coisa alguma: cada execução ganha o orçamento inteiro de novo, e o
    manifesto passa a declarar menos chamadas do que foram feitas. Reabrir
    continua possível, e agora é decisão explícita de quem grava.
    """
