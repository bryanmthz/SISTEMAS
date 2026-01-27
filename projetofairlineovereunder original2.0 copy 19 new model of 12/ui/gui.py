import math
import sys
import re
from PyQt5.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QTextEdit, QGroupBox, QFormLayout, QCheckBox, QToolButton,
    QApplication, QListWidget, QListWidgetItem, QMenu, QLineEdit
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5 import QtGui

from core.calculations import (
    calcular_lambdas,
    calcular_odds_completas,
    ciclo_linha_asiatica,
    ciclo_linha_asiatica_para_baixo,
    obter_linha_atual,
    calcular_linha_asiatica,

    definir_linha_atual
)
from utils.styles import get_stylesheet


# =========================================================
# CONFIG: limitar o GUI de 0.5 até 3.5 (sem 3.75+ e sem 4.5)
# =========================================================
LINHAS_GUI = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]


def _linha_suffix_key(linha: float) -> str:
    """
    Converte a linha em sufixo usado no nome do campo:
    0.5  -> "05"
    0.75 -> "075"
    1.0  -> "10"
    1.25 -> "125"
    1.5  -> "15"
    1.75 -> "175"
    2.0  -> "20"
    2.25 -> "225"
    2.5  -> "25"
    2.75 -> "275"
    3.0  -> "30"
    3.25 -> "325"
    3.5  -> "35"
    """
    frac = round(linha - int(linha), 2)
    if frac in (0.0, 0.5):
        s = f"{linha:.1f}"   # 1.0 -> "1.0" => "10"; 0.5 -> "0.5" => "05"
    else:
        s = f"{linha:.2f}"   # 1.25 -> "1.25" => "125"; 0.75 -> "0.75" => "075"
    return s.replace(".", "")


def _odd_key_over(linha: float) -> str:
    return f"over{_linha_suffix_key(linha)}"


def _odd_key_under(linha: float) -> str:
    return f"under{_linha_suffix_key(linha)}"


class CalculadoraEstatistica(QWidget):
    def __init__(self):
        super().__init__()
        self.dark_mode = True
        self.undo_stack = []
        self.valores_brutos = {
            'mandante': {'media_gols_marcados': 1.5, 'media_gols_sofridos': 1.2, 'ppg': 1.0},
            'visitante': {'media_gols_marcados': 1.3, 'media_gols_sofridos': 1.4, 'ppg': 1.0},
            'handicap_mandante': {'media_gols_marcados': 1.5, 'media_gols_sofridos': 1.2, 'ppg': 1.0},
            'handicap_visitante': {'media_gols_marcados': 1.3, 'media_gols_sofridos': 1.4, 'ppg': 1.0},
        }

        # Agora inclui 0.5 e 0.75 e termina em 3.5
        self.linha_to_spinbox_name = {
            0.5: "0.5",
            0.75: "0.75",
            1.0: "1.0",
            1.25: "1.25",
            1.5: "1.5",
            1.75: "1.75",
            2.0: "2.0",
            2.25: "2.25",
            2.5: "2.5",
            2.75: "2.75",
            3.0: "3.0",
            3.25: "3.25",
            3.5: "3.5",
        }

        self.setup_ui()
        self.setStyleSheet(get_stylesheet(self.dark_mode))
        self.connect_spinboxes()
        definir_linha_atual(2.5)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Captura Ctrl+Z para desfazer"""
        if event.type() == QEvent.KeyPress and event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo_last_action()
            return True
        return super().eventFilter(obj, event)

    def setup_ui(self):
        self.setWindowTitle('Calculadora Estatística - Previsão de Jogos')
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout()
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Aba Principal
        aba_principal = QWidget()
        aba_principal_layout = QHBoxLayout()
        self.mandante_group = self.create_team_section("Time Mandante")
        self.central_group = self.create_central_section()
        self.visitante_group = self.create_team_section("Time Visitante")
        aba_principal_layout.addWidget(self.mandante_group)
        aba_principal_layout.addWidget(self.central_group)
        aba_principal_layout.addWidget(self.visitante_group)
        aba_principal.setLayout(aba_principal_layout)
        self.tabs.addTab(aba_principal, "Principal")

        # Aba Handicap Asiático e Placares
        aba_handicap = QWidget()
        aba_handicap_layout = self.create_handicap_section()
        aba_handicap.setLayout(aba_handicap_layout)
        self.tabs.addTab(aba_handicap, "Handicap Asiático e Placares")

        # Aba Comparativo de Odds
        aba_odds = QWidget()
        aba_odds_layout = QVBoxLayout()
        self.odd_group = QGroupBox("Comparativo de Odds")
        odd_layout = QFormLayout()

        # ✅ Agora inclui 0.5 e 0.75; e remove tudo acima de 3.5
        odds_fields = [
            ("Over 0.5", "over05"), ("Under 0.5", "under05"),
            ("Over 0.75", "over075"), ("Under 0.75", "under075"),
            ("Over 1.0", "over10"), ("Under 1.0", "under10"),
            ("Over 1.25", "over125"), ("Under 1.25", "under125"),
            ("Over 1.5", "over15"), ("Under 1.5", "under15"),
            ("Over 1.75", "over175"), ("Under 1.75", "under175"),
            ("Over 2.0", "over20"), ("Under 2.0", "under20"),
            ("Over 2.25", "over225"), ("Under 2.25", "under225"),
            ("Over 2.5", "over25"), ("Under 2.5", "under25"),
            ("Over 2.75", "over275"), ("Under 2.75", "under275"),
            ("Over 3.0", "over30"), ("Under 3.0", "under30"),
            ("Over 3.25", "over325"), ("Under 3.25", "under325"),
            ("Over 3.5", "over35"), ("Under 3.5", "under35"),
            ("BTTS Sim", "btts"), ("BTTS Não", "btts_no"),
        ]
        for label, name in odds_fields:
            default_value = 2.0 if name == "over25" else -1.0
            self.add_spinbox(odd_layout, f"Odd Casa ({label}):", f"odd_{name}", -1.0, 10.0, default_value)

        self.odd_group.setLayout(odd_layout)
        aba_odds_layout.addWidget(self.odd_group)
        aba_odds_layout.addStretch()
        aba_odds.setLayout(aba_odds_layout)
        self.tabs.addTab(aba_odds, "Comparativo de Odds")

        self.setLayout(main_layout)
        self.update_tab_styles()

    def update_tab_styles(self):
        if self.dark_mode:
            self.tabs.setStyleSheet(
                "QTabBar::tab { color: #ffffff; background-color: #333333; padding: 8px; } "
                "QTabBar::tab:selected { background-color: #555555; }"
            )
        else:
            self.tabs.setStyleSheet(
                "QTabBar::tab { color: #000000; background-color: #f0f0f0; padding: 8px; } "
                "QTabBar::tab:selected { background-color: #ffffff; }"
            )

    def alternar_tema(self):
        self.dark_mode = self.toggle_theme.isChecked()
        self.setStyleSheet(get_stylesheet(self.dark_mode))
        self.update_tab_styles()

    def create_team_section(self, title):
        group = QGroupBox(title)
        layout = QVBoxLayout()
        prefix = title.replace(" ", "_").lower()

        basico_group = QGroupBox("Estatísticas Básicas")
        basico_layout = QFormLayout()
        self.add_spinbox(basico_layout, "Média Gols Marcados:", f"{prefix}_media_gols_marcados", 0.0, 5.0, 1.5)
        self.add_spinbox(basico_layout, "Média Gols Sofridos:", f"{prefix}_media_gols_sofridos", 0.0, 5.0, 1.2)
        self.add_spinbox(basico_layout, "PPG:", f"{prefix}_ppg", 0.0, 3.0, 1.0)
        basico_group.setLayout(basico_layout)

        avancado_group = QGroupBox("Métricas Avançadas (xG)")
        avancado_layout = QFormLayout()
        self.add_spinbox(avancado_layout, "xG Ataque:", f"{prefix}_xg_ataque", 0.0, 5.0, 1.5)
        avancado_group.setLayout(avancado_layout)

        contexto_group = QGroupBox("Fatores Contextuais")
        contexto_layout = QFormLayout()
        self.add_spinbox(contexto_layout, "% BTTS Recente:", f"{prefix}_btts_8", 0, 100, 50)
        self.add_spinbox(contexto_layout, "% Over 1.5 Recente:", f"{prefix}_over15_8", 0, 100, 60)
        self.add_spinbox(contexto_layout, "% Over 2.5 Recente:", f"{prefix}_over25_8", 0, 100, 40)
        self.add_spinbox(contexto_layout, "% Over 3.5 Recente:", f"{prefix}_over35_8", 0, 100, 20)
        contexto_group.setLayout(contexto_layout)

        layout.addWidget(basico_group)
        layout.addWidget(avancado_group)
        layout.addWidget(contexto_group)
        group.setLayout(layout)
        return group

    def create_central_section(self):
        self.central_group = QGroupBox("Configurações Gerais")
        layout = QVBoxLayout()

        self.toggle_theme = QCheckBox("Modo Escuro")
        self.toggle_theme.setChecked(self.dark_mode)
        self.toggle_theme.stateChanged.connect(self.alternar_tema)
        layout.addWidget(self.toggle_theme)

        linha_layout = QHBoxLayout()
        self.linha_label = QLabel(f"Linha Asiática Atual: {obter_linha_atual()}")
        self.btn_linha_up = QToolButton()
        self.btn_linha_up.setArrowType(Qt.UpArrow)
        self.btn_linha_up.clicked.connect(self.incrementar_linha)
        self.btn_linha_down = QToolButton()
        self.btn_linha_down.setArrowType(Qt.DownArrow)
        self.btn_linha_down.clicked.connect(self.decrementar_linha)
        linha_layout.addWidget(self.linha_label)
        linha_layout.addWidget(self.btn_linha_up)
        linha_layout.addWidget(self.btn_linha_down)
        layout.addLayout(linha_layout)

        self.camp_group = QGroupBox("Estatísticas do Campeonato")
        camp_layout = QFormLayout()
        self.add_spinbox(camp_layout, "% BTTS:", "campeonato_btts", 0, 100, 45)
        self.add_spinbox(camp_layout, "% Over 1.5:", "campeonato_over15", 0, 100, 70)
        self.add_spinbox(camp_layout, "% Over 2.5:", "campeonato_over25", 0, 100, 50)
        self.add_spinbox(camp_layout, "% Over 3.5:", "campeonato_over35", 0, 100, 25)
        self.camp_group.setLayout(camp_layout)

        self.confronto_group = QGroupBox("Histórico de Confrontos")
        confronto_layout = QFormLayout()
        self.add_spinbox(confronto_layout, "Jogos Analisados:", "confronto_jogos", 0, 50, 8)
        self.add_spinbox(confronto_layout, "% Over 1.5:", "confronto_over15", 0, 100, 70)
        self.add_spinbox(confronto_layout, "% Over 2.5:", "confronto_over25", 0, 100, 50)
        self.add_spinbox(confronto_layout, "% Over 3.5:", "confronto_over35", 0, 100, 25)
        self.add_spinbox(confronto_layout, "% BTTS:", "confronto_btts", 0, 100, 50)
        self.confronto_group.setLayout(confronto_layout)

        button_layout = QHBoxLayout()
        self.btn_paste_team = QPushButton("Paste Team Stats")
        self.btn_paste_team.clicked.connect(self.paste_team_stats)
        self.btn_paste_ppg = QPushButton("Paste PPG")
        self.btn_paste_ppg.clicked.connect(self.paste_ppg)
        self.btn_paste_champ = QPushButton("Paste Championship Stats")
        self.btn_paste_champ.clicked.connect(self.paste_championship_stats)
        self.btn_paste_h2h = QPushButton("Paste H2H")
        self.btn_paste_h2h.clicked.connect(self.paste_h2h_stats)
        self.btn_paste_odds = QPushButton("Paste Odds")
        self.btn_paste_odds.clicked.connect(self.paste_odds)
        self.btn_calcular = QPushButton("Calcular Probabilidades")
        self.btn_calcular.clicked.connect(self.calcular_odds)
        button_layout.addWidget(self.btn_paste_team)
        button_layout.addWidget(self.btn_paste_ppg)
        button_layout.addWidget(self.btn_paste_champ)
        button_layout.addWidget(self.btn_paste_h2h)
        button_layout.addWidget(self.btn_paste_odds)
        button_layout.addWidget(self.btn_calcular)

        resultados_layout = QHBoxLayout()
        self.resultados = QTextEdit()
        self.resultados.setReadOnly(True)
        self.resultados.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.resultados.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        resultados_layout.addWidget(self.resultados, stretch=3)

        lists_layout = QVBoxLayout()
        self.ev_positivo_list = QListWidget()
        self.ev_positivo_list.setMaximumWidth(300)
        self.ev_positivo_list.setMinimumHeight(150)
        self.ev_positivo_list.itemClicked.connect(self.on_ev_item_clicked)
        self.ev_positivo_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ev_positivo_list.customContextMenuRequested.connect(self.show_context_menu)
        lists_layout.addWidget(self.ev_positivo_list)

        self.main_lines_list = QListWidget()
        self.main_lines_list.setMaximumWidth(300)
        self.main_lines_list.setMinimumHeight(150)
        self.main_lines_list.itemClicked.connect(self.on_ev_item_clicked)
        lists_layout.addWidget(self.main_lines_list)

        resultados_layout.addLayout(lists_layout, stretch=1)

        layout.addWidget(self.camp_group)
        layout.addWidget(self.confronto_group)
        layout.addLayout(button_layout)
        layout.addLayout(resultados_layout)

        self.central_group.setLayout(layout)
        return self.central_group

    def create_handicap_section(self):
        layout = QVBoxLayout()
        title = QLabel("<b>Calculadora de Handicap Asiático e Placares Prováveis</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        input_group = QGroupBox("Entradas")
        input_layout = QHBoxLayout()

        mandante_layout = QVBoxLayout()
        mandante_group = QGroupBox("Time Mandante")
        mandante_form = QFormLayout()
        self.add_spinbox(mandante_form, "Média Gols Marcados:", "handicap_mandante_media_gols_marcados", 0.0, 10.0, 1.5)
        self.add_spinbox(mandante_form, "Média Gols Sofridos:", "handicap_mandante_media_gols_sofridos", 0.0, 10.0, 1.2)
        self.add_spinbox(mandante_form, "PPG:", "handicap_mandante_ppg", 0.0, 3.0, 1.0)
        self.add_spinbox(mandante_form, "xG Ataque:", "handicap_mandante_xg_ataque", 0.0, 10.0, 1.5)
        mandante_group.setLayout(mandante_form)
        mandante_layout.addWidget(mandante_group)
        input_layout.addLayout(mandante_layout)

        visitante_layout = QVBoxLayout()
        visitante_group = QGroupBox("Time Visitante")
        visitante_form = QFormLayout()
        self.add_spinbox(visitante_form, "Média Gols Marcados:", "handicap_visitante_media_gols_marcados", 0.0, 10.0, 1.3)
        self.add_spinbox(visitante_form, "Média Gols Sofridos:", "handicap_visitante_media_gols_sofridos", 0.0, 10.0, 1.4)
        self.add_spinbox(visitante_form, "PPG:", "handicap_visitante_ppg", 0.0, 3.0, 1.0)
        self.add_spinbox(visitante_form, "xG Ataque:", "handicap_visitante_xg_ataque", 0.0, 10.0, 1.3)
        visitante_group.setLayout(visitante_form)
        visitante_layout.addWidget(visitante_group)
        input_layout.addLayout(visitante_layout)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        handicap_layout = QHBoxLayout()
        handicap_lbl = QLabel("Handicap Asiático (Mandante):")
        self.handicap_spin = QDoubleSpinBox()
        self.handicap_spin.setRange(-2.5, 2.5)
        self.handicap_spin.setSingleStep(0.25)
        self.handicap_spin.setDecimals(2)
        self.handicap_spin.setValue(-0.5)
        handicap_layout.addWidget(handicap_lbl)
        handicap_layout.addWidget(self.handicap_spin)
        layout.addLayout(handicap_layout)

        self.calcular_handicap_button = QPushButton("Calcular Handicap e Placares")
        self.calcular_handicap_button.clicked.connect(self.calcular_handicap_e_placares)
        layout.addWidget(self.calcular_handicap_button)

        self.btn_copiar_principal = QPushButton("Copiar Dados da Aba Principal")
        self.btn_copiar_principal.clicked.connect(self.copiar_dados_principal)
        layout.addWidget(self.btn_copiar_principal)

        self.resultado_handicap_textedit = QTextEdit()
        self.resultado_handicap_textedit.setReadOnly(True)
        self.resultado_handicap_textedit.setAlignment(Qt.AlignCenter)
        self.resultado_handicap_textedit.setPlainText("Resultados do Handicap Asiático e Placares Prováveis")
        layout.addWidget(self.resultado_handicap_textedit)

        return layout

    def add_spinbox(self, layout, label, name, min_val, max_val, default=0):
        spin = QDoubleSpinBox()
        spin.setObjectName(name)
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(0.1 if max_val <= 5 else 1)
        layout.addRow(QLabel(label), spin)
        return spin

    def update_spinbox(self, spinbox, value, campo, origem):
        """Atualiza o valor do spinbox e os valores brutos."""
        spinbox.setValue(value)
        if origem.startswith('handicap_'):
            if campo in ['media_gols_marcados', 'media_gols_sofridos', 'ppg']:
                self.valores_brutos[origem][campo] = value
        else:
            if campo in ['media_gols_marcados', 'media_gols_sofridos', 'ppg']:
                self.valores_brutos[origem][campo] = value
                self.valores_brutos[f'handicap_{origem}'][campo] = value

    def connect_spinboxes(self):
        campos = [
            ('media_gols_marcados', 'media_gols_marcados'),
            ('media_gols_sofridos', 'media_gols_sofridos'),
            ('xg_ataque', 'xg_ataque'),
            ('ppg', 'ppg'),
        ]

        for campo_principal, campo_handicap in campos:
            spin_principal = self.mandante_group.findChild(QDoubleSpinBox, f"time_mandante_{campo_principal}")
            spin_handicap = self.findChild(QDoubleSpinBox, f"handicap_mandante_{campo_handicap}")
            if spin_principal and spin_handicap:
                spin_principal.valueChanged.connect(
                    lambda value, s=spin_handicap, c=campo_principal: self.update_spinbox(s, value, c, 'mandante')
                )
                spin_handicap.valueChanged.connect(
                    lambda value, s=spin_principal, c=campo_principal: self.update_spinbox(s, value, c, 'handicap_mandante')
                )

            spin_principal = self.visitante_group.findChild(QDoubleSpinBox, f"time_visitante_{campo_principal}")
            spin_handicap = self.findChild(QDoubleSpinBox, f"handicap_visitante_{campo_handicap}")
            if spin_principal and spin_handicap:
                spin_principal.valueChanged.connect(
                    lambda value, s=spin_handicap, c=campo_principal: self.update_spinbox(s, value, c, 'visitante')
                )
                spin_handicap.valueChanged.connect(
                    lambda value, s=spin_principal, c=campo_principal: self.update_spinbox(s, value, c, 'handicap_visitante')
                )

    def incrementar_linha(self):
        ciclo_linha_asiatica()
        self.linha_label.setText(f"Linha Asiática Atual: {obter_linha_atual()}")
        self.calcular_odds()

    def decrementar_linha(self):
        ciclo_linha_asiatica_para_baixo()
        self.linha_label.setText(f"Linha Asiática Atual: {obter_linha_atual()}")
        self.calcular_odds()

    def on_ev_item_clicked(self, item):
        linha = item.data(Qt.UserRole)
        if linha is not None:
            definir_linha_atual(linha)
            self.linha_label.setText(f"Linha Asiática Atual: {linha}")
            self.calcular_odds()
        else:
            self.resultados.setHtml(f"<span style='color: #00ff00;'>Item selecionado: {item.text()}</span>")

    def show_context_menu(self, position):
        menu = QMenu()
        copy_action = menu.addAction("Copiar")
        sort_ev_asc = menu.addAction("Ordenar por EV (Menor → Maior)")
        sort_ev_desc = menu.addAction("Ordenar por EV (Maior → Menor)")
        sort_odd_asc = menu.addAction("Ordenar por Odd Casa (Menor → Maior)")
        sort_odd_desc = menu.addAction("Ordenar por Odd Casa (Maior → Menor)")
        action = menu.exec_(self.ev_positivo_list.mapToGlobal(position))
        if action == copy_action:
            selected_item = self.ev_positivo_list.currentItem()
            if selected_item:
                QApplication.clipboard().setText(selected_item.text())
        elif action == sort_ev_asc:
            self.sort_ev_list(ascending=True)
        elif action == sort_ev_desc:
            self.sort_ev_list(ascending=False)
        elif action == sort_odd_asc:
            self.sort_odd_list(ascending=True)
        elif action == sort_odd_desc:
            self.sort_odd_list(ascending=False)

    def sort_ev_list(self, ascending=True):
        items = []
        for i in range(self.ev_positivo_list.count()):
            item = self.ev_positivo_list.item(i)
            ev = float(item.text().split("EV: ")[1].split("%")[0])
            linha = item.data(Qt.UserRole)
            odd = item.data(Qt.UserRole + 1)
            cor = item.foreground().color().name()
            items.append((ev, odd, linha, cor, item.text()))

        items.sort(key=lambda x: x[0], reverse=not ascending)
        self.ev_positivo_list.clear()
        for _, odd, linha, cor, text in items:
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, linha)
            item.setData(Qt.UserRole + 1, odd)
            item.setForeground(QtGui.QColor(cor))
            self.ev_positivo_list.addItem(item)

    def sort_odd_list(self, ascending=True):
        items = []
        for i in range(self.ev_positivo_list.count()):
            item = self.ev_positivo_list.item(i)
            ev = float(item.text().split("EV: ")[1].split("%")[0])
            linha = item.data(Qt.UserRole)
            odd = item.data(Qt.UserRole + 1)
            cor = item.foreground().color().name()
            items.append((ev, odd, linha, cor, item.text()))

        items.sort(key=lambda x: x[1], reverse=not ascending)
        self.ev_positivo_list.clear()
        for _, odd, linha, cor, text in items:
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, linha)
            item.setData(Qt.UserRole + 1, odd)
            item.setForeground(QtGui.QColor(cor))
            self.ev_positivo_list.addItem(item)

    def save_state(self):
        odds_names = []
        for l in LINHAS_GUI:
            odds_names.append(_odd_key_over(l))
            odds_names.append(_odd_key_under(l))
        odds_names += ["btts", "btts_no"]

        state = {
            'mandante': {key: self.mandante_group.findChild(QDoubleSpinBox, f"time_mandante_{key}").value()
                         for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg',
                                     'btts_8', 'over15_8', 'over25_8', 'over35_8']},
            'visitante': {key: self.visitante_group.findChild(QDoubleSpinBox, f"time_visitante_{key}").value()
                          for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg',
                                      'btts_8', 'over15_8', 'over25_8', 'over35_8']},
            'campeonato': {key: self.camp_group.findChild(QDoubleSpinBox, f"campeonato_{key}").value()
                           for key in ['btts', 'over15', 'over25', 'over35']},
            'confronto': {key: self.confronto_group.findChild(QDoubleSpinBox, f"confronto_{key}").value()
                          for key in ['jogos', 'over15', 'over25', 'over35', 'btts']},
            'odds': {},
            'handicap': {
                'mandante': {key: self.findChild(QDoubleSpinBox, f"handicap_mandante_{key}").value()
                             for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg']},
                'visitante': {key: self.findChild(QDoubleSpinBox, f"handicap_visitante_{key}").value()
                              for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg']},
                'handicap_value': self.handicap_spin.value()
            },
            'valores_brutos': self.valores_brutos.copy()
        }

        for name in odds_names:
            spinbox = self.odd_group.findChild(QDoubleSpinBox, f"odd_{name}")
            if spinbox:
                state['odds'][name] = spinbox.value()

        self.undo_stack.append(state)

    def undo_last_action(self):
        if not self.undo_stack:
            self.resultados.setHtml("<span style='color: #ff0000;'>Nenhuma ação para desfazer!</span>")
            self.resultado_handicap_textedit.setHtml("<span style='color: #ff0000;'>Nenhuma ação para desfazer!</span>")
            return

        state = self.undo_stack.pop()
        try:
            # ✅ Corrigido: cada time volta para o grupo certo
            for key, value in state['mandante'].items():
                spinbox = self.mandante_group.findChild(QDoubleSpinBox, f"time_mandante_{key}")
                if spinbox:
                    spinbox.setValue(value)
            for key, value in state['visitante'].items():
                spinbox = self.visitante_group.findChild(QDoubleSpinBox, f"time_visitante_{key}")
                if spinbox:
                    spinbox.setValue(value)

            for key, value in state['campeonato'].items():
                spinbox = self.camp_group.findChild(QDoubleSpinBox, f"campeonato_{key}")
                if spinbox:
                    spinbox.setValue(value)

            for key, value in state['confronto'].items():
                spinbox = self.confronto_group.findChild(QDoubleSpinBox, f"confronto_{key}")
                if spinbox:
                    spinbox.setValue(value)

            for key, value in state['odds'].items():
                spinbox = self.odd_group.findChild(QDoubleSpinBox, f"odd_{key}")
                if spinbox:
                    spinbox.setValue(value)

            for team in ['mandante', 'visitante']:
                for key, value in state['handicap'][team].items():
                    spinbox = self.findChild(QDoubleSpinBox, f"handicap_{team}_{key}")
                    if spinbox:
                        spinbox.setValue(value)

            self.handicap_spin.setValue(state['handicap']['handicap_value'])
            self.valores_brutos = state['valores_brutos'].copy()

            self.resultados.setHtml("<span style='color: #00ff00;'>Última ação desfeita!</span>")
            self.resultado_handicap_textedit.setHtml("<span style='color: #00ff00;'>Última ação desfeita!</span>")
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao desfazer ação: {str(e)}</span>")
            self.resultado_handicap_textedit.setHtml(f"<span style='color: #ff0000;'>Erro ao desfazer ação: {str(e)}</span>")

    def paste_team_stats(self):
        self.save_state()
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text.strip():
                raise ValueError("Área de transferência vazia")
            dados = self.parse_team_stats(text)

            for team in ['mandante', 'visitante']:
                prefix = f"time_{team}"
                for key, value in dados[team].items():
                    spinbox = self.findChild(QDoubleSpinBox, f"{prefix}_{key}")
                    if spinbox:
                        spinbox.setValue(value)
                        if key in ['media_gols_marcados', 'media_gols_sofridos', 'ppg']:
                            self.valores_brutos[team][key] = value
                            self.valores_brutos[f"handicap_{team}"][key] = value

            self.resultados.setHtml("<span style='color: #00ff00;'>Estatísticas dos times coladas com sucesso!</span>")
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao colar estatísticas dos times: {str(e)}</span>")

    def paste_ppg(self):
        self.save_state()
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text.strip():
                raise ValueError("Área de transferência vazia")
            dados = self.parse_ppg(text)

            for team in ['mandante', 'visitante']:
                if 'ppg' in dados[team]:
                    spinbox = self.findChild(QDoubleSpinBox, f"time_{team}_ppg")
                    if spinbox:
                        spinbox.setValue(dados[team]['ppg'])
                        self.valores_brutos[team]['ppg'] = dados[team]['ppg']
                        self.valores_brutos[f"handicap_{team}"]['ppg'] = dados[team]['ppg']

            self.resultados.setHtml("<span style='color: #00ff00;'>PPG colado com sucesso!</span>")
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao colar PPG: {str(e)}</span>")

    def paste_championship_stats(self):
        self.save_state()
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text.strip():
                raise ValueError("Área de transferência vazia")
            dados = self.parse_championship_stats(text)

            for key, value in dados['campeonato'].items():
                spinbox = self.camp_group.findChild(QDoubleSpinBox, f"campeonato_{key}")
                if spinbox:
                    spinbox.setValue(value)

            self.resultados.setHtml("<span style='color: #00ff00;'>Estatísticas do campeonato coladas com sucesso!</span>")
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao colar estatísticas do campeonato: {str(e)}</span>")

    def paste_h2h_stats(self):
        self.save_state()
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            if not text.strip():
                raise ValueError("Área de transferência vazia")
            dados = self.parse_h2h_stats(text)

            for key, value in dados['confronto'].items():
                spinbox = self.confronto_group.findChild(QDoubleSpinBox, f"confronto_{key}")
                if spinbox:
                    spinbox.setValue(value)

            self.resultados.setHtml("<span style='color: #00ff00;'>Estatísticas H2H coladas com sucesso!</span>")
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao colar estatísticas H2H: {str(e)}</span>")

    def paste_odds(self):
        try:
            self.save_state()
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            dados = self.parse_odds(text)

            # ✅ Reseta APENAS as odds até 3.5 (e BTTS)
            reset_keys = []
            for l in LINHAS_GUI:
                reset_keys.append(_odd_key_over(l))
                reset_keys.append(_odd_key_under(l))
            reset_keys += ['btts', 'btts_no']

            for key in reset_keys:
                spinbox = self.odd_group.findChild(QDoubleSpinBox, f"odd_{key}")
                if spinbox:
                    spinbox.setValue(-1.0)

            atualizados = []
            for key, value in dados['odds'].items():
                spinbox = self.odd_group.findChild(QDoubleSpinBox, f"odd_{key}")
                if spinbox:
                    spinbox.setValue(value)
                    atualizados.append(f"{key}: {value}")
                else:
                    print(f"Campo 'odd_{key}' não encontrado na interface.")

            if atualizados:
                self.resultados.setPlainText("Odds coladas com sucesso!\n" + "\n".join(atualizados))
            else:
                self.resultados.setPlainText("Nenhuma odd válida encontrada no texto colado.")
        except Exception as e:
            self.resultados.setPlainText(f"Erro ao colar odds: {str(e)}")

    def copiar_dados_principal(self):
        self.save_state()
        try:
            dados = self.coletar_dados()

            for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg']:
                src_key = key if key not in ['media_gols_marcados', 'media_gols_sofridos'] else (
                    'media_gols' if key == 'media_gols_marcados' else 'media_sofridos')
                spinbox = self.findChild(QDoubleSpinBox, f"handicap_mandante_{key}")
                if spinbox:
                    spinbox.setValue(dados['mandante'][src_key])
                    if key in ['media_gols_marcados', 'media_gols_sofridos', 'ppg']:
                        self.valores_brutos['handicap_mandante'][key] = dados['mandante'][src_key]

            for key in ['media_gols_marcados', 'media_gols_sofridos', 'xg_ataque', 'ppg']:
                src_key = key if key not in ['media_gols_marcados', 'media_gols_sofridos'] else (
                    'media_gols' if key == 'media_gols_marcados' else 'media_sofridos')
                spinbox = self.findChild(QDoubleSpinBox, f"handicap_visitante_{key}")
                if spinbox:
                    spinbox.setValue(dados['visitante'][src_key])
                    if key in ['media_gols_marcados', 'media_gols_sofridos', 'ppg']:
                        self.valores_brutos['handicap_visitante'][key] = dados['visitante'][src_key]

            self.resultado_handicap_textedit.setHtml("<span style='color: #00ff00;'>Dados copiados da aba Principal com sucesso!</span>")
        except Exception as e:
            self.resultado_handicap_textedit.setHtml(f"<span style='color: #ff0000;'>Erro ao copiar dados: {str(e)}</span>")

    def calcular_handicap_e_placares(self):
        self.save_state()
        try:
            dados = self.coletar_dados_handicap()
            handicap = self.handicap_spin.value()
            resultado = calcular_odds_completas(dados, handicap=handicap)

            mandante_result = resultado['handicap']['mandante']
            visitante_result = resultado['handicap']['visitante']
            handicap_value = resultado['handicap']['handicap']
            placares = resultado['placares_provaveis']

            texto = (
                f"<h3>Handicap Asiático (Mandante {handicap_value:+.2f})</h3>"
                f"<p><b>Time Mandante:</b><br>"
                f"  - Prob. de Vitória: {mandante_result['prob_vitoria'] * 100:.2f}%<br>"
                f"  - Prob. de Reembolso: {mandante_result['prob_reembolso'] * 100:.2f}%<br>"
                f"  - Prob. de Derrota: {mandante_result['prob_derrota'] * 100:.2f}%<br>"
                f"  - Odd Justa: {mandante_result['odd']:.2f}</p>"
                f"<p><b>Time Visitante (Handicap {(-handicap_value):+.2f}):</b><br>"
                f"  - Prob. de Vitória: {visitante_result['prob_vitoria'] * 100:.2f}%<br>"
                f"  - Prob. de Reembolso: {visitante_result['prob_reembolso'] * 100:.2f}%<br>"
                f"  - Prob. de Derrota: {visitante_result['prob_derrota'] * 100:.2f}%<br>"
                f"  - Odd Justa: {visitante_result['odd']:.2f}</p>"
                f"<h3>Placares Mais Prováveis</h3>"
            )

            for i, placar in enumerate(placares, 1):
                texto += f"<p>{i}. {placar['placar']} - Probabilidade: {placar['probabilidade'] * 100:.2f}%</p>"

            self.resultado_handicap_textedit.setHtml(texto)
        except Exception as e:
            self.resultado_handicap_textedit.setHtml(f"<span style='color: #ff0000;'>Erro ao calcular: {str(e)}</span>")

    def coletar_dados(self):
        return {
            'mandante': {
                'media_gols': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_media_gols_marcados").value(),
                'media_sofridos': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_media_gols_sofridos").value(),
                'ppg': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_ppg").value(),
                'xg_ataque': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_xg_ataque").value(),
                'btts_8': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_btts_8").value() / 100,
                'over15_8': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_over15_8").value() / 100,
                'over25_8': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_over25_8").value() / 100,
                'over35_8': self.mandante_group.findChild(QDoubleSpinBox, "time_mandante_over35_8").value() / 100,
            },
            'visitante': {
                'media_gols': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_media_gols_marcados").value(),
                'media_sofridos': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_media_gols_sofridos").value(),
                'ppg': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_ppg").value(),
                'xg_ataque': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_xg_ataque").value(),
                'btts_8': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_btts_8").value() / 100,
                'over15_8': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_over15_8").value() / 100,
                'over25_8': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_over25_8").value() / 100,
                'over35_8': self.visitante_group.findChild(QDoubleSpinBox, "time_visitante_over35_8").value() / 100,
            },
            'campeonato': {
                'btts': self.camp_group.findChild(QDoubleSpinBox, "campeonato_btts").value() / 100,
                'over15': self.camp_group.findChild(QDoubleSpinBox, "campeonato_over15").value() / 100,
                'over25': self.camp_group.findChild(QDoubleSpinBox, "campeonato_over25").value() / 100,
                'over35': self.camp_group.findChild(QDoubleSpinBox, "campeonato_over35").value() / 100,
            },
            'confronto': {
                'jogos': self.confronto_group.findChild(QDoubleSpinBox, "confronto_jogos").value(),
                'over15': self.confronto_group.findChild(QDoubleSpinBox, "confronto_over15").value() / 100,
                'over25': self.confronto_group.findChild(QDoubleSpinBox, "confronto_over25").value() / 100,
                'over35': self.confronto_group.findChild(QDoubleSpinBox, "confronto_over35").value() / 100,
                'btts': self.confronto_group.findChild(QDoubleSpinBox, "confronto_btts").value() / 100,
            },
        }

    def coletar_dados_handicap(self):
        dados = self.coletar_dados()
        dados['mandante'].update({
            'media_gols': self.findChild(QDoubleSpinBox, "handicap_mandante_media_gols_marcados").value(),
            'media_sofridos': self.findChild(QDoubleSpinBox, "handicap_mandante_media_gols_sofridos").value(),
            'xg_ataque': self.findChild(QDoubleSpinBox, "handicap_mandante_xg_ataque").value(),
            'ppg': self.findChild(QDoubleSpinBox, "handicap_mandante_ppg").value(),
        })
        dados['visitante'].update({
            'media_gols': self.findChild(QDoubleSpinBox, "handicap_visitante_media_gols_marcados").value(),
            'media_sofridos': self.findChild(QDoubleSpinBox, "handicap_visitante_media_gols_sofridos").value(),
            'xg_ataque': self.findChild(QDoubleSpinBox, "handicap_visitante_xg_ataque").value(),
            'ppg': self.findChild(QDoubleSpinBox, "handicap_visitante_ppg").value(),
        })
        for team in ['mandante', 'visitante']:
            for key in ['btts_8', 'over15_8', 'over25_8', 'over35_8']:
                if key not in dados[team]:
                    dados[team][key] = 0.5
        return dados

    def parse_ppg(self, text):
        lines = text.strip().split('\n')
        dados = {'mandante': {}, 'visitante': {}}
        ppg_regex = re.compile(r'(\d+\.\d+)\s+PPG')
        team_index = 0
        for line in lines:
            line = line.strip()
            ppg_match = ppg_regex.search(line)
            if ppg_match:
                ppg_value = float(ppg_match.group(1))
                if team_index == 0:
                    dados['mandante']['ppg'] = ppg_value
                    team_index += 1
                elif team_index == 1:
                    dados['visitante']['ppg'] = ppg_value
                    break
        return dados

    def parse_team_stats(self, text):
        lines = text.strip().split('\n')
        dados = {'mandante': {}, 'visitante': {}}

        patterns = {
            'media_gols_marcados': re.compile(r'([\d.]+)\s+Avg\. Scored\s+([\d.]+)', re.IGNORECASE),
            'media_gols_sofridos': re.compile(r'([\d.]+)\s+Avg\. Suffer\s+([\d.]+)', re.IGNORECASE),
            'ppg': re.compile(r'([\d.]+)\s+PPG\s+([\d.]+)', re.IGNORECASE),
            'btts_8': re.compile(r'(\d+)%\s+BTTS\s+(\d+)%', re.IGNORECASE),
            'over15_8': re.compile(r'Over 1\.5\s+(\d+)%\s+(\d+)%', re.IGNORECASE),
            'over25_8': re.compile(r'Over 2\.5\s+(\d+)%\s+(\d+)%', re.IGNORECASE),
            'over35_8': re.compile(r'Over 3\.5\s+(\d+)%\s+(\d+)%', re.IGNORECASE),
        }

        for line in lines:
            for key, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    mandante_val = float(match.group(1))
                    visitante_val = float(match.group(2))
                    dados['mandante'][key] = mandante_val
                    dados['visitante'][key] = visitante_val

        for team in ['mandante', 'visitante']:
            dados[team]['media_gols_marcados'] = dados[team].get('media_gols_marcados', 1.5)
            dados[team]['media_gols_sofridos'] = dados[team].get('media_gols_sofridos', 1.2)
            dados[team]['ppg'] = dados[team].get('ppg', 1.0)
            dados[team]['xg_ataque'] = dados[team].get('xg_ataque', dados[team]['media_gols_marcados'])
            dados[team]['btts_8'] = dados[team].get('btts_8', 50.0)
            dados[team]['over15_8'] = dados[team].get('over15_8', 60.0)
            dados[team]['over25_8'] = dados[team].get('over25_8', 40.0)
            dados[team]['over35_8'] = dados[team].get('over35_8', 20.0)

        return dados

    def parse_championship_stats(self, text):
        lines = text.strip().split('\n')
        dados = {'campeonato': {}}

        mapping = {
            'Over 1.5FT': 'over15',
            'Over 2.5FT': 'over25',
            'BTTS - Yes': 'btts',
        }

        for line in lines[1:]:
            parts = line.split('\t')
            if len(parts) != 2:
                continue
            label, value = parts
            try:
                value = float(value.replace('%', ''))
                if label in mapping:
                    dados['campeonato'][mapping[label]] = value
            except ValueError:
                continue

        defaults = {'btts': 50.0, 'over15': 70.0, 'over25': 50.0, 'over35': 25.0}
        for key, value in defaults.items():
            if key not in dados['campeonato']:
                dados['campeonato'][key] = value

        return dados

    def parse_h2h_stats(self, text):
        lines = text.strip().split('\n')
        dados = {'confronto': {'jogos': 0, 'over15': 0.0, 'over25': 0.0, 'over35': 0.0, 'btts': 0.0}}

        jogos, over_15, over_25, over_35, btts = 0, 0, 0, 0, 0
        for line in lines:
            parts = line.split('\t')
            if len(parts) < 5:
                continue
            placar_str = parts[3]
            try:
                placar = placar_str.split(' ')[0]
                gols_time1, gols_time2 = map(int, placar.split('-'))
                total_gols = gols_time1 + gols_time2
                jogos += 1
                if total_gols > 1:
                    over_15 += 1
                if total_gols > 2:
                    over_25 += 1
                if total_gols > 3:
                    over_35 += 1
                if gols_time1 > 0 and gols_time2 > 0:
                    btts += 1
            except (ValueError, IndexError):
                continue

        if jogos > 0:
            dados['confronto'] = {
                'jogos': jogos,
                'over15': (over_15 / jogos) * 100,
                'over25': (over_25 / jogos) * 100,
                'over35': (over_35 / jogos) * 100,
                'btts': (btts / jogos) * 100
            }

        return dados

    def parse_odds(self, text):
        """
        ✅ Agora parseia apenas 0.5 até 3.5 (e BTTS).
        Deixa mais robusto para o bloco "Odds Market" do FootyStats.
        """
        lines = text.strip().split('\n')
        dados = {'odds': {}}

        # Fallback (formato "rótulo em uma linha" + "valor na próxima")
        mapping_odds = {
            'Over 0.5': 'over05', 'Under 0.5': 'under05',
            'Over 0.75': 'over075', 'Under 0.75': 'under075',
            'Over 1.0': 'over10', 'Under 1.0': 'under10',
            'Over 1.25': 'over125', 'Under 1.25': 'under125',
            'Over 1.50': 'over15', 'Under 1.50': 'under15',
            'Over 1.75': 'over175', 'Under 1.75': 'under175',
            'Over 2.00': 'over20', 'Under 2.00': 'under20',
            'Over 2.25': 'over225', 'Under 2.25': 'under225',
            'Over 2.50': 'over25', 'Under 2.50': 'under25',
            'Over 2.75': 'over275', 'Under 2.75': 'under275',
            'Over 3.00': 'over30', 'Under 3.00': 'under30',
            'Over 3.25': 'over325', 'Under 3.25': 'under325',
            'Over 3.50': 'over35', 'Under 3.50': 'under35',
            'Yes': 'btts', 'No': 'btts_no',
        }

        i = 0
        odds_section = False
        while i < len(lines):
            line = lines[i].strip()

            if "Odds Market" in line:
                odds_section = True
                i += 1
                continue

            # Formato FootyStats: "Over 2.5 1.87"
            if odds_section and len(line.split()) >= 2:
                parts = line.split()
                market = " ".join(parts[:-1])
                try:
                    valor = float(parts[-1])

                    if market in ("Yes", "No"):
                        dados['odds']['btts' if market == "Yes" else 'btts_no'] = valor
                        i += 1
                        continue

                    if market.startswith("Over ") or market.startswith("Under "):
                        try:
                            num = float(market.split()[1])
                        except (ValueError, IndexError):
                            i += 1
                            continue

                        if 0.5 <= num <= 3.5:
                            key = _odd_key_over(num) if market.startswith("Over") else _odd_key_under(num)
                            dados['odds'][key] = valor

                    i += 1
                    continue
                except (ValueError, IndexError):
                    i += 1
                    continue

            # Formato alternativo: linha com "Over 2.50" e na próxima a odd
            if line in mapping_odds:
                try:
                    valor = float(lines[i + 1].strip())
                    campo = mapping_odds[line]
                    dados['odds'][campo] = valor
                    i += 2
                    continue
                except (ValueError, IndexError):
                    i += 1
                    continue

            i += 1

        return dados

    def get_gestao_banca(self, ev):
        if ev < 5:
            return ("❌ No Value Bet", 0, "red")
        elif 5 <= ev < 8:
            return ("✅ Value Bet (Small 1)", 0.5, "#B8860B")
        elif 8 <= ev < 12:
            return ("✅ Value Bet (Small 2)", 1.0, "#B8860B")
        elif 12 <= ev < 16:
            return ("✅ Value Bet (Medium 1)", 1.5, "#4682B4")
        elif 16 <= ev < 20:
            return ("✅ Value Bet (Medium 2)", 2.0, "#4682B4")
        elif 20 <= ev < 27:
            return ("✅ Value Bet (Big 1)", 2.5, "green")
        else:
            return ("✅ Value Bet (Big 2)", 3.0, "green")

    def calcular_odds(self):
        self.save_state()
        try:
            dados = self.coletar_dados()
            self._executar_calculo_odds(dados)
        except Exception as e:
            self.resultados.setHtml(f"<span style='color: #ff0000;'>Erro ao calcular odds: {str(e)}</span>")

    def _executar_calculo_odds(self, dados):
        odds = calcular_odds_completas(dados)

        odd_casa_over25 = self.odd_group.findChild(QDoubleSpinBox, "odd_over25").value()
        odd_casa_under25 = self.odd_group.findChild(QDoubleSpinBox, "odd_under25").value()
        odd_casa_btts = self.odd_group.findChild(QDoubleSpinBox, "odd_btts").value()
        odd_casa_btts_no = self.odd_group.findChild(QDoubleSpinBox, "odd_btts_no").value()

        # ✅ Só de 0.5 até 3.5
        mapping_linhas = {}
        for linha in LINHAS_GUI:
            over_field = f"odd_{_odd_key_over(linha)}"
            under_field = f"odd_{_odd_key_under(linha)}"
            mapping_linhas[linha] = (over_field, under_field)

        evs_linhas = {}
        lambda_m, lambda_v = calcular_lambdas(dados)

        for linha in mapping_linhas:
            over_field, under_field = mapping_linhas[linha]
            odd_casa_linha_over = self.odd_group.findChild(QDoubleSpinBox, over_field).value()
            odd_casa_linha_under = self.odd_group.findChild(QDoubleSpinBox, under_field).value()

            prob_over = calcular_linha_asiatica(dados, lambda_m, lambda_v, linha)
            prob_under = 1 - prob_over
            ev_over = ((odd_casa_linha_over * prob_over) - 1) * 100 if odd_casa_linha_over > 0 else 0.0
            ev_under = ((odd_casa_linha_under * prob_under) - 1) * 100 if odd_casa_linha_under > 0 else 0.0

            evs_linhas[linha] = {
                'over': ev_over, 'under': ev_under,
                'odd_casa_over': odd_casa_linha_over,
                'odd_casa_under': odd_casa_linha_under,
                'prob_over': prob_over * 100,
                'prob_under': prob_under * 100
            }

        linha_atual = obter_linha_atual()
        if linha_atual in mapping_linhas:
            over_field, under_field = mapping_linhas[linha_atual]
            odd_casa_linha_over = self.odd_group.findChild(QDoubleSpinBox, over_field).value()
            odd_casa_linha_under = self.odd_group.findChild(QDoubleSpinBox, under_field).value()
        else:
            odd_casa_linha_over = self.odd_group.findChild(QDoubleSpinBox, "odd_over25").value()
            odd_casa_linha_under = self.odd_group.findChild(QDoubleSpinBox, "odd_under25").value()

        odds_justas = {
            'over25': odds['over_under']['over25'],
            'btts_sim': odds['btts']['sim'],
            'btts_nao': odds['btts']['nao'],
            'linha_over': odds['linha_asiatica']['over'],
            'linha_under': odds['linha_asiatica']['under'],
            'linha_valor': odds['linha_asiatica']['valor']
        }

        self.exibir_resultados(
            odds_justas, odd_casa_over25, odd_casa_under25, odd_casa_btts, odd_casa_btts_no,
            odd_casa_linha_over, odd_casa_linha_under, evs_linhas
        )

    def exibir_resultados(self, odds_justas, odd_casa_over25, odd_casa_under25, odd_casa_btts, odd_casa_btts_no,
                         odd_casa_linha_over, odd_casa_linha_under, evs_linhas, selected_line=None):

        prob_over25 = 100 / odds_justas['over25'] if odds_justas['over25'] > 0 else 0.0
        prob_under25 = 100 - prob_over25 if prob_over25 > 0 else 0.0
        prob_btts = 100 / odds_justas['btts_sim'] if odds_justas['btts_sim'] > 0 else 0.0
        prob_btts_nao = 100 - prob_btts if prob_btts > 0 else 0.0
        prob_linha_over = 100 / odds_justas['linha_over'] if odds_justas['linha_over'] > 0 else 0.0
        prob_linha_under = 100 - prob_linha_over if prob_linha_over > 0 else 0.0

        ev_over25 = ((odd_casa_over25 * (prob_over25 / 100)) - 1) * 100 if odd_casa_over25 > 0 else 0.0
        ev_under25 = ((odd_casa_under25 * (prob_under25 / 100)) - 1) * 100 if odd_casa_under25 > 0 else 0.0
        ev_btts = ((odd_casa_btts * (prob_btts / 100)) - 1) * 100 if odd_casa_btts > 0 else 0.0
        ev_btts_nao = ((odd_casa_btts_no * (prob_btts_nao / 100)) - 1) * 100 if odd_casa_btts_no > 0 else 0.0
        ev_linha_over = ((odd_casa_linha_over * (prob_linha_over / 100)) - 1) * 100 if odd_casa_linha_over > 0 else 0.0
        ev_linha_under = ((odd_casa_linha_under * (prob_linha_under / 100)) - 1) * 100 if odd_casa_linha_under > 0 else 0.0

        gestao_over25, _, color_over25 = self.get_gestao_banca(ev_over25)
        gestao_under25, _, color_under25 = self.get_gestao_banca(ev_under25)
        gestao_btts, _, color_btts = self.get_gestao_banca(ev_btts)
        gestao_btts_nao, _, color_btts_nao = self.get_gestao_banca(ev_btts_nao)
        gestao_linha_over, _, color_linha_over = self.get_gestao_banca(ev_linha_over)
        gestao_linha_under, _, color_linha_under = self.get_gestao_banca(ev_linha_under)

        odd_justa_over25_exibida = odds_justas['over25']
        odd_justa_under25_exibida = 100 / prob_under25 if prob_under25 > 0 else 100.0
        odd_justa_btts_exibida = odds_justas['btts_sim']
        odd_justa_btts_nao_exibida = odds_justas['btts_nao']
        odd_justa_linha_over_exibida = odds_justas['linha_over']
        odd_justa_linha_under_exibida = odds_justas['linha_under']

        over25_display = f"{odd_casa_over25:.2f}" if odd_casa_over25 > 0 else "No odds found"
        under25_display = f"{odd_casa_under25:.2f}" if odd_casa_under25 > 0 else "No odds found"
        btts_display = f"{odd_casa_btts:.2f}" if odd_casa_btts > 0 else "No odds found"
        btts_no_display = f"{odd_casa_btts_no:.2f}" if odd_casa_btts_no > 0 else "No odds found"
        linha_over_display = f"{odd_casa_linha_over:.2f}" if odd_casa_linha_over > 0 else "No odds found"
        linha_under_display = f"{odd_casa_linha_under:.2f}" if odd_casa_linha_under > 0 else "No odds found"

        texto = "<h3>Probabilidades Calculadas</h3>"
        texto += (
            f"<p><b style='color: {color_over25};'>Over 2.5 Goals:</b> {prob_over25:.1f}% "
            f"(Odd Justa: {odd_justa_over25_exibida:.2f}) vs Casa {over25_display} - "
            f"EV: {ev_over25:.1f}% - <span style='color: {color_over25};'>{gestao_over25}</span></p>"
        )
        texto += (
            f"<p><b style='color: {color_under25};'>Under 2.5 Goals:</b> {prob_under25:.1f}% "
            f"(Odd Justa: {odd_justa_under25_exibida:.2f}) vs Casa {under25_display} - "
            f"EV: {ev_under25:.1f}% - <span style='color: {color_under25};'>{gestao_under25}</span></p>"
        )
        texto += (
            f"<p><b style='color: {color_btts};'>Ambas Marcam (BTTS Sim):</b> {prob_btts:.1f}% "
            f"(Odd Justa: {odd_justa_btts_exibida:.2f}) vs Casa {btts_display} - "
            f"EV: {ev_btts:.1f}% - <span style='color: {color_btts};'>{gestao_btts}</span></p>"
        )
        texto += (
            f"<p><b style='color: {color_btts_nao};'>BTTS Não:</b> {prob_btts_nao:.1f}% "
            f"(Odd Justa: {odd_justa_btts_nao_exibida:.2f}) vs Casa {btts_no_display} - "
            f"EV: {ev_btts_nao:.1f}% - <span style='color: {color_btts_nao};'>{gestao_btts_nao}</span></p>"
        )

        if selected_line is not None and selected_line in evs_linhas:
            linha = selected_line
            prob_linha_over_sel = evs_linhas[linha]['prob_over']
            prob_linha_under_sel = evs_linhas[linha]['prob_under']
            ev_linha_over_sel = evs_linhas[linha]['over']
            ev_linha_under_sel = evs_linhas[linha]['under']
            odd_casa_linha_over_sel = evs_linhas[linha]['odd_casa_over']
            odd_casa_linha_under_sel = evs_linhas[linha]['odd_casa_under']

            gestao_linha_over_sel, _, color_linha_over_sel = self.get_gestao_banca(ev_linha_over_sel)
            gestao_linha_under_sel, _, color_linha_under_sel = self.get_gestao_banca(ev_linha_under_sel)

            linha_over_display_sel = f"{odd_casa_linha_over_sel:.2f}" if odd_casa_linha_over_sel > 0 else "No odds found"
            linha_under_display_sel = f"{odd_casa_linha_under_sel:.2f}" if odd_casa_linha_under_sel > 0 else "No odds found"
            odd_justa_linha_over_sel = (100 / prob_linha_over_sel) if prob_linha_over_sel > 0 else 100.0
            odd_justa_linha_under_sel = (100 / prob_linha_under_sel) if prob_linha_under_sel > 0 else 100.0

            texto += f"<h4>Linhas Asiáticas (Linha {linha}):</h4>"
            texto += (
                f"<p><b style='color: {color_linha_over_sel};'>Over:</b> {prob_linha_over_sel:.1f}% "
                f"(Odd Justa: {odd_justa_linha_over_sel:.2f}) vs Casa {linha_over_display_sel} - "
                f"EV: {ev_linha_over_sel:.1f}% - <span style='color: {color_linha_over_sel};'>{gestao_linha_over_sel}</span></p>"
            )
            texto += (
                f"<p><b style='color: {color_linha_under_sel};'>Under:</b> {prob_linha_under_sel:.1f}% "
                f"(Odd Justa: {odd_justa_linha_under_sel:.2f}) vs Casa {linha_under_display_sel} - "
                f"EV: {ev_linha_under_sel:.1f}% - <span style='color: {color_linha_under_sel};'>{gestao_linha_under_sel}</span></p>"
            )
        else:
            texto += f"<h4>Linhas Asiáticas (Linha {odds_justas['linha_valor']}):</h4>"
            texto += (
                f"<p><b style='color: {color_linha_over};'>Over:</b> {prob_linha_over:.1f}% "
                f"(Odd Justa: {odd_justa_linha_over_exibida:.2f}) vs Casa {linha_over_display} - "
                f"EV: {ev_linha_over:.1f}% - <span style='color: {color_linha_over};'>{gestao_linha_over}</span></p>"
            )
            texto += (
                f"<p><b style='color: {color_linha_under};'>Under:</b> {prob_linha_under:.1f}% "
                f"(Odd Justa: {odd_justa_linha_under_exibida:.2f}) vs Casa {linha_under_display} - "
                f"EV: {ev_linha_under:.1f}% - <span style='color: {color_linha_under};'>{gestao_linha_under}</span></p>"
            )

        self.resultados.setHtml(texto)

        # Lista EV positivo
        self.ev_positivo_list.clear()
        mercados_ev_positivo = [
            ("Over 2.5", ev_over25, odd_casa_over25, self.get_gestao_banca(ev_over25)),
            ("Under 2.5", ev_under25, odd_casa_under25, self.get_gestao_banca(ev_under25)),
            ("BTTS Sim", ev_btts, odd_casa_btts, self.get_gestao_banca(ev_btts)),
            ("BTTS Não", ev_btts_nao, odd_casa_btts_no, self.get_gestao_banca(ev_btts_nao)),
        ]

        for linha, ev_data in evs_linhas.items():
            ev_over = ev_data['over'] if ev_data['odd_casa_over'] > 0 else 0.0
            ev_under = ev_data['under'] if ev_data['odd_casa_under'] > 0 else 0.0
            mercados_ev_positivo.append((f"Over {linha}", ev_over, ev_data['odd_casa_over'], self.get_gestao_banca(ev_over)))
            mercados_ev_positivo.append((f"Under {linha}", ev_under, ev_data['odd_casa_under'], self.get_gestao_banca(ev_under)))

        for mercado, ev, odd_casa, (gestao, _, cor) in mercados_ev_positivo:
            if ev > 0 and odd_casa > 0:
                item_text = f"{mercado} EV: {ev:.1f}% - Odd: {odd_casa:.2f} - {gestao}"
                item = QListWidgetItem(item_text)
                linha = None
                if "Over" in mercado or "Under" in mercado:
                    try:
                        linha = float(mercado.split()[1])
                    except (IndexError, ValueError):
                        pass
                item.setData(Qt.UserRole, linha)
                item.setData(Qt.UserRole + 1, odd_casa)
                item.setForeground(QtGui.QColor(cor))
                self.ev_positivo_list.addItem(item)

        # Lista main lines (odd 1.70-2.25)
        self.main_lines_list.clear()
        for mercado, ev, odd_casa, (gestao, _, cor) in mercados_ev_positivo:
            if 1.70 <= odd_casa <= 2.25:
                item_text = f"{mercado} EV: {ev:.1f}% - Odd: {odd_casa:.2f} - {gestao}"
                item = QListWidgetItem(item_text)
                linha = None
                if "Over" in mercado or "Under" in mercado:
                    try:
                        linha = float(mercado.split()[1])
                    except (IndexError, ValueError):
                        pass
                item.setData(Qt.UserRole, linha)
                item.setData(Qt.UserRole + 1, odd_casa)
                item.setForeground(QtGui.QColor(cor))
                self.main_lines_list.addItem(item)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    calculadora = CalculadoraEstatistica()
    calculadora.show()
    sys.exit(app.exec_())
