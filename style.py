"""Dark, animated, professional theme: CSS injection + shared Plotly template."""
import plotly.graph_objects as go
import plotly.io as pio

ACCENT = "#00E0A4"
ACCENT2 = "#7C4DFF"
BG = "#0E1117"
CARD = "#161B22"
DANGER = "#FF5C5C"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.stApp {{ background: radial-gradient(circle at 20% 0%, #131722 0%, {BG} 55%); }}

@keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes pulseGlow {{
    0%, 100% {{ box-shadow: 0 0 0 rgba(0,224,164,0.0); }}
    50% {{ box-shadow: 0 0 18px rgba(0,224,164,0.35); }}
}}

.metric-card {{
    background: linear-gradient(145deg, {CARD} 0%, #10151c 100%);
    border: 1px solid rgba(0,224,164,0.15);
    border-radius: 16px;
    padding: 18px 20px;
    animation: fadeInUp 0.5s ease-out, pulseGlow 4s ease-in-out infinite;
    transition: transform 0.2s ease, border-color 0.2s ease;
}}
.metric-card:hover {{ transform: translateY(-3px); border-color: rgba(0,224,164,0.5); }}
.metric-label {{ color: #8b949e; font-size: 0.8rem; letter-spacing: 0.05em; text-transform: uppercase; }}
.metric-value {{ font-size: 1.9rem; font-weight: 800; margin-top: 4px; }}
.metric-positive {{ color: {ACCENT}; }}
.metric-negative {{ color: {DANGER}; }}

.app-title {{
    font-weight: 800; font-size: 2.1rem;
    background: linear-gradient(90deg, {ACCENT}, {ACCENT2});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    animation: fadeInUp 0.6s ease-out;
}}
.section-fade {{ animation: fadeInUp 0.5s ease-out; }}

div[data-testid="stSidebar"] {{ background: #0B0E14; border-right: 1px solid rgba(255,255,255,0.06); }}

.stButton>button {{
    border-radius: 10px; border: 1px solid rgba(0,224,164,0.35);
    background: linear-gradient(135deg, rgba(0,224,164,0.12), rgba(124,77,255,0.12));
    color: #E6EDF3; transition: all 0.2s ease; font-weight: 600;
}}
.stButton>button:hover {{ border-color: {ACCENT}; box-shadow: 0 0 14px rgba(0,224,164,0.35); }}

[data-testid="stDataFrame"] {{ animation: fadeInUp 0.5s ease-out; }}

.anomaly-badge {{
    background: rgba(255,92,92,0.15); color: {DANGER}; border: 1px solid rgba(255,92,92,0.4);
    border-radius: 8px; padding: 2px 8px; font-size: 0.75rem; font-weight: 600;
}}
</style>
"""


def inject_css(st):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def metric_card_html(label, value, positive=True):
    cls = "metric-positive" if positive else "metric-negative"
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {cls}">{value}</div>
    </div>
    """


def apply_plotly_theme(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(family="Inter, sans-serif", color="#E6EDF3"),
        colorway=[ACCENT, ACCENT2, "#FFB84D", "#FF5C5C", "#4DA6FF", "#FF7CE0", "#7CFFB2"],
        margin=dict(l=10, r=10, t=50, b=10),
        transition=dict(duration=500, easing="cubic-in-out"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="top", y=-0.30, xanchor="center", x=0.5),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig
