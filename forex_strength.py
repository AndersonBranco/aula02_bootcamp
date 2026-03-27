import yfinance as yf
import pandas as pd
import numpy as np
import itertools
import time
from datetime import datetime

# ─────────────────────────────────────────────
# MOEDAS E PESOS DE LIQUIDEZ
# ─────────────────────────────────────────────
CURRENCIES = {
    "USD": 1.00,
    "EUR": 0.90,
    "JPY": 0.80,
    "GBP": 0.75,
    "CHF": 0.65,
    "AUD": 0.55,
    "CAD": 0.55,
    "NZD": 0.45,
}

# ─────────────────────────────────────────────
# TIMEFRAMES
# Cada TF define quantos candles de 30min usar
# e o peso na composição do score final
# (candles mais recentes = mais peso)
# ─────────────────────────────────────────────
TIMEFRAMES = {
    "4h":  {"candles": 8,  "peso_tf": 0.25},   # 8 × 30min = 4h
    "1h":  {"candles": 2,  "peso_tf": 0.35},   # 2 × 30min = 1h
    "30m": {"candles": 1,  "peso_tf": 0.40},   # 1 × 30min = 30min
}

SLEEP = 300  # segundos entre atualizações


# ─────────────────────────────────────────────
# COLETA DE DADOS
# ─────────────────────────────────────────────

def gerar_pares(currencies: dict) -> list[str]:
    return [f"{b}{q}" for b, q in itertools.permutations(currencies.keys(), 2)]


def baixar_close(par: str) -> pd.Series | None:
    """Baixa série de fechamento em candles de 30min (últimos 2 dias)."""
    ticker = par + "=X"
    try:
        df = yf.download(ticker, period="2d", interval="30m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 10:
            return None
        # yfinance recente retorna MultiIndex — squeeze() garante Series 1D
        close = df["Close"].squeeze().dropna()
        if not isinstance(close, pd.Series):
            return None
        return close
    except Exception:
        return None


def retorno_acumulado(close: pd.Series, n_candles: int) -> float | None:
    """Log-retorno acumulado dos últimos n_candles."""
    if len(close) < n_candles + 1:
        return None
    try:
        preco_ini = float(np.asarray(close.iloc[-(n_candles + 1)]).flat[0])
        preco_fim = float(np.asarray(close.iloc[-1]).flat[0])
    except (TypeError, IndexError):
        return None
    if preco_ini <= 0:
        return None
    return float(np.log(preco_fim / preco_ini))


# ─────────────────────────────────────────────
# CÁLCULO DE FORÇA POR TIMEFRAME
# ─────────────────────────────────────────────

def calcular_forca_tf(pares: list[str], n_candles: int) -> pd.Series:
    """
    Força de cada moeda baseada no retorno acumulado dos últimos n_candles (30min cada).
    O retorno é ponderado pelo peso de liquidez médio do par.
    """
    strength = {c: 0.0 for c in CURRENCIES}
    counts   = {c: 0   for c in CURRENCIES}

    for par in pares:
        base  = par[:3]
        quote = par[3:]

        close = baixar_close(par)
        if close is None:
            continue

        ret = retorno_acumulado(close, n_candles)
        if ret is None:
            continue

        peso = (CURRENCIES[base] + CURRENCIES[quote]) / 2.0

        strength[base]  += ret * peso
        strength[quote] -= ret * peso
        counts[base]    += 1
        counts[quote]   += 1

    for c in CURRENCIES:
        if counts[c] > 0:
            strength[c] /= counts[c]

    return pd.Series(strength)


def calcular_forca_combinada(pares: list[str]) -> tuple[dict[str, pd.Series], pd.Series]:
    """
    Calcula força para cada TF e retorna:
      - dict com a força por timeframe
      - série combinada (média ponderada pelos pesos de TF)
    """
    forcas_tf: dict[str, pd.Series] = {}

    print("  Coletando dados", end="", flush=True)
    for label, cfg in TIMEFRAMES.items():
        print(f" [{label}]", end="", flush=True)
        forcas_tf[label] = calcular_forca_tf(pares, cfg["candles"])
    print()

    # combinação ponderada
    combinada = pd.Series({c: 0.0 for c in CURRENCIES})
    for label, cfg in TIMEFRAMES.items():
        combinada += forcas_tf[label] * cfg["peso_tf"]

    return forcas_tf, combinada.sort_values(ascending=False)


# ─────────────────────────────────────────────
# AVALIAÇÃO DE PARES
# ─────────────────────────────────────────────

def avaliar_pares(strength_combined: pd.Series,
                  forcas_tf: dict[str, pd.Series]) -> pd.DataFrame:
    """
    Para cada par calcula gap (base - quote) em cada TF,
    além do score final ponderado pelo peso de liquidez do par.
    """
    registros = []

    for base, quote in itertools.permutations(CURRENCIES.keys(), 2):
        gap_combinado = strength_combined[base] - strength_combined[quote]
        peso_par      = (CURRENCIES[base] + CURRENCIES[quote]) / 2.0
        score         = abs(gap_combinado) * peso_par
        direcao       = f"LONG  {base}" if gap_combinado > 0 else f"SHORT {base}"

        row = {
            "par"          : base + quote,
            "score"        : round(score, 6),
            "gap_combined" : round(gap_combinado, 6),
            "peso_par"     : round(peso_par, 2),
            "direcao"      : direcao,
        }

        # gaps individuais por TF
        for label in TIMEFRAMES:
            gap_tf = forcas_tf[label][base] - forcas_tf[label][quote]
            row[f"gap_{label}"] = round(gap_tf, 6)

        registros.append(row)

    df = pd.DataFrame(registros)
    df.sort_values("score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ─────────────────────────────────────────────
# EXIBIÇÃO
# ─────────────────────────────────────────────

def barra(valor: float, escala: float = 8000, largura: int = 12) -> str:
    """Barra visual proporcional ao valor."""
    n = min(int(abs(valor) * escala), largura)
    sinal = "+" if valor >= 0 else "-"
    return sinal + "█" * n


def exibir(forcas_tf: dict[str, pd.Series],
           strength_combined: pd.Series,
           pares_df: pd.DataFrame) -> None:

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 72

    print(f"\n{sep}")
    print(f"  FOREX STRENGTH METER  —  {now}")
    print(sep)

    # ── Força por timeframe ──────────────────────────────────────────────
    print(f"\n{'MOEDA':<6} {'PESO':>5}  {'30m':>10}  {'1h':>10}  {'4h':>10}  {'COMBINADO':>10}  TENDÊNCIA")
    print("─" * 72)

    for moeda in strength_combined.index:
        peso = CURRENCIES[moeda]
        f30  = forcas_tf["30m"][moeda]
        f1h  = forcas_tf["1h"][moeda]
        f4h  = forcas_tf["4h"][moeda]
        fc   = strength_combined[moeda]

        # alinhamento de tendência entre TFs
        sinais = [np.sign(f30), np.sign(f1h), np.sign(f4h)]
        if all(s > 0 for s in sinais):
            tendencia = "↑ forte"
        elif all(s < 0 for s in sinais):
            tendencia = "↓ fraco"
        elif sinais[0] > 0:
            tendencia = "↑ acele"
        elif sinais[0] < 0:
            tendencia = "↓ acele"
        else:
            tendencia = "~ neutro"

        print(
            f"{moeda:<6} {peso:>5.2f}  "
            f"{f30:>+10.6f}  "
            f"{f1h:>+10.6f}  "
            f"{f4h:>+10.6f}  "
            f"{fc:>+10.6f}  "
            f"{tendencia}"
        )

    # ── Top 10 pares ─────────────────────────────────────────────────────
    print(f"\n{'─'*72}")
    print("  TOP 10 PARES  (score = |gap_combinado| × peso_liquidez)\n")
    print(
        f"  {'#':<3} {'PAR':<8} {'SCORE':>8}  "
        f"{'GAP 30m':>9}  {'GAP 1h':>9}  {'GAP 4h':>9}  "
        f"{'PESO':>5}  DIREÇÃO"
    )
    print("  " + "─" * 68)

    for i, row in pares_df.head(10).iterrows():
        alinhado = (
            np.sign(row["gap_30m"]) == np.sign(row["gap_1h"]) ==
            np.sign(row["gap_4h"])
        )
        marca = " ★" if alinhado else "  "
        print(
            f"  {i+1:<3} {row['par']:<8} {row['score']:>8.6f}  "
            f"{row['gap_30m']:>+9.6f}  "
            f"{row['gap_1h']:>+9.6f}  "
            f"{row['gap_4h']:>+9.6f}  "
            f"{row['peso_par']:>5.2f}  {row['direcao']}{marca}"
        )

    # ── Melhor trade ──────────────────────────────────────────────────────
    melhor = pares_df.iloc[0]
    alinhado_melhor = (
        np.sign(melhor["gap_30m"]) == np.sign(melhor["gap_1h"]) ==
        np.sign(melhor["gap_4h"])
    )
    confirmacao = "TODOS OS TFs ALINHADOS ★" if alinhado_melhor else "TFs divergentes — atenção"

    print(f"\n{'═'*72}")
    print(f"  MELHOR PAR AGORA  →  {melhor['par']}")
    print(f"  Direção    : {melhor['direcao']}")
    print(f"  Score      : {melhor['score']:.6f}")
    print(f"  Gap 30m    : {melhor['gap_30m']:+.6f}")
    print(f"  Gap  1h    : {melhor['gap_1h']:+.6f}")
    print(f"  Gap  4h    : {melhor['gap_4h']:+.6f}")
    print(f"  Sinal      : {confirmacao}")
    print(f"{'═'*72}\n")


# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────

def main():
    pares = gerar_pares(CURRENCIES)
    n_pares = len(pares)
    print(f"\nMonitorando {n_pares} pares  |  TFs: 30m / 1h / 4h")
    print("Pesos TF → 30m: 40%  1h: 35%  4h: 25%")
    print("Pressione Ctrl+C para encerrar.\n")

    while True:
        try:
            forcas_tf, combinada = calcular_forca_combinada(pares)
            pares_df = avaliar_pares(combinada, forcas_tf)
            exibir(forcas_tf, combinada, pares_df)
        except KeyboardInterrupt:
            print("\nSistema encerrado.")
            break
        except Exception as e:
            print(f"Erro no ciclo: {e}")

        print(f"Próxima atualização em {SLEEP // 60} min...")
        time.sleep(SLEEP)


if __name__ == "__main__":
    main()
