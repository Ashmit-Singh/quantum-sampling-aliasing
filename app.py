import streamlit as st
from mock_data import get_mock_signal, get_mock_qft
from ui_components import show_aliasing_alert, show_signal_stats
from time_domain_plot import make_time_domain_plot
from frequency_plot import make_frequency_plot
from qft_panel import make_qft_panel

st.set_page_config(page_title="Quantum Sampling Demo", layout="wide", page_icon="⚛️")

st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #6C63FF, #48CAE4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitle {
        color: #888;
        font-size: 1rem;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }
    .preset-label {
        font-size: 0.85rem;
        color: #aaa;
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">⚛️ Quantum-Enhanced Sampling & Aliasing Demonstrator</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Explore how sampling rate affects signal quality — with a quantum computing twist</p>', unsafe_allow_html=True)

# Preset buttons
st.markdown('<p class="preset-label">Quick Presets — click to load a demo scenario:</p>', unsafe_allow_html=True)
col_p1, col_p2, col_p3, col_p4, _ = st.columns([1, 1, 1, 1, 3])

if "f" not in st.session_state:
    st.session_state.f = 5
    st.session_state.fs = 20
    st.session_state.signal_type = "sine"

with col_p1:
    if st.button("✅ Normal", use_container_width=True):
        st.session_state.f = 5
        st.session_state.fs = 40
        st.session_state.signal_type = "sine"
with col_p2:
    if st.button("⚡ Nyquist Edge", use_container_width=True):
        st.session_state.f = 5
        st.session_state.fs = 10
        st.session_state.signal_type = "sine"
with col_p3:
    if st.button("⚠️ Aliasing", use_container_width=True):
        st.session_state.f = 5
        st.session_state.fs = 7
        st.session_state.signal_type = "sine"
with col_p4:
    if st.button("🔬 Oversampling", use_container_width=True):
        st.session_state.f = 5
        st.session_state.fs = 100
        st.session_state.signal_type = "sine"

st.divider()

# Sidebar
st.sidebar.header("⚙️ Signal Controls")
st.sidebar.caption("Adjust manually or use the preset buttons above")

signal_type = st.sidebar.selectbox(
    "Signal Type",
    ["sine", "square", "triangle"],
    index=["sine", "square", "triangle"].index(st.session_state.signal_type)
)
f = st.sidebar.slider("Signal Frequency (Hz)", min_value=1, max_value=20, value=st.session_state.f)
fs = st.sidebar.slider("Sampling Rate (Hz)", min_value=2, max_value=100, value=st.session_state.fs)
amplitude = st.sidebar.slider("Amplitude", min_value=0.1, max_value=2.0, value=1.0, step=0.1)

st.sidebar.divider()
st.sidebar.markdown("**📊 What you're seeing**")
st.sidebar.caption("**Blue line** — the original continuous signal")
st.sidebar.caption("**Orange dots** — the discrete samples taken at rate fs")
st.sidebar.caption("**Red dashed line** — the aliased signal (only appears when fs < 2f)")
st.sidebar.caption("**Purple bars** — quantum frequency representation via QFT")

# Get data
data = get_mock_signal(f=f, fs=fs, signal_type=signal_type)
qft_data = get_mock_qft(n_qubits=3)

# Alert + stats
show_aliasing_alert(fs, f)
st.divider()
show_signal_stats(data)
st.divider()

# Charts
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(make_time_domain_plot(data), use_container_width=True)
with col2:
    st.plotly_chart(make_frequency_plot(data), use_container_width=True)

st.divider()

st.subheader("Quantum Fourier Transform Comparison")