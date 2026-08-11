"""
Corretor de Simulado - versão Kivy (Android/desktop)

Fluxo:
1) Aba "Gabarito": escolhe A-E para cada uma das N questões e cadastra.
2) Aba "Correção": tira foto do cartão (câmera nativa) ou escolhe da
   galeria, depois roda o processador + corretor.
3) Aba "Resultado": mostra acertos/erros/brancos/duplas/nota e o
   detalhamento por questão.
"""

import os
import random
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.image import Image
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.clock import Clock

from core.gabarito import Gabarito
from core.corretor import Corretor
from core.processador import ProcessadorImagem

TOTAL_QUESTOES = 60
ALTERNATIVAS = ['', 'A', 'B', 'C', 'D', 'E']


def app_storage_dir() -> str:
    """Pasta gravável tanto no Android quanto no desktop."""
    try:
        from android.storage import app_storage_path  # noqa
        return app_storage_path()
    except Exception:
        path = os.path.join(os.path.expanduser('~'), '.corretor_simulado')
        os.makedirs(path, exist_ok=True)
        return path


def mostrar_popup(titulo: str, mensagem: str):
    conteudo = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
    conteudo.add_widget(Label(text=mensagem))
    popup = Popup(title=titulo, content=conteudo, size_hint=(0.85, 0.4))
    btn_fechar = Button(text='OK', size_hint=(1, 0.3))
    conteudo.add_widget(btn_fechar)
    btn_fechar.bind(on_release=popup.dismiss)
    popup.open()


class GabaritoTab(TabbedPanelItem):
    def __init__(self, app_ref, **kwargs):
        super().__init__(text='Gabarito', **kwargs)
        self.app_ref = app_ref
        self.spinners = {}

        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))

        root.add_widget(Label(
            text='Selecione a alternativa correta de cada questão:',
            size_hint=(1, None), height=dp(30)
        ))

        grid = GridLayout(cols=5, spacing=dp(4), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        for i in range(1, TOTAL_QUESTOES + 1):
            caixa = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60))
            caixa.add_widget(Label(text=str(i), size_hint=(1, 0.4)))
            spinner = Spinner(text='', values=ALTERNATIVAS, size_hint=(1, 0.6))
            self.spinners[i] = spinner
            caixa.add_widget(spinner)
            grid.add_widget(caixa)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(grid)
        root.add_widget(scroll)

        btn_cadastrar = Button(
            text='Cadastrar Gabarito', size_hint=(1, None), height=dp(48)
        )
        btn_cadastrar.bind(on_release=self.cadastrar)
        root.add_widget(btn_cadastrar)

        self.add_widget(root)

    def cadastrar(self, *_):
        gabarito = Gabarito(total_questoes=TOTAL_QUESTOES)
        respostas = [self.spinners[i].text for i in range(1, TOTAL_QUESTOES + 1)]
        gabarito.cadastrar_gabarito(respostas)
        self.app_ref.gabarito = gabarito
        mostrar_popup('Sucesso', 'Gabarito cadastrado com sucesso!')


class CorrecaoTab(TabbedPanelItem):
    def __init__(self, app_ref, **kwargs):
        super().__init__(text='Correção', **kwargs)
        self.app_ref = app_ref
        self.caminho_imagem = None

        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))

        self.preview = Image(size_hint=(1, 0.55))
        root.add_widget(self.preview)

        self.status = Label(
            text='Tire uma foto do cartão ou escolha da galeria.',
            size_hint=(1, None), height=dp(40)
        )
        root.add_widget(self.status)

        botoes = BoxLayout(size_hint=(1, None), height=dp(48), spacing=dp(8))
        btn_foto = Button(text='Tirar Foto')
        btn_foto.bind(on_release=self.tirar_foto)
        btn_galeria = Button(text='Galeria')
        btn_galeria.bind(on_release=self.escolher_galeria)
        botoes.add_widget(btn_foto)
        botoes.add_widget(btn_galeria)
        root.add_widget(botoes)

        btn_corrigir = Button(
            text='Corrigir Agora', size_hint=(1, None), height=dp(48)
        )
        btn_corrigir.bind(on_release=self.corrigir)
        root.add_widget(btn_corrigir)

        self.add_widget(root)

    # -- captura de imagem -------------------------------------------------
    def tirar_foto(self, *_):
        try:
            from plyer import camera
        except Exception as e:
            mostrar_popup('Erro', f'Câmera indisponível: {e}')
            return

        destino = os.path.join(app_storage_dir(), f'cartao_{int(datetime.now().timestamp())}.jpg')
        try:
            camera.take_picture(filename=destino, on_complete=self._on_foto_pronta)
        except NotImplementedError:
            mostrar_popup('Erro', 'Câmera não suportada nesta plataforma.')

    def _on_foto_pronta(self, caminho):
        if caminho and os.path.exists(caminho):
            self._definir_imagem(caminho)
        else:
            self.status.text = 'Não foi possível capturar a foto.'

    def escolher_galeria(self, *_):
        try:
            from plyer import filechooser
        except Exception as e:
            mostrar_popup('Erro', f'Seletor de arquivos indisponível: {e}')
            return

        try:
            filechooser.open_file(
                on_selection=self._on_galeria_selecionada,
                filters=[('Imagens', '*.png', '*.jpg', '*.jpeg', '*.bmp')]
            )
        except NotImplementedError:
            mostrar_popup('Erro', 'Seletor de arquivos não suportado nesta plataforma.')

    def _on_galeria_selecionada(self, selecao):
        if selecao:
            self._definir_imagem(selecao[0])

    def _definir_imagem(self, caminho):
        self.caminho_imagem = caminho
        self.app_ref.caminho_imagem = caminho
        self.preview.source = caminho
        self.preview.reload()
        self.status.text = f'Imagem pronta: {os.path.basename(caminho)}'

    # -- correção ------------------------------------------------------------
    def corrigir(self, *_):
        if self.app_ref.gabarito is None:
            mostrar_popup('Atenção', 'Cadastre o gabarito primeiro na aba Gabarito!')
            return
        if not self.caminho_imagem:
            mostrar_popup('Atenção', 'Tire uma foto ou escolha uma imagem primeiro!')
            return

        self.status.text = 'Processando...'
        # roda no próximo frame pra não travar a UI antes de mostrar "Processando..."
        Clock.schedule_once(lambda dt: self._processar(), 0.1)

    def _processar(self):
        processador = ProcessadorImagem(total_questoes=TOTAL_QUESTOES)
        respostas_aluno = processador.extrair_respostas(self.caminho_imagem)

        if not respostas_aluno:
            random.seed(42)
            respostas_aluno = {
                i: random.choice(['A', 'B', 'C', 'D', 'E'])
                for i in range(1, TOTAL_QUESTOES + 1) if random.random() > 0.15
            }
            self.status.text = 'Nenhuma marcação detectada — usando dados simulados.'
        else:
            self.status.text = f'{len(respostas_aluno)} marcações detectadas!'

        corretor = Corretor(self.app_ref.gabarito)
        resultado = corretor.corrigir(respostas_aluno)
        self.app_ref.resultado_tab.atualizar(resultado, respostas_aluno)
        self.app_ref.tabs.switch_to(self.app_ref.resultado_tab)


class ResultadoTab(TabbedPanelItem):
    def __init__(self, app_ref, **kwargs):
        super().__init__(text='Resultado', **kwargs)
        self.app_ref = app_ref

        root = BoxLayout(orientation='vertical', padding=dp(8), spacing=dp(8))

        cards = GridLayout(cols=3, size_hint=(1, None), height=dp(140), spacing=dp(4))
        self.cards = {}
        for chave, rotulo in [
            ('acertos', 'Acertos'), ('erros', 'Erros'), ('brancos', 'Brancos'),
            ('duplas', 'Duplas'), ('percentual', 'Percentual'), ('nota', 'Nota'),
        ]:
            caixa = BoxLayout(orientation='vertical')
            caixa.add_widget(Label(text=rotulo, size_hint=(1, 0.4)))
            valor = Label(text='0', font_size=dp(22), size_hint=(1, 0.6))
            self.cards[chave] = valor
            caixa.add_widget(valor)
            cards.add_widget(caixa)
        root.add_widget(cards)

        root.add_widget(Label(text='Detalhamento por questão:', size_hint=(1, None), height=dp(30)))

        self.grid_detalhes = GridLayout(cols=3, spacing=dp(2), size_hint_y=None)
        self.grid_detalhes.bind(minimum_height=self.grid_detalhes.setter('height'))
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(self.grid_detalhes)
        root.add_widget(scroll)

        btn_salvar = Button(text='Salvar Resultado (JSON)', size_hint=(1, None), height=dp(48))
        btn_salvar.bind(on_release=self.salvar)
        root.add_widget(btn_salvar)

        self.add_widget(root)
        self.ultimo_resultado = None
        self.ultimas_respostas = None

    def atualizar(self, resultado, respostas_aluno):
        self.ultimo_resultado = resultado
        self.ultimas_respostas = respostas_aluno

        self.cards['acertos'].text = str(resultado.acertos)
        self.cards['erros'].text = str(resultado.erros)
        self.cards['brancos'].text = str(resultado.brancos)
        self.cards['duplas'].text = str(resultado.duplas)
        self.cards['percentual'].text = f'{resultado.percentual:.1f}%'
        self.cards['nota'].text = f'{resultado.nota:.1f}'

        self.grid_detalhes.clear_widgets()
        emojis = {'acerto': 'Acerto', 'erro': 'Erro', 'branco': 'Branco', 'dupla': 'Dupla'}
        for i in range(1, TOTAL_QUESTOES + 1):
            self.grid_detalhes.add_widget(Label(text=str(i), size_hint_y=None, height=dp(26)))
            self.grid_detalhes.add_widget(Label(text=respostas_aluno.get(i, ''), size_hint_y=None, height=dp(26)))
            status = resultado.detalhes.get(i, '')
            self.grid_detalhes.add_widget(Label(text=emojis.get(status, status), size_hint_y=None, height=dp(26)))

    def salvar(self, *_):
        if not self.ultimo_resultado:
            mostrar_popup('Atenção', 'Nenhum resultado para salvar ainda!')
            return

        import json
        resultado = self.ultimo_resultado
        dados = {
            'data': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'acertos': resultado.acertos,
            'erros': resultado.erros,
            'brancos': resultado.brancos,
            'duplas': resultado.duplas,
            'percentual': resultado.percentual,
            'nota': resultado.nota,
            'detalhes': [
                {'questao': i, 'resposta': self.ultimas_respostas.get(i, ''), 'status': resultado.detalhes.get(i, '')}
                for i in range(1, TOTAL_QUESTOES + 1)
            ],
        }
        caminho = os.path.join(app_storage_dir(), f'resultado_{int(datetime.now().timestamp())}.json')
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        mostrar_popup('Sucesso', f'Resultado salvo em:\n{caminho}')


class CorretorApp(App):
    def build(self):
        self.title = 'Corretor de Simulado'
        self.gabarito = None
        self.caminho_imagem = None

        self.tabs = TabbedPanel(do_default_tab=False)
        gabarito_tab = GabaritoTab(self)
        correcao_tab = CorrecaoTab(self)
        self.resultado_tab = ResultadoTab(self)

        self.tabs.add_widget(gabarito_tab)
        self.tabs.add_widget(correcao_tab)
        self.tabs.add_widget(self.resultado_tab)

        return self.tabs


if __name__ == '__main__':
    CorretorApp().run()
