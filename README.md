# Corretor de Simulado — versão Kivy (Android)

Reescrita do app original (PySide6) em Kivy, para permitir gerar um APK
real. A lógica de negócio (`core/gabarito.py`, `core/corretor.py`) é a
mesma; `core/processador.py` foi corrigido (ver seção "O que foi
consertado" abaixo); a interface (`main.py`) foi refeita do zero em Kivy.

## Como gerar o APK (sem instalar nada na sua máquina)

Este projeto já vem com um workflow do GitHub Actions
(`.github/workflows/build-apk.yml`) que compila o APK automaticamente.

1. Crie um repositório novo no GitHub (pode ser privado).
2. Suba estes arquivos para ele (`git init`, `git add .`, `git commit`, `git push`).
3. Vá na aba **Actions** do repositório → o workflow "Build APK" vai
   rodar sozinho. Se não rodar, clique em **Run workflow** manualmente.
4. **O primeiro build demora bastante** (30–60+ minutos), porque ele
   precisa baixar e compilar o Android NDK/SDK, numpy e opencv do zero.
   Builds seguintes são mais rápidos (cache).
5. Quando terminar, abra a execução concluída → seção **Artifacts** →
   baixe `corretor-simulado-apk` → dentro tem o `.apk`.
6. Transfira o `.apk` pro celular (pode ser por USB, Drive, etc.) e
   instale (é preciso permitir "instalar de fontes desconhecidas").

Isso te dá um APK de **debug**, ótimo pra testar. Pra distribuir de
verdade (Play Store) seria necessário assinar com uma chave de release
— posso te ajudar com isso depois se for o caso.

## Rodar no PC antes de gerar o APK (recomendado)

Testar no computador é bem mais rápido que esperar o build do APK:

```bash
pip install kivy plyer opencv-python numpy pillow
python main.py
```

No desktop, os botões de câmera/galeria usam o `plyer`, que no Windows/
Linux/Mac abre o seletor de arquivo do sistema (não a câmera de verdade)
— isso é esperado, é só pra você testar o fluxo do app.

## O que foi consertado em relação ao projeto original

- **Bug crítico**: em `processador.py`, a função que decidia qual
  alternativa (A-E) uma marcação representava sempre retornava `'A'`,
  não importava a posição. Isso foi trocado por um agrupamento real das
  posições X das marcações em 5 "raias" (k-means 1D simples).
- **Limitação que continua existindo**: a detecção assume um cartão
  com um único bloco de questões (uma embaixo da outra, 5 bolhas por
  linha, A a E). Cartões com múltiplas colunas de questões lado a lado
  não são reconhecidos automaticamente — precisaria recortar a imagem
  em blocos antes de processar, ou calibrar coordenadas fixas para o
  layout específico do seu cartão impresso.
- Câmera trocada de `PySide6.QtMultimedia` (não funciona em Android)
  para `plyer.camera` (abre o app de câmera nativo do Android).
- "Escolher da galeria" trocado de `QFileDialog` para
  `plyer.filechooser` (compatível com Android).

## Próximos passos sugeridos

- Testar com fotos reais do cartão-resposta específico que vocês usam
  e ajustar `min_radius`/`max_radius`/`min_dist` em
  `core/processador.py` conforme o tamanho real das bolhas na foto.
- Se o cartão tiver várias colunas de questões, me mostre uma foto dele
  que eu ajusto a lógica de recorte por blocos.
