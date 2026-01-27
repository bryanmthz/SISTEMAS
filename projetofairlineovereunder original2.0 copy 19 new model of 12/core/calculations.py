import math


def poisson_pmf(k, lambda_):
    """Calcula a função massa de probabilidade de Poisson."""
    return (math.exp(-lambda_) * lambda_ ** k) / math.factorial(k)


def safe_get(dic, key, default=0.0):
    """Retorna valor do dicionário ou default se não existir."""
    if not isinstance(dic, dict):
        return default
    return dic.get(key, default)


def calcular_fator_performance(time):
    """✅ CONSERVADOR: Faixa 0.96-1.04 (impacto mínimo)"""
    ppg = time.get("ppg", 1.0)
    score_ppg = min(1.0, max(0, (ppg - 0.5) / 2.0))
    fator = 0.96 + score_ppg * 0.08
    return min(1.04, max(0.96, fator))


def calcular_lambdas(dados):
    """
    ✅ CONSERVADOR (estilo P1) + REFINAMENTOS (do P3):
    - Multiplicadores BAIXOS: 1.05 e 1.02
    - Home advantage MÍNIMO: 1.015
    - Defesa tem MAIS impacto: 0.08
    - Alpha PPG MÍNIMO: 0.05
    - Peso média: 0.40 (igual P1)
    """
    peso_media = 0.40  # IGUAL P1
    peso_xg = 0.60
    
    mandante = dados["mandante"]
    visitante = dados["visitante"]
    
    fator_perf_m = calcular_fator_performance(mandante)
    fator_perf_v = calcular_fator_performance(visitante)
    alpha = 0.05  # MUITO baixo
    fator_mandante = 1 + (fator_perf_m - 1) * alpha
    fator_visitante = 1 + (fator_perf_v - 1) * alpha
    
    xg_mandante = mandante.get("xg_ataque", mandante["media_gols"])
    xg_visitante = visitante.get("xg_ataque", visitante["media_gols"])
    
    # ✅ MULTIPLICADORES MÍNIMOS
    lambda_mandante = (
        (mandante["media_gols"] * peso_media) + (xg_mandante * peso_xg)
    ) * 1.05
    
    lambda_visitante = (
        (visitante["media_gols"] * peso_media) + (xg_visitante * peso_xg)
    ) * 1.02
    
    lambda_mandante *= fator_mandante
    lambda_visitante *= fator_visitante
    
    # ✅ DEFESA COM MUITO IMPACTO
    lambda_mandante *= 1 - min(0.25, visitante["media_sofridos"] * 0.08)
    lambda_visitante *= 1 - min(0.25, mandante["media_sofridos"] * 0.08)
    
    # ✅ FATOR PPG MÍNIMO
    ppg_mandante = mandante.get("ppg", 1.0)
    ppg_visitante = visitante.get("ppg", 1.0)
    fator_ppg = min(1.12, max(0.88, 1 + (ppg_mandante - ppg_visitante) * 0.05))
    
    lambda_mandante *= fator_ppg
    lambda_visitante /= fator_ppg
    
    # ✅ HOME ADVANTAGE MÍNIMO
    home_adv = dados["campeonato"].get("home_advantage", 1.015)
    home_adv = min(1.02, max(1.01, home_adv))
    lambda_mandante *= home_adv
    lambda_visitante *= 2 - home_adv
    
    return max(0.2, lambda_mandante), max(0.2, lambda_visitante)


def calcular_lambdas_handicap(dados):
    return calcular_lambdas(dados)


def prob_total_over(linha, lambda_total):
    L_eff = linha + 0.5
    n = math.floor(L_eff)
    r = L_eff - n
    
    def poisson_tail(k, lam):
        total = 0.0
        for i in range(k, k + 40):
            total += poisson_pmf(i, lam)
        return total
    
    if r == 0:
        return poisson_tail(n, lambda_total)
    else:
        p1 = poisson_tail(n, lambda_total)
        p2 = poisson_tail(n + 1, lambda_total)
        return (1 - r) * p1 + r * p2


def calcular_over25(dados, lambda_mandante, lambda_visitante):
    """
    ✅ CONSERVADOR:
    - Peso Poisson: 50% (meio termo P1-60% e P3-20%)
    - Distribuição IGUAL P1: 30/25/25/20
    """
    lambda_total = lambda_mandante + lambda_visitante
    base_prob = prob_total_over(2.5, lambda_total)
    
    fatores = []
    if dados["confronto"]["jogos"] > 0:
        # IGUAL P1
        fatores.append(safe_get(dados["confronto"], "over25", 0.0) * 0.30)
        fatores.append(safe_get(dados["mandante"], "over25_8", 0.0) * 0.25)
        fatores.append(safe_get(dados["visitante"], "over25_8", 0.0) * 0.25)
        fatores.append(safe_get(dados["campeonato"], "over25", 0.0) * 0.20)
    else:
        # IGUAL P1
        fatores.append(safe_get(dados["mandante"], "over25_8", 0.0) * 0.40)
        fatores.append(safe_get(dados["visitante"], "over25_8", 0.0) * 0.40)
        fatores.append(safe_get(dados["campeonato"], "over25", 0.0) * 0.20)
    
    POISSON_PESO = 0.50
    prob_final = (base_prob * POISSON_PESO) + (sum(fatores) * (1 - POISSON_PESO))
    return min(0.95, max(0.05, prob_final))


def calcular_btts(dados, lambda_mandante, lambda_visitante):
    prob_mandante = 1 - math.exp(-lambda_mandante)
    prob_visitante = 1 - math.exp(-lambda_visitante)
    prob_poisson = prob_mandante * prob_visitante
    
    fatores = []
    if dados["confronto"]["jogos"] > 0:
        fatores.append(safe_get(dados["confronto"], "btts", 0.0) * 0.30)
        fatores.append(safe_get(dados["mandante"], "btts_8", 0.0) * 0.25)
        fatores.append(safe_get(dados["visitante"], "btts_8", 0.0) * 0.25)
        fatores.append(safe_get(dados["campeonato"], "btts", 0.0) * 0.20)
    else:
        fatores.append(safe_get(dados["mandante"], "btts_8", 0.0) * 0.40)
        fatores.append(safe_get(dados["visitante"], "btts_8", 0.0) * 0.40)
        fatores.append(safe_get(dados["campeonato"], "btts", 0.0) * 0.20)
    
    POISSON_PESO = 0.50
    return min(0.95, max(0.05, (prob_poisson * POISSON_PESO) + (sum(fatores) * (1 - POISSON_PESO))))


def calcular_under25(dados, lambda_mandante, lambda_visitante):
    prob_over = calcular_over25(dados, lambda_mandante, lambda_visitante)
    return min(0.95, max(0.05, 1 - prob_over))


def calcular_btts_nao(dados, lambda_mandante, lambda_visitante):
    prob_btts_sim = calcular_btts(dados, lambda_mandante, lambda_visitante)
    return min(0.95, max(0.05, 1 - prob_btts_sim))


LINHAS_ASIATICAS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]
indice_linha_atual = 0


def ciclo_linha_asiatica():
    global indice_linha_atual
    if indice_linha_atual < len(LINHAS_ASIATICAS) - 1:
        indice_linha_atual += 1
    return LINHAS_ASIATICAS[indice_linha_atual]


def ciclo_linha_asiatica_para_baixo():
    global indice_linha_atual
    if indice_linha_atual > 0:
        indice_linha_atual -= 1
    return LINHAS_ASIATICAS[indice_linha_atual]


def definir_linha_atual(linha):
    global indice_linha_atual
    try:
        indice_linha_atual = LINHAS_ASIATICAS.index(linha)
    except ValueError:
        pass


def obter_linha_atual():
    return LINHAS_ASIATICAS[indice_linha_atual]


def calcular_money_line(lambda_mandante, lambda_visitante):
    lambda_mandante = min(5.0, max(0.3, lambda_mandante))
    lambda_visitante = min(5.0, max(0.3, lambda_visitante))
    
    max_goals = 10
    prob_1 = 0.0
    prob_x = 0.0
    prob_2 = 0.0
    
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_pmf(i, lambda_mandante) * poisson_pmf(j, lambda_visitante)
            if i > j:
                prob_1 += prob
            elif i == j:
                prob_x += prob
            else:
                prob_2 += prob
    
    total = prob_1 + prob_x + prob_2
    if total > 0:
        prob_1 /= total
        prob_x /= total
        prob_2 /= total
    
    return {
        "1": min(0.95, max(0.05, prob_1)),
        "X": min(0.95, max(0.05, prob_x)),
        "2": min(0.95, max(0.05, prob_2)),
    }


def calcular_linha_asiatica(dados, lambda_mandante, lambda_visitante, linha):
    lambda_total = lambda_mandante + lambda_visitante
    base_prob = prob_total_over(linha, lambda_total)
    
    fatores = []
    
    pesos_confronto = {
        0.5: [("over15", 1.0)],
        0.75: [("over15", 1.0)],
        1.0: [("over15", 1.0)],
        1.25: [("over15", 1.0)],
        1.5: [("over15", 1.0)],
        1.75: [("over15", 0.75), ("over25", 0.25)],
        2.0: [("over15", 0.50), ("over25", 0.50)],
        2.25: [("over25", 0.75), ("over15", 0.25)],
        2.5: [("over25", 1.0)],
        2.75: [("over25", 0.75), ("over35", 0.25)],
        3.0: [("over25", 0.50), ("over35", 0.50)],
        3.25: [("over25", 0.25), ("over35", 0.75)],
        3.5: [("over35", 1.0)],
    }
    
    pesos = pesos_confronto.get(linha, [("over25", 1.0)])
    
    for tipo, peso in pesos:
        if dados["confronto"]["jogos"] > 0:
            if tipo == "over15":
                fatores.append(safe_get(dados["confronto"], "over15", 0.0) * peso * 0.30)
                fatores.append(safe_get(dados["mandante"], "over15_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["visitante"], "over15_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["campeonato"], "over15", 0.0) * peso * 0.20)
            elif tipo == "over25":
                fatores.append(safe_get(dados["confronto"], "over25", 0.0) * peso * 0.30)
                fatores.append(safe_get(dados["mandante"], "over25_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["visitante"], "over25_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["campeonato"], "over25", 0.0) * peso * 0.20)
            elif tipo == "over35":
                fatores.append(safe_get(dados["confronto"], "over35", 0.0) * peso * 0.30)
                fatores.append(safe_get(dados["mandante"], "over35_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["visitante"], "over35_8", 0.0) * peso * 0.25)
                fatores.append(safe_get(dados["campeonato"], "over35", 0.0) * peso * 0.20)
        else:
            if tipo == "over15":
                fatores.append(safe_get(dados["mandante"], "over15_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["visitante"], "over15_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["campeonato"], "over15", 0.0) * peso * 0.20)
            elif tipo == "over25":
                fatores.append(safe_get(dados["mandante"], "over25_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["visitante"], "over25_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["campeonato"], "over25", 0.0) * peso * 0.20)
            elif tipo == "over35":
                fatores.append(safe_get(dados["mandante"], "over35_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["visitante"], "over35_8", 0.0) * peso * 0.40)
                fatores.append(safe_get(dados["campeonato"], "over35", 0.0) * peso * 0.20)
    
    POISSON_PESO = 0.50
    prob_final = (base_prob * POISSON_PESO) + (sum(fatores) * (1 - POISSON_PESO))
    return min(0.95, max(0.05, prob_final))


def calcular_placares_provaveis(dados):
    lambda_mandante, lambda_visitante = calcular_lambdas(dados)
    lambda_total = lambda_mandante + lambda_visitante
    max_goals = max(6, int(lambda_total) + 2)
    
    placares = []
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = poisson_pmf(i, lambda_mandante) * poisson_pmf(j, lambda_visitante)
            placares.append((i, j, prob))
    
    placares.sort(key=lambda x: x[2], reverse=True)
    top3 = placares[:3]
    return [{"placar": f"{p[0]}x{p[1]}", "probabilidade": p[2]} for p in top3]


def probabilidade_para_odd(probabilidade):
    return 1 / max(0.01, probabilidade)


def calcular_odds_completas(dados, handicap=None):
    lambda_m, lambda_v = calcular_lambdas(dados)
    
    prob_over25 = calcular_over25(dados, lambda_m, lambda_v)
    prob_under25 = 1 - prob_over25
    prob_btts = calcular_btts(dados, lambda_m, lambda_v)
    prob_btts_nao = 1 - prob_btts
    
    money_line = calcular_money_line(lambda_m, lambda_v)
    linha_atual = obter_linha_atual()
    prob_linha_over = calcular_linha_asiatica(dados, lambda_m, lambda_v, linha_atual)
    prob_linha_under = 1 - prob_linha_over
    
    placares = calcular_placares_provaveis(dados)
    
    odds = {
        "btts": {
            "sim": probabilidade_para_odd(prob_btts),
            "nao": probabilidade_para_odd(prob_btts_nao),
        },
        "over_under": {
            "over25": probabilidade_para_odd(prob_over25),
            "under25": probabilidade_para_odd(prob_under25),
        },
        "linha_asiatica": {
            "valor": linha_atual,
            "over": probabilidade_para_odd(prob_linha_over),
            "under": probabilidade_para_odd(prob_linha_under),
        },
        "money_line": {
            "1": probabilidade_para_odd(money_line["1"]),
            "X": probabilidade_para_odd(money_line["X"]),
            "2": probabilidade_para_odd(money_line["2"]),
        },
        "placares_provaveis": placares,
    }
    
    return odds


VERSAO = "3.3-CONSERVADOR"
