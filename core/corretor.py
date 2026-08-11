from typing import Dict
from dataclasses import dataclass


@dataclass
class ResultadoCorrecao:
    acertos: int
    erros: int
    brancos: int
    duplas: int
    percentual: float
    nota: float
    detalhes: Dict[int, str]


class Corretor:
    def __init__(self, gabarito):
        self.gabarito = gabarito
        self.peso_por_questao = 1.0

    def corrigir(self, respostas_aluno: Dict[int, str]) -> ResultadoCorrecao:
        total = self.gabarito.total_questoes
        acertos = erros = brancos = duplas = 0
        detalhes = {}

        for questao in range(1, total + 1):
            resp_aluno = respostas_aluno.get(questao, '').strip()
            resp_gabarito = self.gabarito.get_resposta(questao)

            if not resp_aluno:
                status = 'branco'
                brancos += 1
            elif len(resp_aluno) > 1:
                status = 'dupla'
                duplas += 1
            elif resp_aluno == resp_gabarito:
                status = 'acerto'
                acertos += 1
            else:
                status = 'erro'
                erros += 1

            detalhes[questao] = status

        percentual = (acertos / total) * 100 if total > 0 else 0
        nota = acertos * self.peso_por_questao

        return ResultadoCorrecao(
            acertos=acertos, erros=erros, brancos=brancos, duplas=duplas,
            percentual=percentual, nota=nota, detalhes=detalhes
        )
