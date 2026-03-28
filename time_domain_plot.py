import plotly.graph_objects as go
import numpy as np

def make_time_domain_plot(data):
    fig = go.Figure()

    # Continuous signal — blue line
    fig.add_trace(go.Scatter(
        x=data.time, y=data.signal,
        mode='lines', name='Continuous Signal',
        line=dict(color='royalblue', width=2)
    ))

    # Sampled points — orange dots
    fig.add_trace(go.Scatter(
        x=data.samples_t, y=data.samples_a,
        mode='markers', name='Samples',
        marker=dict(color='orange', size=8)
    ))

    # If aliasing, show reconstructed alias in red
    if data.aliased_freq > 0:
        alias_signal = np.sin(2 * np.pi * data.aliased_freq * data.time)
        fig.add_trace(go.Scatter(
            x=data.time, y=alias_signal,
            mode='lines', name=f'Alias ({data.aliased_freq:.1f} Hz)',
            line=dict(color='red', width=2, dash='dash')
        ))

    fig.update_layout(
        title="Time Domain",
        xaxis_title="Time (s)",
        yaxis_title="Amplitude",
        legend=dict(orientation="h", y=-0.2),
        height=350
    )

    return fig