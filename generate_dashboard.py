import argparse
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


def infer_datetime_column(df: pd.DataFrame) -> Optional[str]:
    """Identify a datetime-like column if one exists."""
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    for col in df.columns:
        lower = col.lower()
        if any(token in lower for token in ("date", "time", "timestamp")):
            converted = pd.to_datetime(df[col], errors="coerce")
            if converted.notna().sum() > len(df) * 0.5:
                df[col] = converted
                return col
    return None


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    time_col = infer_datetime_column(df)
    if time_col:
        df = df.sort_values(time_col)
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.set_index(time_col)
    return df


def create_time_series(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    fig = go.Figure()
    for col in numeric_cols:
        fig.add_trace(
            go.Scatter(
                x=df.index if df.index.is_all_dates else np.arange(len(df)),
                y=df[col],
                mode="lines",
                name=col,
            )
        )
    fig.update_layout(
        title="Évolution temporelle des variables clefs",
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h"),
    )
    return fig


def create_distribution_grid(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    cols = numeric_cols[:4]
    rows = int(np.ceil(len(cols) / 2)) or 1
    fig = make_subplots(rows=rows, cols=2, subplot_titles=cols)
    for i, col in enumerate(cols):
        row, col_idx = divmod(i, 2)
        hist = go.Histogram(x=df[col], nbinsx=40, name=col, marker_color="#7ed3f4", opacity=0.85)
        fig.add_trace(hist, row=row + 1, col=col_idx + 1)
        fig.update_xaxes(title_text=col, row=row + 1, col=col_idx + 1)
        fig.update_yaxes(title_text="Fréquence", row=row + 1, col=col_idx + 1)
    fig.update_layout(title="Distribution des paramètres (histogrammes)", template="plotly_dark", showlegend=False)
    return fig


def create_correlation_heatmap(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    corr = df[numeric_cols].corr()
    fig = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="Viridis",
        aspect="auto",
        title="Corrélations entre variables",
    )
    fig.update_layout(template="plotly_dark")
    return fig


def create_extremes_table(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    records = []
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue
        idx_max = series.idxmax()
        idx_min = series.idxmin()
        records.append(
            {
                "Variable": col,
                "Maximum": series.max(),
                "Date max": idx_max if not isinstance(idx_max, (int, float)) else "-",
                "Minimum": series.min(),
                "Date min": idx_min if not isinstance(idx_min, (int, float)) else "-",
                "Moyenne": series.mean(),
            }
        )
    table_df = pd.DataFrame(records)
    fig = go.Figure(
        go.Table(
            header=dict(values=list(table_df.columns), fill_color="#0f1c2e", font=dict(color="white", size=12)),
            cells=dict(
                values=[table_df[c] for c in table_df.columns],
                fill_color="#11263d",
                font=dict(color="white"),
            ),
        )
    )
    fig.update_layout(title="Synthèse statistiques (min/max/moyenne)")
    return fig


def create_rolling_trends(df: pd.DataFrame, numeric_cols: List[str]) -> go.Figure:
    fig = go.Figure()
    window = max(5, int(len(df) * 0.02))
    for col in numeric_cols[:3]:
        series = df[col].dropna()
        if series.empty:
            continue
        smoothed = series.rolling(window=window, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=series.index, y=smoothed, mode="lines", name=f"{col} (moy. glissante)"))
    fig.update_layout(
        title=f"Tendances lissées (fenêtre {window} points)",
        template="plotly_dark",
        hovermode="x unified",
    )
    return fig


def create_climatology(df: pd.DataFrame, numeric_cols: List[str]) -> Optional[go.Figure]:
    if not df.index.is_all_dates:
        return None
    monthly = df[numeric_cols].groupby(df.index.month).agg(["mean", "max", "min"])
    fig = make_subplots(rows=1, cols=1)
    for col in numeric_cols[:3]:
        fig.add_trace(
            go.Scatter(
                x=monthly.index,
                y=monthly[(col, "mean")],
                mode="lines+markers",
                name=f"{col} moyenne",
            )
        )
    fig.update_xaxes(title_text="Mois")
    fig.update_yaxes(title_text="Valeur moyenne")
    fig.update_layout(title="Cycle mensuel moyen", template="plotly_dark")
    return fig


def build_html(figures: List[go.Figure], output_path: Path) -> None:
    fragments = []
    for fig in figures:
        if fig is None:
            continue
        fragments.append(pio.to_html(fig, include_plotlyjs=False, full_html=False, default_height="520px"))

    html = f"""
<!DOCTYPE html>
<html lang=\"fr\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Tableau de bord hydrométéorologique</title>
    <script src=\"https://cdn.plot.ly/plotly-2.27.0.min.js\"></script>
    <style>
        body {{
            margin: 0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: radial-gradient(circle at 10% 20%, rgba(76,131,255,0.18), transparent 25%),
                        radial-gradient(circle at 80% 0%, rgba(93,230,255,0.15), transparent 25%),
                        #0b1224;
            color: #e8eef7;
        }}
        header {{
            padding: 32px 48px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        h1 {{
            margin: 0;
            font-size: 28px;
            letter-spacing: 0.5px;
        }}
        .pill {{
            padding: 10px 14px;
            background: linear-gradient(120deg, #2a5bd7, #13c1d6);
            border-radius: 999px;
            font-weight: 600;
            color: #0b1224;
            box-shadow: 0 8px 24px rgba(19,193,214,0.35);
        }}
        main {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 22px;
            padding: 0 32px 42px;
        }}
        .card {{
            background: linear-gradient(160deg, rgba(23,36,64,0.95), rgba(13,19,36,0.95));
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 16px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.35);
            padding: 12px;
            backdrop-filter: blur(8px);
        }}
        .card h2 {{
            margin: 12px 14px;
            font-size: 18px;
            color: #b6c8ff;
            letter-spacing: 0.3px;
        }}
        iframe {{ border: none; width: 100%; }}
    </style>
</head>
<body>
    <header>
        <h1>Dashboard hydrométéorologique interactif</h1>
        <div class=\"pill\">Analytique avancée</div>
    </header>
    <main>
        {''.join(f'<div class="card">{frag}</div>' for frag in fragments)}
    </main>
</body>
</html>
    """
    output_path.write_text(html, encoding="utf-8")


def generate_dashboard(input_path: Path, output_path: Path) -> None:
    df = pd.read_parquet(input_path)
    df = prepare_frame(df)
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        raise ValueError("Aucune colonne numérique détectée pour construire le dashboard.")

    figures = [
        create_time_series(df, numeric_cols),
        create_distribution_grid(df, numeric_cols),
        create_correlation_heatmap(df, numeric_cols),
        create_extremes_table(df, numeric_cols),
        create_rolling_trends(df, numeric_cols),
        create_climatology(df, numeric_cols),
    ]
    build_html(figures, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère un dashboard HTML à partir d'un fichier Parquet hydrométéorologique.")
    parser.add_argument("--input", type=Path, default=Path("donnees-hydrometeorologiques.parquet"), help="Chemin du fichier Parquet")
    parser.add_argument("--output", type=Path, default=Path("dashboard.html"), help="Chemin du fichier HTML à produire")
    args = parser.parse_args()
    generate_dashboard(args.input, args.output)
    print(f"Dashboard généré dans {args.output.resolve()}")
