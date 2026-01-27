import sys
import math
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QDoubleSpinBox, 
                             QTextEdit, QGroupBox, QFormLayout, QCheckBox)
from PyQt5.QtCore import Qt

class CalculadoraEstatistica(QWidget):
    def __init__(self):
        super().__init__()
        self.dark_mode = True  # Tema inicial
        self.setup_ui()
        self.setStyleSheet(get_stylesheet(self.dark_mode))

    def setup_ui(self):
        self.setWindowTitle('Calculadora Estatística - Previsão de Jogos')
        self.setGeometry(100, 100, 1200, 800)
        
        main_layout = QHBoxLayout()

        # Seção Time Mandante
        self.mandante_group = self.create_team_section("Time Mandante")
        
        # Seção Central
        central_group = self.create_central_section()
        
        # Seção Time Visitante
        self.visitante_group = self.create_team_section("Time Visitante")

        main_layout.addWidget(self.mandante_group)
        main_layout.addWidget(central_group)
        main_layout.addWidget(self.visitante_group)

        self.setLayout(main_layout)

    def create_team_section(self, title):
        group = QGroupBox(title)
        layout = QVBoxLayout()
        prefix = title.replace(" ", "_").lower()

        # Métricas Básicas
        basico_group = QGroupBox("Estatísticas Básicas")
        basico_layout = QFormLayout()
        self.add_spinbox(basico_layout, "Média Gols Marcados:", f"{prefix}_media_gols_marcados", 0.0, 5.0, 1.5)
        self.add_spinbox(basico_layout, "Média Gols Sofridos:", f"{prefix}_media_gols_sofridos", 0.0, 5.0, 1.2)
        basico_group.setLayout(basico_layout)

        # Métricas Avançadas
        avancado_group = QGroupBox("Métricas Avançadas (xG)")
        avancado_layout = QFormLayout()
        self.add_spinbox(avancado_layout, "xG Ataque:", f"{prefix}_xg_ataque", 0.0, 5.0, 1.5)
        self.add_spinbox(avancado_layout, "xG Defesa:", f"{prefix}_xg_defesa", 0.0, 5.0, 1.2)
        avancado_group.setLayout(avancado_layout)

        # Fatores Contextuais
        contexto_group = QGroupBox("Fatores Contextuais")
        contexto_layout = QFormLayout()
        self.add_spinbox(contexto_layout, "Lesões/Suspensões (0-5):", f"{prefix}_lesoes", 0, 5, 0)
        self.add_spinbox(contexto_layout, "% BTTS Recente:", f"{prefix}_btts_8", 0, 100, 50)
        self.add_spinbox(contexto_layout, "% Over 2.5 Recente:", f"{prefix}_over25_8", 0, 100, 40)
        contexto_group.setLayout(contexto_layout)

        layout.addWidget(basico_group)
        layout.addWidget(avancado_group)
        layout.addWidget(contexto_group)
        group.setLayout(layout)
        return group

    def create_central_section(self):
        group = QGroupBox("Configurações Gerais")
        layout = QVBoxLayout()

        # Alternância de Tema
        self.toggle_theme = QCheckBox("Modo Escuro")
        self.toggle_theme.setChecked(self.dark_mode)
        self.toggle_theme.stateChanged.connect(self.alternar_tema)
        layout.addWidget(self.toggle_theme)

        # Campeonato
        camp_group = QGroupBox("Estatísticas do Campeonato")
        camp_layout = QFormLayout()
        self.add_spinbox(camp_layout, "Média de Gols:", "campeonato_media_gols", 0.0, 5.0, 2.5)
        self.add_spinbox(camp_layout, "% BTTS:", "campeonato_btts", 0, 100, 45)
        self.add_spinbox(camp_layout, "% Over 2.5:", "campeonato_over25", 0, 100, 50)
        camp_group.setLayout(camp_layout)

        # Confrontos Diretos
        confronto_group = QGroupBox("Histórico de Confrontos")
        confronto_layout = QFormLayout()
        self.add_spinbox(confronto_layout, "Jogos Analisados:", "confronto_jogos", 0, 50, 8)
        self.add_spinbox(confronto_layout, "% Over 2.5:", "confronto_over25", 0, 100, 50)
        self.add_spinbox(confronto_layout, "% BTTS:", "confronto_btts", 0, 100, 50)
        confronto_group.setLayout(confronto_layout)

        # Odd da Casa de Aposta
        odd_group = QGroupBox("Comparativo de Odds")
        odd_layout = QFormLayout()
        self.add_spinbox(odd_layout, "Odd Casa (Over 2.5):", "odd_over25", 1.0, 10.0, 2.0)
        self.add_spinbox(odd_layout, "Odd Casa (BTTS):", "odd_btts", 1.0, 10.0, 2.0)
        odd_group.setLayout(odd_layout)

        # Controles
        self.btn_calcular = QPushButton("Calcular Probabilidades")
        self.btn_calcular.clicked.connect(self.calcular_odds)
        layout.addWidget(camp_group)
        layout.addWidget(confronto_group)
        layout.addWidget(odd_group)
        layout.addWidget(self.btn_calcular)
        
        # Novo botão para validação do modelo
        self.btn_validar = QPushButton("Validar Modelo")
        self.btn_validar.clicked.connect(self.validar_modelo)
        layout.addWidget(self.btn_validar)
        
        self.resultados = QTextEdit()
        self.resultados.setReadOnly(True)
        layout.addWidget(self.resultados)
        group.setLayout(layout)
        return group

    def add_spinbox(self, layout, label, name, min_val, max_val, default=0):
        spin = QDoubleSpinBox()
        spin.setObjectName(name)
        spin.setRange(min_val, max_val)
        spin.setValue(default)
        spin.setSingleStep(0.1 if max_val > 10 else 1)
        layout.addRow(QLabel(label), spin)
        return spin

    def alternar_tema(self):
        self.dark_mode = self.toggle_theme.isChecked()
        self.setStyleSheet(get_stylesheet(self.dark_mode))

    def calcular_odds(self):
        try:
            dados = self.coletar_dados()
            lambda_mandante, lambda_visitante = self.calcular_lambdas(dados)
            prob_over25 = self.calcular_over25(dados, lambda_mandante, lambda_visitante)
            prob_btts = self.calcular_btts(dados, lambda_mandante, lambda_visitante)
            
            # Conversão para odds
            odd_over25 = self.probabilidade_para_odd(prob_over25)
            odd_btts = self.probabilidade_para_odd(prob_btts)
            
            # Comparativo de odds
            odd_casa_over25 = self.findChild(QDoubleSpinBox, "odd_over25").value()
            odd_casa_btts = self.findChild(QDoubleSpinBox, "odd_btts").value()
            
            # Verificação de value bet
            value_over25 = odd_casa_over25 >= odd_over25 * 1.05
            value_btts = odd_casa_btts >= odd_btts * 1.05
            
            # Exibir resultados
            self.exibir_resultados(lambda_mandante, lambda_visitante, prob_over25, prob_btts, 
                                  odd_over25, odd_btts, value_over25, value_btts)

        except Exception as e:
            self.resultados.setPlainText(f"Erro: {str(e)}")

    def coletar_dados(self):
        return {
            'mandante': {
                'media_gols': self.findChild(QDoubleSpinBox, "time_mandante_media_gols_marcados").value(),
                'media_sofridos': self.findChild(QDoubleSpinBox, "time_mandante_media_gols_sofridos").value(),
                'xg_ataque': self.findChild(QDoubleSpinBox, "time_mandante_xg_ataque").value(),
                'xg_defesa': self.findChild(QDoubleSpinBox, "time_mandante_xg_defesa").value(),
                'lesoes': self.findChild(QDoubleSpinBox, "time_mandante_lesoes").value(),
                'btts_8': self.findChild(QDoubleSpinBox, "time_mandante_btts_8").value()/100,
                'over25_8': self.findChild(QDoubleSpinBox, "time_mandante_over25_8").value()/100
            },
            'visitante': {
                'media_gols': self.findChild(QDoubleSpinBox, "time_visitante_media_gols_marcados").value(),
                'media_sofridos': self.findChild(QDoubleSpinBox, "time_visitante_media_gols_sofridos").value(),
                'xg_ataque': self.findChild(QDoubleSpinBox, "time_visitante_xg_ataque").value(),
                'xg_defesa': self.findChild(QDoubleSpinBox, "time_visitante_xg_defesa").value(),
                'lesoes': self.findChild(QDoubleSpinBox, "time_visitante_lesoes").value(),
                'btts_8': self.findChild(QDoubleSpinBox, "time_visitante_btts_8").value()/100,
                'over25_8': self.findChild(QDoubleSpinBox, "time_visitante_over25_8").value()/100
            },
            'campeonato': {
                'media_gols': self.findChild(QDoubleSpinBox, "campeonato_media_gols").value(),
                'btts': self.findChild(QDoubleSpinBox, "campeonato_btts").value()/100,
                'over25': self.findChild(QDoubleSpinBox, "campeonato_over25").value()/100
            },
            'confronto': {
                'jogos': self.findChild(QDoubleSpinBox, "confronto_jogos").value(),
                'over25': self.findChild(QDoubleSpinBox, "confronto_over25").value()/100,
                'btts': self.findChild(QDoubleSpinBox, "confronto_btts").value()/100
            }
        }

    def calcular_lambdas(self, dados):
        # Pesos das métricas (ajustados por análise)
        peso_media = 0.4
        peso_xg = 0.6
        peso_lesoes = 0.05
        
        # Cálculo para mandante
        lambda_mandante = (
            (dados['mandante']['media_gols'] * peso_media) +
            (dados['mandante']['xg_ataque'] * peso_xg) -
            (dados['mandante']['lesoes'] * peso_lesoes)
        )
        
        # Cálculo para visitante
        lambda_visitante = (
            (dados['visitante']['media_gols'] * peso_media) +
            (dados['visitante']['xg_ataque'] * peso_xg) -
            (dados['visitante']['lesoes'] * peso_lesoes)
        )
        
        # Ajuste defensivo
        lambda_mandante *= (1 - (dados['visitante']['media_sofridos'] * 0.1))
        lambda_visitante *= (1 - (dados['mandante']['media_sofridos'] * 0.1))
        
        return max(0.1, lambda_mandante), max(0.1, lambda_visitante)

    def calcular_over25(self, dados, lambda_mandante, lambda_visitante):
        # Base Poisson para calcular a probabilidade de menos de 3 gols
        prob_poisson = 1 - sum(
            poisson_pmf(i, lambda_mandante) * poisson_pmf(j, lambda_visitante)
            for i in range(3) for j in range(3 - i)
        )
        
        # Fatores contextuais
        fatores = []
        if dados['confronto']['jogos'] > 0:
            fatores.append(dados['confronto']['over25'] * 0.3)
            fatores.append(dados['mandante']['over25_8'] * 0.25)
            fatores.append(dados['visitante']['over25_8'] * 0.25)
            fatores.append(dados['campeonato']['over25'] * 0.2)
        else:
            fatores.append(dados['mandante']['over25_8'] * 0.4)
            fatores.append(dados['visitante']['over25_8'] * 0.4)
            fatores.append(dados['campeonato']['over25'] * 0.2)
        
        return min(0.95, max(0.05, (prob_poisson * 0.6) + (sum(fatores) * 0.4)))

    def calcular_btts(self, dados, lambda_mandante, lambda_visitante):
        # Base Poisson para a probabilidade de marcar pelo menos um gol
        prob_mandante = 1 - math.exp(-lambda_mandante)
        prob_visitante = 1 - math.exp(-lambda_visitante)
        prob_poisson = prob_mandante * prob_visitante
        
        # Fatores contextuais
        fatores = []
        if dados['confronto']['jogos'] > 0:
            fatores.append(dados['confronto']['btts'] * 0.3)
            fatores.append(dados['mandante']['btts_8'] * 0.25)
            fatores.append(dados['visitante']['btts_8'] * 0.25)
            fatores.append(dados['campeonato']['btts'] * 0.2)
        else:
            fatores.append(dados['mandante']['btts_8'] * 0.4)
            fatores.append(dados['visitante']['btts_8'] * 0.4)
            fatores.append(dados['campeonato']['btts'] * 0.2)
        
        return min(0.95, max(0.05, (prob_poisson * 0.6) + (sum(fatores) * 0.4)))

    def probabilidade_para_odd(self, probabilidade):
        return 1 / probabilidade if probabilidade > 0 else 999.0

    def exibir_resultados(self, lambda_mandante, lambda_visitante, prob_over25, prob_btts, 
                           odd_over25, odd_btts, value_over25, value_btts):
        texto = (f"<h3>Probabilidades Calculadas</h3>"
                 f"<p><b>Over 2.5 Goals:</b> {prob_over25:.1%} (Odd: {odd_over25:.2f}) - "
                 f"<span style='color:{'green' if value_over25 else 'red'};'>"
                 f"{'Value Bet' if value_over25 else 'No Value Bet'}</span></p>"
                 f"<p><b>Ambas Marcam (BTTS):</b> {prob_btts:.1%} (Odd: {odd_btts:.2f}) - "
                 f"<span style='color:{'green' if value_btts else 'red'};'>"
                 f"{'Value Bet' if value_btts else 'No Value Bet'}</span></p>"
                 f"<p><b>Médias Esperadas de Gols:</b><br>"
                 f"Mandante: {lambda_mandante:.2f} (Marcados) | {lambda_visitante:.2f} (Sofridos)<br>"
                 f"Visitante: {lambda_visitante:.2f} (Marcados) | {lambda_mandante:.2f} (Sofridos)</p>")
        self.resultados.setHtml(texto)

    def validar_modelo(self):
        """
        Função para validar o modelo usando dados históricos dummy.
        Para cada partida, calculamos as probabilidades previstas e comparamos com os resultados reais,
        computando o MAE (erro absoluto médio) e o Brier Score (erro quadrático médio).
        """
        try:
            # Conjunto de dados históricos (exemplo)
            # Cada dicionário segue a mesma estrutura que 'dados' + resultados reais
            historical_data = [
                {
                    'mandante': {
                        'media_gols': 1.5,
                        'media_sofridos': 1.2,
                        'xg_ataque': 1.7,
                        'xg_defesa': 1.2,
                        'lesoes': 0,
                        'btts_8': 0.5,
                        'over25_8': 0.4
                    },
                    'visitante': {
                        'media_gols': 1.2,
                        'media_sofridos': 1.0,
                        'xg_ataque': 1.4,
                        'xg_defesa': 1.1,
                        'lesoes': 0,
                        'btts_8': 0.6,
                        'over25_8': 0.35
                    },
                    'campeonato': {
                        'media_gols': 2.5,
                        'btts': 0.45,
                        'over25': 0.5
                    },
                    'confronto': {
                        'jogos': 10,
                        'over25': 0.55,
                        'btts': 0.5
                    },
                    'resultado_over25': 1,  # 1 = over 2.5 ocorreu
                    'resultado_btts': 1   # 1 = ambas marcaram
                },
                {
                    'mandante': {
                        'media_gols': 1.3,
                        'media_sofridos': 1.1,
                        'xg_ataque': 1.4,
                        'xg_defesa': 1.0,
                        'lesoes': 1,
                        'btts_8': 0.45,
                        'over25_8': 0.38
                    },
                    'visitante': {
                        'media_gols': 1.0,
                        'media_sofridos': 0.9,
                        'xg_ataque': 1.1,
                        'xg_defesa': 1.0,
                        'lesoes': 0,
                        'btts_8': 0.50,
                        'over25_8': 0.30
                    },
                    'campeonato': {
                        'media_gols': 2.3,
                        'btts': 0.40,
                        'over25': 0.48
                    },
                    'confronto': {
                        'jogos': 0,
                        'over25': 0.0,
                        'btts': 0.0
                    },
                    'resultado_over25': 0,
                    'resultado_btts': 0
                },
                {
                    'mandante': {
                        'media_gols': 1.8,
                        'media_sofridos': 1.3,
                        'xg_ataque': 1.9,
                        'xg_defesa': 1.3,
                        'lesoes': 0,
                        'btts_8': 0.55,
                        'over25_8': 0.42
                    },
                    'visitante': {
                        'media_gols': 1.6,
                        'media_sofridos': 1.4,
                        'xg_ataque': 1.7,
                        'xg_defesa': 1.4,
                        'lesoes': 1,
                        'btts_8': 0.60,
                        'over25_8': 0.40
                    },
                    'campeonato': {
                        'media_gols': 2.7,
                        'btts': 0.50,
                        'over25': 0.52
                    },
                    'confronto': {
                        'jogos': 5,
                        'over25': 0.60,
                        'btts': 0.55
                    },
                    'resultado_over25': 1,
                    'resultado_btts': 0
                }
            ]
            
            n = len(historical_data)
            # Listas para armazenar as previsões e os resultados reais
            preds_over25 = []
            truths_over25 = []
            preds_btts = []
            truths_btts = []
            
            for partida in historical_data:
                lambda_mandante, lambda_visitante = self.calcular_lambdas(partida)
                p_over25 = self.calcular_over25(partida, lambda_mandante, lambda_visitante)
                p_btts = self.calcular_btts(partida, lambda_mandante, lambda_visitante)
                
                preds_over25.append(p_over25)
                truths_over25.append(partida['resultado_over25'])
                preds_btts.append(p_btts)
                truths_btts.append(partida['resultado_btts'])
            
            # Cálculo do MAE (erro absoluto médio) e Brier Score (erro quadrático médio)
            mae_over25 = sum(abs(p - t) for p, t in zip(preds_over25, truths_over25)) / n
            brier_over25 = sum((p - t) ** 2 for p, t in zip(preds_over25, truths_over25)) / n
            
            mae_btts = sum(abs(p - t) for p, t in zip(preds_btts, truths_btts)) / n
            brier_btts = sum((p - t) ** 2 for p, t in zip(preds_btts, truths_btts)) / n
            
            texto = (f"<h3>Validação do Modelo</h3>"
                     f"<p>Número de partidas analisadas: {n}</p>"
                     f"<p><b>Over 2.5 Goals</b><br>"
                     f"MAE: {mae_over25:.3f}<br>"
                     f"Brier Score: {brier_over25:.3f}</p>"
                     f"<p><b>Ambas Marcam (BTTS)</b><br>"
                     f"MAE: {mae_btts:.3f}<br>"
                     f"Brier Score: {brier_btts:.3f}</p>")
            self.resultados.setHtml(texto)
        except Exception as e:
            self.resultados.setPlainText(f"Erro na validação: {str(e)}")

def poisson_pmf(k, lambda_):
    return (math.exp(-lambda_) * lambda_**k) / math.factorial(k)

def get_stylesheet(dark_mode):
    if dark_mode:
        return """
        QWidget { 
            background-color: #2D2D2D;
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
        }
        QGroupBox {
            border: 1px solid #444;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
            color: #FFFFFF;
        }
        QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #444;
            border-radius: 4px;
            background-color: #3A3A3A;
            color: #FFFFFF;
        }
        QTextEdit {
            background: #3A3A3A;
            border: 1px solid #444;
            border-radius: 6px;
            padding: 10px;
            font-family: monospace;
            color: #FFFFFF;
        }
        QPushButton {
            background-color: #3B82F6;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2563EB;
        }
        QCheckBox {
            color: #FFFFFF;
        }
        """
    else:
        return """
        QWidget { 
            background-color: #FAF9F6;
            color: #000000;
            font-family: 'Segoe UI', sans-serif;
        }
        QGroupBox {
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
            color: #374151;
        }
        QDoubleSpinBox {
            padding: 5px;
            border: 1px solid #D1D5DB;
            border-radius: 4px;
            background-color: #FFFFFF;
            color: #000000;
        }
        QTextEdit {
            background: #FFFFFF;
            border: 1px solid #D1D5DB;
            border-radius: 6px;
            padding: 10px;
            font-family: monospace;
            color: #000000;
        }
        QPushButton {
            background-color: #3B82F6;
            color: white;
            padding: 10px 20px;
            border-radius: 6px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2563EB;
        }
        QCheckBox {
            color: #000000;
        }
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalculadoraEstatistica()
    window.show()
    sys.exit(app.exec_())
