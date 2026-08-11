"""
Detecção de marcações em cartão-resposta (OMR simplificado).

IMPORTANTE - LEIA ANTES DE USAR:
Este módulo assume um layout SIMPLES: um único bloco de questões, uma
embaixo da outra, com exatamente `n_alternativas` bolhas por linha
(A, B, C, D, E) alinhadas na mesma faixa horizontal do cartão inteiro.

Ele NÃO reconhece automaticamente cartões com múltiplas colunas de
questões lado a lado (ex: questões 1-20 numa coluna, 21-40 noutra).
Se o seu cartão físico for assim, cada bloco de coluna precisa ser
processado separadamente (recorte a imagem em N faixas verticais antes
de chamar `extrair_respostas`, uma por bloco de coluna).

A versão anterior deste arquivo tinha um bug: a função que mapeava a
posição X para a alternativa sempre retornava 'A', não importava onde
o círculo estivesse. Aqui isso foi substituído por um agrupamento real
das posições X em `n_alternativas` "raias" (clustering 1D), então cada
marcação é comparada com o centro de cada raia para decidir A/B/C/D/E.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import os


class ProcessadorImagem:
    def __init__(self, n_alternativas: int = 5, total_questoes: int = 60):
        self.imagem_original = None
        self.imagem_processada = None
        self.marcacoes_detectadas: Dict[int, str] = {}
        self.deteccoes_visuais = None
        self.n_alternativas = n_alternativas
        self.total_questoes = total_questoes
        self.alternativas = ['A', 'B', 'C', 'D', 'E'][:n_alternativas]

    # ------------------------------------------------------------------ #
    # Carregamento e pré-processamento
    # ------------------------------------------------------------------ #
    def carregar_imagem(self, caminho: str) -> np.ndarray:
        if not os.path.exists(caminho):
            raise FileNotFoundError(f"Imagem não encontrada: {caminho}")

        img = cv2.imread(caminho)
        if img is None:
            raise ValueError("Não foi possível ler a imagem")

        self.imagem_original = img.copy()
        return img

    def preprocessar(self, img: np.ndarray) -> np.ndarray:
        altura, largura = img.shape[:2]
        if largura > 2000:
            escala = 2000 / largura
            img = cv2.resize(img, (int(largura * escala), int(altura * escala)))

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = np.ones((3, 3), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        self.imagem_processada = cleaned
        return cleaned

    # ------------------------------------------------------------------ #
    # Detecção de círculos preenchidos
    # ------------------------------------------------------------------ #
    def detectar_circulos(self, img_binaria: np.ndarray, img_colorida: np.ndarray) -> List[Tuple[int, int, int]]:
        min_radius, max_radius, min_dist = 8, 25, 15

        circles = cv2.HoughCircles(
            img_binaria, cv2.HOUGH_GRADIENT, dp=1, minDist=min_dist,
            param1=50, param2=30, minRadius=min_radius, maxRadius=max_radius
        )

        circulos_detectados = []
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                if self._is_circle_filled(img_binaria, x, y, r):
                    circulos_detectados.append((x, y, r))
                    cv2.circle(img_colorida, (x, y), r, (0, 255, 0), 2)
                    cv2.circle(img_colorida, (x, y), 2, (0, 0, 255), 3)

        self.deteccoes_visuais = img_colorida
        return circulos_detectados

    def _is_circle_filled(self, img_binaria: np.ndarray, cx: int, cy: int, r: int) -> bool:
        mask = np.zeros_like(img_binaria)
        cv2.circle(mask, (cx, cy), r, 255, -1)
        area_circulo = np.pi * r * r
        pixels_brancos = np.sum((img_binaria & mask) > 0)
        return pixels_brancos / area_circulo > 0.4

    # ------------------------------------------------------------------ #
    # Agrupamento em linhas (questões) e colunas (alternativas)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _kmeans_1d(valores: List[float], k: int, iteracoes: int = 25) -> List[float]:
        """K-means simples em 1 dimensão, sem depender de scikit-learn."""
        valores_arr = np.array(sorted(valores), dtype=float)
        if len(valores_arr) < k:
            # Poucos pontos: espalha centros uniformemente no intervalo observado.
            lo, hi = valores_arr.min(), valores_arr.max()
            return list(np.linspace(lo, hi, k))

        # Inicializa centros em quantis, para começar já bem espalhado.
        indices = np.linspace(0, len(valores_arr) - 1, k).astype(int)
        centros = valores_arr[indices].astype(float)

        for _ in range(iteracoes):
            distancias = np.abs(valores_arr[:, None] - centros[None, :])
            atribuicoes = np.argmin(distancias, axis=1)
            novos_centros = centros.copy()
            for i in range(k):
                pontos = valores_arr[atribuicoes == i]
                if len(pontos) > 0:
                    novos_centros[i] = pontos.mean()
            if np.allclose(novos_centros, centros):
                break
            centros = novos_centros

        return sorted(centros.tolist())

    def detectar_marcacoes_alternativas(self, img: np.ndarray) -> Dict[int, str]:
        img_binaria = self.preprocessar(img)
        img_visual = img.copy()
        circulos = self.detectar_circulos(img_binaria, img_visual)

        marcacoes: Dict[int, str] = {}
        if not circulos:
            self.marcacoes_detectadas = marcacoes
            return marcacoes

        # 1) Agrupa em linhas (uma linha ~ uma questão) por proximidade em Y.
        circulos_ordenados = sorted(circulos, key=lambda c: (c[1], c[0]))
        linhas = []
        linha_atual = [circulos_ordenados[0]]
        y_ref = circulos_ordenados[0][1]

        for (x, y, r) in circulos_ordenados[1:]:
            if abs(y - y_ref) < 30:
                linha_atual.append((x, y, r))
            else:
                linhas.append(sorted(linha_atual, key=lambda c: c[0]))
                linha_atual = [(x, y, r)]
                y_ref = y
        linhas.append(sorted(linha_atual, key=lambda c: c[0]))

        # 2) Descobre as "raias" das alternativas (A..E) olhando o X de TODAS
        #    as marcações preenchidas na folha inteira, via k-means 1D.
        todos_x = [x for linha in linhas for (x, y, r) in linha]
        centros_colunas = self._kmeans_1d(todos_x, self.n_alternativas)

        # 3) Para cada linha (questão), decide qual alternativa foi marcada
        #    comparando o X de cada bolha preenchida com a raia mais próxima.
        for idx, linha in enumerate(linhas, 1):
            if idx > self.total_questoes:
                break
            if not linha:
                continue

            alternativas_marcadas = []
            for (x, y, r) in linha:
                distancias = [abs(x - c) for c in centros_colunas]
                col = int(np.argmin(distancias))
                alternativas_marcadas.append(self.alternativas[col])

            # Remove duplicatas mantendo ordem (pode haver 2 bolhas
            # detectadas muito perto uma da outra para a mesma alternativa).
            vistos = []
            for a in alternativas_marcadas:
                if a not in vistos:
                    vistos.append(a)

            marcacoes[idx] = ''.join(vistos)

        self.marcacoes_detectadas = marcacoes
        return marcacoes

    # ------------------------------------------------------------------ #
    # Pipeline público
    # ------------------------------------------------------------------ #
    def extrair_respostas(self, caminho_imagem: str) -> Dict[int, str]:
        try:
            img = self.carregar_imagem(caminho_imagem)
            return self.detectar_marcacoes_alternativas(img)
        except Exception as e:
            print(f"Erro ao processar imagem: {e}")
            return {}

    def gerar_imagem_com_deteccoes(self) -> Optional[np.ndarray]:
        if self.deteccoes_visuais is not None:
            return self.deteccoes_visuais
        return self.imagem_original
