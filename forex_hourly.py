"""
forex_hourly.py
───────────────
Sistema live de diferença de pips por hora.

Para cada par (base × quote) calcula quantos pips a moeda
base se moveu contra a quote nas últimas 1 hora completa e
na hora corrente (parcial). Exibe:
  - Matriz completa  moeda × moeda  (pips da última hora)
  - Score líquido por moeda (pips ganhos vs perdidos contra todas)
  - Ranking dos 10 melhores pares por divergência
  - Histórico das horas do dia corrente

Atualiza a cada SLEEP segundos (padrão 5 min).
"""

import logging
import warnings

import yfinance as yf
import pandas as pd
import numpy as np
import itertools
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# suprime mensagens de erro internas do yfinance
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]
BRT        = ZoneInfo("America/Sao_Paulo")
SLEEP      = 300   # segundos entre atualizações (5 min)
COL_W      = 8     # largura das colunas numéricas
MIN_PIPS   = 10    # pips mínimos para contar no score


def pip_size(base: str, quote: str) -> float:
    return 0.01 if "JPY" in (base, quote) else 0.0001


# ─────────────────────────────────────────────
# DOWNLOAD
# ─────────────────────────────────────────────

def baixar_todos(pares: list[str]) -> dict[str, pd.Series]:
    """
    Baixa candles de 5 min (últimos 2 dias) para cada par.
    Retorna {par: Series(close, index=BRT)}.
    """
    dados: dict[str, pd.Series] = {}
    total = len(pares)

    for i, par in enumerate(pares, 1):
        print(f"\r  Baixando {i}/{total}  [{par}]    ", end="", flush=True)
        try:
            df = yf.download(par + "=X", period="2d", interval="5m",
                             progress=False, auto_adjust=True, threads=False)
            if df.empty:
                continue

            close = df["Close"].squeeze().dropna()
            if not isinstance(close, pd.Series):
                continue

            if close.index.tz is None:
                close.index = close.index.tz_localize("UTC")
            close.index = close.index.tz_convert(BRT)

            dados[par] = close
        except Exception:
            continue

    print()
    return dados


# ─────────────────────────────────────────────
# PREÇO PONTUAL
# ─────────────────────────────────────────────

def preco_em(serie: pd.Series, dt: datetime) -> float | None:
    """Último fechamento em ou antes de dt."""
    candidatos = serie[serie.index <= dt]
    if candidatos.empty:
        return None
    return float(np.asarray(candidatos.iloc[-1]).flat[0])


# ─────────────────────────────────────────────
# CÁLCULO DE PIPS PARA UM INTERVALO
# ─────────────────────────────────────────────

def pips_par(dados: dict[str, pd.Series],
             base: str, quote: str,
             dt_ini: datetime, dt_fim: datetime) -> float | None:
    """Pips do par base/quote entre dt_ini e dt_fim."""
    par = base + quote
    if par not in dados:
        return None
    p_ini = preco_em(dados[par], dt_ini)
    p_fim = preco_em(dados[par], dt_fim)
    if p_ini is None or p_fim is None or p_ini <= 0:
        return None
    return round((p_fim - p_ini) / pip_size(base, quote), 1)


def calcular_hora(dados: dict[str, pd.Series],
                  dt_ini: datetime,
                  dt_fim: datetime) -> tuple[pd.DataFrame, pd.Series]:
    """
    Retorna:
      matriz  — DataFrame moeda×moeda com pips do intervalo
      score   — Series moeda→pips líquidos (média ponderada vs todas)
    """
    moedas = CURRENCIES
    matriz = pd.DataFrame(np.nan, index=moedas, columns=moedas)
    acum   = {c: 0.0 for c in moedas}
    count  = {c: 0   for c in moedas}

    for base, quote in itertools.permutations(moedas, 2):
        v = pips_par(dados, base, quote, dt_ini, dt_fim)
        if v is None:
            continue
        matriz.loc[base, quote] = v
        # score: só conta movimentos acima do filtro mínimo
        if abs(v) >= MIN_PIPS:
            acum[base]  += v
            acum[quote] -= v
            count[base]  += 1
            count[quote] += 1

    score = pd.Series({
        c: round(acum[c] / count[c], 1) if count[c] > 0 else 0.0
        for c in moedas
    }).sort_values(ascending=False)

    return matriz, score


def score_contagem(matriz: pd.DataFrame) -> pd.Series:
    """
    Para cada moeda como BASE, conta quantas quotes ela bateu
    por mais de MIN_PIPS pips (vitórias). Resultado: 0 a 7.
    """
    contagem = {}
    for base in CURRENCIES:
        vitorias = 0
        for quote in CURRENCIES:
            if base == quote:
                continue
            v = matriz.loc[base, quote]
            if not pd.isna(v) and v > MIN_PIPS:
                vitorias += 1
        contagem[base] = vitorias
    return pd.Series(contagem).sort_values(ascending=False)


# ─────────────────────────────────────────────
# RANKING DE PARES
# ─────────────────────────────────────────────

def ranking_pares(matriz: pd.DataFrame,
                  score: pd.Series,
                  top_n: int = 10) -> pd.DataFrame:
    registros = []
    for base, quote in itertools.permutations(CURRENCIES, 2):
        v = matriz.loc[base, quote]
        if pd.isna(v):
            continue
        registros.append({
            "par"        : base + quote,
            "pips"       : v,
            "abs_pips"   : abs(v),
            "score_base" : score.get(base, 0.0),
            "score_quote": score.get(quote, 0.0),
            "divergencia": round(abs(score.get(base, 0.0) - score.get(quote, 0.0)), 1),
            "direcao"    : f"LONG {base}" if v > 0 else f"SHORT {base}",
        })

    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["rank"] = df["abs_pips"].rank(pct=True) + df["divergencia"].rank(pct=True)
    df.sort_values("rank", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df.head(top_n)


# ─────────────────────────────────────────────
# EXIBIÇÃO
# ─────────────────────────────────────────────

SEP_LARGA  = "═" * 84
SEP_FINA   = "─" * 84


def exibir_matriz(matriz: pd.DataFrame, titulo: str) -> None:
    print(f"\n  {titulo}")
    print(f"  {'(linha=BASE  coluna=QUOTE  | positivo=base valorizou)'}")
    print("  " + SEP_FINA)

    header = f"  {'':>5}" + "".join(f"  {q:>{COL_W}}" for q in CURRENCIES)
    print(header)
    print("  " + SEP_FINA)

    for base in CURRENCIES:
        linha = f"  {base:<5}"
        for quote in CURRENCIES:
            if base == quote:
                linha += f"  {'—':>{COL_W}}"
            else:
                v = matriz.loc[base, quote]
                if pd.isna(v):
                    linha += f"  {'N/D':>{COL_W}}"
                else:
                    linha += f"  {v:>+{COL_W}.1f}"
        print(linha)


def exibir_score(score: pd.Series, titulo: str) -> None:
    print(f"\n  {titulo}")
    print("  " + SEP_FINA)
    print(f"  {'MOEDA':<6}  {'SCORE (pips)':>12}  BARRA")
    print("  " + "─" * 50)

    max_v = max(abs(score.values)) or 1
    for moeda, v in score.items():
        barras = int(abs(v) / max_v * 20)
        sinal  = "+" if v >= 0 else "-"
        print(f"  {moeda:<6}  {v:>+12.1f}  {sinal}{'█' * barras}")


def exibir_score_contagem(contagem: pd.Series, titulo: str) -> None:
    """Score de 0 a 7 — número de moedas batidas por > MIN_PIPS pips."""
    max_moedas = len(CURRENCIES) - 1   # 7
    print(f"\n  {titulo}")
    print(f"  (conta vitórias onde pips > {MIN_PIPS}  |  máximo: {max_moedas})")
    print("  " + SEP_FINA)
    print(f"  {'MOEDA':<6}  {'SCORE':>5}  BARRA")
    print("  " + "─" * 40)

    for moeda, v in contagem.items():
        barras = int(v / max_moedas * 20)
        print(f"  {moeda:<6}  {v:>3}/{max_moedas}  {'█' * barras}")


def exibir_ranking(top: pd.DataFrame, titulo: str) -> None:
    if top.empty:
        print(f"\n  {titulo}  — sem dados suficientes")
        return

    print(f"\n  {titulo}")
    print("  " + SEP_FINA)
    print(f"  {'#':<3} {'PAR':<8} {'PIPS':>7}  {'SC BASE':>8}  {'SC QUOTE':>9}  {'DIVERG':>7}  DIREÇÃO")
    print("  " + "─" * 65)

    for i, row in top.iterrows():
        alinhado = row["pips"] * (row["score_base"] - row["score_quote"]) > 0
        marca = " ★" if alinhado else "  "
        print(
            f"  {i+1:<3} {row['par']:<8} "
            f"{row['pips']:>+7.1f}  "
            f"{row['score_base']:>+8.1f}  "
            f"{row['score_quote']:>+9.1f}  "
            f"{row['divergencia']:>7.1f}  "
            f"{row['direcao']}{marca}"
        )

    melhor = top.iloc[0]
    print(f"\n  {'═'*60}")
    print(f"  MELHOR PAR  →  {melhor['par']}  |  {melhor['direcao']}")
    print(f"  Pips        :  {melhor['pips']:+.1f}")
    print(f"  Divergência :  {melhor['divergencia']:.1f} pips")
    print(f"  {'═'*60}")


def exibir_historico(historico: list[dict]) -> None:
    if not historico:
        return

    print(f"\n  HISTÓRICO DE HORAS — DIA ATUAL (BRT)")
    print("  " + SEP_FINA)

    header = f"  {'SLOT':<14}" + "".join(f"  {c:>{COL_W}}" for c in CURRENCIES)
    print(header)
    print("  " + "─" * 84)

    acum = {c: 0.0 for c in CURRENCIES}
    for h in historico:
        sc   = h["score"]
        slot = h["slot"]
        linha = f"  {slot:<14}"
        for c in CURRENCIES:
            v = sc.get(c, 0.0)
            acum[c] += v
            linha += f"  {v:>+{COL_W}.1f}"
        print(linha)

    print("  " + "─" * 84)
    linha_t = f"  {'ACUMULADO':<14}"
    for c in CURRENCIES:
        linha_t += f"  {acum[c]:>+{COL_W}.1f}"
    print(linha_t)


# ─────────────────────────────────────────────
# HORAS DO DIA CORRENTE
# ─────────────────────────────────────────────

def horas_completas_hoje(dados: dict[str, pd.Series]) -> list[dict]:
    """
    Calcula o score de cada hora completa já decorrida no dia de hoje (BRT).
    Retorna lista de {slot, dt_ini, dt_fim, score}.
    """
    agora = datetime.now(BRT)
    hoje  = agora.date()
    resultado = []

    for hora in range(0, agora.hour):   # somente horas já fechadas
        dt_ini = datetime(hoje.year, hoje.month, hoje.day, hora,     0, tzinfo=BRT)
        dt_fim = datetime(hoje.year, hoje.month, hoje.day, hora + 1, 0, tzinfo=BRT)
        _, sc = calcular_hora(dados, dt_ini, dt_fim)
        resultado.append({
            "slot" : f"{hora:02d}:00–{hora+1:02d}:00",
            "dt_ini": dt_ini,
            "dt_fim": dt_fim,
            "score" : sc.to_dict(),
        })

    return resultado


# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────

def main():
    pares = [f"{b}{q}" for b, q in itertools.permutations(CURRENCIES, 2)]

    print(SEP_LARGA)
    print("  FOREX HOURLY PIPS MONITOR")
    print(f"  Moedas : {', '.join(CURRENCIES)}")
    print(f"  Fuso   : America/Sao_Paulo (BRT = UTC-3)")
    print(f"  Update : a cada {SLEEP // 60} min  |  Ctrl+C para sair")
    print(SEP_LARGA)

    print("\nBaixando dados iniciais...")
    dados = baixar_todos(pares)

    while True:
        agora = datetime.now(BRT)
        print(f"\n{SEP_LARGA}")
        print(f"  Atualização: {agora.strftime('%Y-%m-%d %H:%M:%S')} BRT")
        print(SEP_LARGA)

        # ── Hora atual (parcial: início da hora corrente → agora) ────────
        ini_hora_atual = agora.replace(minute=0, second=0, microsecond=0)
        mat_atual, sc_atual = calcular_hora(dados, ini_hora_atual, agora)

        exibir_matriz(mat_atual,
                      f"HORA ATUAL  {ini_hora_atual.strftime('%H:%M')} – {agora.strftime('%H:%M')} BRT  (parcial)")
        exibir_score(sc_atual, "SCORE POR MOEDA — hora atual")
        top_atual = ranking_pares(mat_atual, sc_atual)
        exibir_ranking(top_atual, "TOP 10 PARES — hora atual")

        # ── Última hora completa ─────────────────────────────────────────
        if agora.hour > 0:
            fim_ant   = ini_hora_atual
            ini_ant   = fim_ant - timedelta(hours=1)
            mat_ant, sc_ant = calcular_hora(dados, ini_ant, fim_ant)
            label_ant = f"{ini_ant.strftime('%H:%M')} – {fim_ant.strftime('%H:%M')}"

            exibir_matriz(mat_ant, f"HORA ANTERIOR  {label_ant} BRT  (completa)")
            exibir_score_contagem(score_contagem(mat_ant), f"SCORE POR MOEDA — {label_ant}")
            top_ant = ranking_pares(mat_ant, sc_ant)
            exibir_ranking(top_ant, f"TOP 10 PARES — {label_ant}")

        # ── Histórico do dia ─────────────────────────────────────────────
        historico = horas_completas_hoje(dados)
        exibir_historico(historico)

        print(f"\n  Próxima atualização em {SLEEP // 60} min...")
        try:
            time.sleep(SLEEP)
        except KeyboardInterrupt:
            print("\n  Sistema encerrado.")
            break

        # Rebaixa os dados a cada ciclo para manter preços frescos
        print("\nAtualizando dados...")
        dados = baixar_todos(pares)


if __name__ == "__main__":
    main()
