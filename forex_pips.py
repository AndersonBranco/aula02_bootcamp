import yfinance as yf
import pandas as pd
import numpy as np
import itertools
from datetime import datetime, date, timedelta

from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]

BRT = ZoneInfo("America/Sao_Paulo")   # UTC-3 (sem horário de verão desde 2019)

HORA_INI = 7    # 07:00 BRT
HORA_FIM = 13   # 13:00 BRT  →  slots: 07-08, 08-09, 09-10, 10-11, 11-12, 12-13

DIAS_NOMES = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
DIAS_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def pip_size(base: str, quote: str) -> float:
    return 0.01 if "JPY" in (base, quote) else 0.0001


# ─────────────────────────────────────────────
# DIAS ÚTEIS
# ─────────────────────────────────────────────

def ultimos_dias_uteis(n: int = 3) -> list[date]:
    """Retorna os últimos n dias úteis (seg–sex) em ordem crescente."""
    dias = []
    d = date.today()
    # se hoje ainda não chegou às 7h BRT, não conta o dia de hoje
    agora_brt = datetime.now(BRT)
    if agora_brt.hour < HORA_INI:
        d -= timedelta(days=1)
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    return sorted(dias)


# ─────────────────────────────────────────────
# DOWNLOAD — um único fetch por par (5 dias, 5min)
# ─────────────────────────────────────────────

def baixar_todos(pares: list[str]) -> dict[str, pd.Series]:
    """
    Baixa candles de 5min (últimos 5 dias) para cada par.
    Retorna dict {par: Series(close, index tz=BRT)}.
    """
    dados: dict[str, pd.Series] = {}
    total = len(pares)

    for i, par in enumerate(pares, 1):
        print(f"\r  Baixando {i}/{total}  ({par})    ", end="", flush=True)
        try:
            df = yf.download(par + "=X", period="5d", interval="5m",
                             progress=False, auto_adjust=True)
            if df.empty:
                continue

            close = df["Close"].squeeze().dropna()
            if not isinstance(close, pd.Series):
                continue

            # garantir tz UTC → converter para BRT
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
    """Preço do candle mais próximo em ou antes de dt."""
    candidatos = serie[serie.index <= dt]
    if candidatos.empty:
        return None
    return float(np.asarray(candidatos.iloc[-1]).flat[0])


# ─────────────────────────────────────────────
# SCORE DE MOEDAS NUM SLOT DE TEMPO
# ─────────────────────────────────────────────

def scores_slot(dados: dict[str, pd.Series],
                dt_ini: datetime, dt_fim: datetime) -> dict[str, float]:
    """
    Calcula o score (pips médios ganhos/perdidos) de cada moeda
    no intervalo [dt_ini, dt_fim].
    """
    acum  = {c: 0.0 for c in CURRENCIES}
    count = {c: 0   for c in CURRENCIES}

    for base, quote in itertools.permutations(CURRENCIES, 2):
        par = base + quote
        if par not in dados:
            continue

        p_ini = preco_em(dados[par], dt_ini)
        p_fim = preco_em(dados[par], dt_fim)

        if p_ini is None or p_fim is None or p_ini <= 0:
            continue

        pips = (p_fim - p_ini) / pip_size(base, quote)

        acum[base]  += pips
        acum[quote] -= pips
        count[base]  += 1
        count[quote] += 1

    resultado = {}
    for c in CURRENCIES:
        resultado[c] = round(acum[c] / count[c], 1) if count[c] > 0 else 0.0
    return resultado


# ─────────────────────────────────────────────
# EXIBIÇÃO DE UM DIA
# ─────────────────────────────────────────────

def exibir_dia(dia: date, dados: dict[str, pd.Series]) -> dict[str, float]:
    """
    Exibe a tabela horária de um dia e retorna o score total 07:00–13:00.
    """
    nome = DIAS_NOMES[dia.weekday()]
    sep  = "─" * 82

    print(f"\n{'═'*82}")
    print(f"  {dia.strftime('%Y-%m-%d')}  ({nome})  │  Janela: {HORA_INI:02d}:00 – {HORA_FIM:02d}:00 BRT")
    print(f"{'═'*82}")

    col_w = 8
    header = f"  {'SLOT':<14}" + "".join(f"  {c:>{col_w}}" for c in CURRENCIES)
    print(header)
    print("  " + sep)

    scores_acum = {c: 0.0 for c in CURRENCIES}

    # ── linha por hora ──────────────────────────────────────────────────
    for hora in range(HORA_INI, HORA_FIM):
        dt_ini = datetime(dia.year, dia.month, dia.day, hora,     0, tzinfo=BRT)
        dt_fim = datetime(dia.year, dia.month, dia.day, hora + 1, 0, tzinfo=BRT)

        sc = scores_slot(dados, dt_ini, dt_fim)

        linha = f"  {hora:02d}:00 – {hora+1:02d}:00"
        for c in CURRENCIES:
            v = sc[c]
            scores_acum[c] += v
            cell = f"{v:>+{col_w}.1f}"
            linha += f"  {cell}"
        print(linha)

    # ── total do dia (calculado diretamente 07:00→13:00) ────────────────
    dt_abertura   = datetime(dia.year, dia.month, dia.day, HORA_INI, 0, tzinfo=BRT)
    dt_fechamento = datetime(dia.year, dia.month, dia.day, HORA_FIM, 0, tzinfo=BRT)
    score_total = scores_slot(dados, dt_abertura, dt_fechamento)

    print("  " + sep)
    linha_t = f"  {'TOTAL 07–13':<14}"
    for c in CURRENCIES:
        v = score_total[c]
        cell = f"{v:>+{col_w}.1f}"
        linha_t += f"  {cell}"
    print(linha_t)

    # ── moeda mais forte e mais fraca no dia ────────────────────────────
    serie = pd.Series(score_total).sort_values(ascending=False)
    print(f"\n  Mais forte  : {serie.index[0]}  ({serie.iloc[0]:+.1f} pips)")
    print(f"  Mais fraca  : {serie.index[-1]}  ({serie.iloc[-1]:+.1f} pips)")

    return score_total


# ─────────────────────────────────────────────
# RESUMO COMPARATIVO E MELHOR PAR
# ─────────────────────────────────────────────

def exibir_resumo(dias: list[date],
                  totais: dict[date, dict[str, float]]) -> None:
    """Tabela comparativa dos 3 dias + melhor par acumulado."""

    print(f"\n{'═'*82}")
    print("  RESUMO — SCORE TOTAL 07:00–13:00 BRT  (pips médios por dia)")
    print(f"{'═'*82}")

    col_w = 8
    header = f"  {'DATA':<16}" + "".join(f"  {c:>{col_w}}" for c in CURRENCIES)
    print(header)
    print("  " + "─" * 82)

    acum_geral = {c: 0.0 for c in CURRENCIES}

    for dia in dias:
        abrev = DIAS_ABREV[dia.weekday()]
        linha = f"  {dia.strftime('%Y-%m-%d')} {abrev:<4}"
        for c in CURRENCIES:
            v = totais[dia][c]
            acum_geral[c] += v
            linha += f"  {v:>+{col_w}.1f}"
        print(linha)

    # média dos 3 dias
    print("  " + "─" * 82)
    linha_m = f"  {'MÉDIA 3 DIAS':<16}"
    for c in CURRENCIES:
        v = round(acum_geral[c] / len(dias), 1)
        linha_m += f"  {v:>+{col_w}.1f}"
    print(linha_m)

    # ── melhor par acumulado ─────────────────────────────────────────────
    media = {c: round(acum_geral[c] / len(dias), 1) for c in CURRENCIES}
    serie = pd.Series(media).sort_values(ascending=False)

    mais_forte = serie.index[0]
    mais_fraca  = serie.index[-1]
    melhor_par  = mais_forte + mais_fraca
    gap         = round(serie.iloc[0] - serie.iloc[-1], 1)

    print(f"\n{'═'*82}")
    print(f"  MELHOR PAR (média 3 dias)  →  {melhor_par}")
    print(f"  Direção     :  LONG {mais_forte} / SHORT {mais_fraca}")
    print(f"  Divergência :  {gap:+.1f} pips  (média 07:00–13:00 BRT)")
    print(f"{'═'*82}\n")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print("\nFOREX PIPS  —  Últimos 3 dias úteis  │  07:00–13:00 BRT")
    print(f"Moedas : {', '.join(CURRENCIES)}")
    print(f"Fuso   : America/Sao_Paulo (BRT = UTC-3)\n")

    dias = ultimos_dias_uteis(3)
    print(f"Dias   : {', '.join(d.strftime('%Y-%m-%d (%a)') for d in dias)}\n")

    pares = [f"{b}{q}" for b, q in itertools.permutations(CURRENCIES, 2)]
    dados = baixar_todos(pares)

    totais: dict[date, dict[str, float]] = {}
    for dia in dias:
        totais[dia] = exibir_dia(dia, dados)

    exibir_resumo(dias, totais)


if __name__ == "__main__":
    main()
