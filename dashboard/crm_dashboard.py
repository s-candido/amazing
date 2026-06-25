"""
CRM Dashboard - Clustering Model Benchmark
Visualises clustering quality metrics from JSON result files.
"""

import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CRM Dashboard - Model Benchmark",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths & constants ─────────────────────────────────────────────────────────
RESULTS_DIR = Path(__file__).parent.parent / "dags" / "src" / "data_folder" / "results"

_MONTH_ORDER = [
    "2019-Oct", "2019-Nov", "2019-Dec",
    "2020-Jan", "2020-Feb", "2020-Mar",
]

_MODEL_COLORS = {
    "Agglomerative": "#e74c3c",
    "Birch":         "#3498db",
    "DBSCAN":        "#2ecc71",
    "GMM":           "#f39c12",
    "KMeans":        "#9b59b6",
}

METRICS = {
    "Silhouette Score":        {"higher_better": True,  "fmt": ".4f"},
    "Davies-Bouldin Index":    {"higher_better": False, "fmt": ".4f"},
    "Calinski-Harabasz Score": {"higher_better": True,  "fmt": ",.0f"},
    "N Clusters":              {"higher_better": None,  "fmt": ".0f"},
}

# ── Data loader ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_benchmark() -> pd.DataFrame:
    """Parse all clustering_results_*.json files into a tidy DataFrame."""
    rows = []
    if not RESULTS_DIR.exists():
        return pd.DataFrame()

    for json_file in sorted(RESULTS_DIR.glob("clustering_results_*.json")):
        with open(json_file, "r") as fh:
            data = json.load(fh)

        date_part = data.get("csv_file", "").replace("-10pct", "")

        for model_name, model_data in data.get("results", {}).items():
            m = model_data.get("metrics", {})
            params = model_data.get("params", {})
            rows.append(
                {
                    "date":                    date_part,
                    "model":                   model_name,
                    "Silhouette Score":        m.get("Silhouette Score"),
                    "Davies-Bouldin Index":    m.get("Davies-Bouldin Index"),
                    "Calinski-Harabasz Score": m.get("Calinski-Harabasz Score"),
                    "N Clusters":              m.get("N Clusters"),
                    "unique_users":            data.get("unique_users"),
                    "total_records":           data.get("total_records"),
                    "params":                  str(params),
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["date"] = pd.Categorical(df["date"], categories=_MONTH_ORDER, ordered=True)
    df = df.sort_values(["date", "model"]).reset_index(drop=True)
    return df


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.title("🔬 Clustering Model Benchmark")
    st.markdown(
        "Compare **clustering quality metrics** across models and months "
        "to identify the best segmentation algorithm for user profiling."
    )

    df = load_benchmark()

    if df.empty:
        st.error(
            f"No clustering result JSON files found.\n\n"
            f"Expected location: `{RESULTS_DIR}`"
        )
        return

    # ── Sidebar filters ───────────────────────────────────────────────────────
    st.sidebar.header("⚙️ Filters")

    all_models = sorted(df["model"].unique().tolist())
    selected_models = st.sidebar.multiselect(
        "Models", all_models, default=all_models
    )

    all_months = [m for m in _MONTH_ORDER if m in df["date"].cat.categories]
    selected_months = st.sidebar.multiselect(
        "Months", all_months, default=all_months
    )

    filtered = df[
        df["model"].isin(selected_models) & df["date"].isin(selected_months)
    ]

    if filtered.empty:
        st.warning("No data matches the selected filters.")
        return

    # ── Summary cards ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Months", len(filtered["date"].unique()))
    c2.metric("Models", len(filtered["model"].unique()))
    c3.metric("Evaluations", len(filtered))
    sample_users = filtered["unique_users"].dropna()
    c4.metric(
        "Avg unique users / month",
        f"{int(sample_users.mean()):,}" if not sample_users.empty else "—",
    )

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Evolution",
        "📦 Box plots",
        "🏆 Rankings",
        "📋 Raw data",
    ])

    # ── TAB 1 : line charts ───────────────────────────────────────────────────
    with tab1:
        st.markdown("### Metric evolution across months")
        st.caption("Each line = one model. Points are the observed value per month.")

        score_metrics = [k for k, v in METRICS.items() if v["higher_better"] is not None]
        cols = st.columns(2)
        for i, metric in enumerate(score_metrics):
            info = METRICS[metric]
            direction = "↑ higher is better" if info["higher_better"] else "↓ lower is better"
            fig = px.line(
                filtered,
                x="date",
                y=metric,
                color="model",
                color_discrete_map=_MODEL_COLORS,
                markers=True,
                title=f"{metric}  ({direction})",
                labels={"date": "Month", metric: metric, "model": "Model"},
                hover_data=["N Clusters", "unique_users"],
            )
            fig.update_traces(line_width=2.5, marker_size=9)
            fig.update_layout(
                height=380,
                xaxis_title="Month",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            cols[i % 2].plotly_chart(fig, use_container_width=True)

        # N Clusters full-width
        fig_nc = px.line(
            filtered,
            x="date",
            y="N Clusters",
            color="model",
            color_discrete_map=_MODEL_COLORS,
            markers=True,
            title="N Clusters per month",
            labels={"date": "Month", "N Clusters": "N Clusters", "model": "Model"},
        )
        fig_nc.update_traces(line_width=2.5, marker_size=9)
        fig_nc.update_layout(
            height=340,
            xaxis_title="Month",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_nc, use_container_width=True)

    # ── TAB 2 : box plots ─────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Metric distribution across months per model")
        st.caption(
            "Each box shows the spread of a metric over all selected months for that model. "
            "Individual points are months. Narrow box = stable model."
        )

        for metric, info in METRICS.items():
            direction = (
                "↑ higher is better" if info["higher_better"]
                else "↓ lower is better" if info["higher_better"] is False
                else ""
            )
            note = f"  ({direction})" if direction else ""
            fig = px.box(
                filtered,
                x="model",
                y=metric,
                color="model",
                color_discrete_map=_MODEL_COLORS,
                points="all",
                hover_data=["date"],
                title=f"{metric}{note}",
                labels={"model": "Model", metric: metric},
            )
            fig.update_layout(height=420, showlegend=False, xaxis_title="Model")
            st.plotly_chart(fig, use_container_width=True)

    # ── TAB 3 : rankings ──────────────────────────────────────────────────────
    with tab3:
        st.markdown("### Model rankings (averaged across selected months)")

        score_metrics = ["Silhouette Score", "Davies-Bouldin Index", "Calinski-Harabasz Score"]
        agg = filtered.groupby("model")[score_metrics].mean().reset_index()

        for metric, info in METRICS.items():
            if metric not in agg.columns or info["higher_better"] is None:
                continue
            agg[f"rank_{metric}"] = agg[metric].rank(
                ascending=not info["higher_better"], method="min"
            ).astype(int)

        rank_cols = [c for c in agg.columns if c.startswith("rank_")]
        agg["Avg Rank ⭐"] = agg[rank_cols].mean(axis=1).round(2)
        agg = agg.sort_values("Avg Rank ⭐")

        display_df = agg.copy()
        for metric in score_metrics:
            if metric in display_df.columns:
                if METRICS[metric]["fmt"] == ",.0f":
                    display_df[metric] = display_df[metric].map(lambda v: f"{v:,.0f}")
                else:
                    display_df[metric] = display_df[metric].map(lambda v: f"{v:.4f}")

        rename_map = {
            "model":                        "Model",
            "Silhouette Score":             "Silhouette (avg)",
            "Davies-Bouldin Index":         "D-B Index (avg)",
            "Calinski-Harabasz Score":      "C-H Score (avg)",
            "rank_Silhouette Score":        "Rank Sil.",
            "rank_Davies-Bouldin Index":    "Rank D-B",
            "rank_Calinski-Harabasz Score": "Rank C-H",
            "Avg Rank ⭐":                  "Avg Rank ⭐",
        }
        display_df = display_df.rename(columns=rename_map)
        display_cols = [c for c in rename_map.values() if c in display_df.columns]

        st.dataframe(display_df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("#### Average metric value per model")
        rcols = st.columns(2)
        for i, metric in enumerate(score_metrics):
            info = METRICS[metric]
            avg_df = filtered.groupby("model")[metric].mean().reset_index()
            avg_df = avg_df.sort_values(metric, ascending=not info["higher_better"])
            direction = "↑ higher is better" if info["higher_better"] else "↓ lower is better"
            fig = px.bar(
                avg_df,
                x="model",
                y=metric,
                color="model",
                color_discrete_map=_MODEL_COLORS,
                title=f"{metric} — avg ({direction})",
                labels={"model": "Model", metric: metric},
                text_auto=".4f",
            )
            fig.update_layout(height=340, showlegend=False)
            rcols[i % 2].plotly_chart(fig, use_container_width=True)

    # ── TAB 4 : raw data ──────────────────────────────────────────────────────
    with tab4:
        st.markdown("### Raw benchmark data")
        display = filtered.drop(columns=["params"]).copy()
        for col in ["Silhouette Score", "Davies-Bouldin Index"]:
            if col in display.columns:
                display[col] = display[col].map(lambda v: round(v, 6) if pd.notna(v) else v)

        st.dataframe(display, use_container_width=True, hide_index=True)

        csv = display.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            data=csv,
            file_name="clustering_benchmark.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
