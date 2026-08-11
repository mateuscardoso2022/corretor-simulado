from typing import Dict, List, Optional


class Gabarito:
    """Armazena o gabarito oficial (respostas corretas) do simulado."""

    def __init__(self, total_questoes: int = 60):
        self.respostas: Dict[int, str] = {}
        self.total_questoes = total_questoes

    def cadastrar_resposta(self, numero: int, alternativa: str) -> bool:
        if 1 <= numero <= self.total_questoes:
            if alternativa.upper() in ['A', 'B', 'C', 'D', 'E']:
                self.respostas[numero] = alternativa.upper()
                return True
        return False

    def cadastrar_gabarito(self, respostas: List[str]) -> None:
        for i, resp in enumerate(respostas[:self.total_questoes], 1):
            if resp.strip():
                self.cadastrar_resposta(i, resp.strip())

    def get_resposta(self, numero: int) -> Optional[str]:
        return self.respostas.get(numero)

    def limpar(self):
        self.respostas.clear()
