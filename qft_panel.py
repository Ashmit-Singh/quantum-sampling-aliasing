import plotly.graph_objects as go

def make_qft_panel(qft_data, fft_data):
    col_labels = qft_data.basis_states

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=col_labels, y=qft_data.amplitudes,
        name='QFT (Quantum)',
        marker_color='mediumpurple'
    ))

    fig.update_layout(
        title=f"Quantum Fourier Transform ({qft_data.n_qubits} qubits)",
        xaxis_title="Basis State",
        yaxis_title="Probability Amplitude",
        height=350
    )

    return fig