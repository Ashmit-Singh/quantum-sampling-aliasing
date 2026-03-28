import plotly.graph_objects as go

def make_frequency_plot(data):
    fig = go.Figure()

    # FFT bars
    fig.add_trace(go.Bar(
        x=data.fft_freqs, y=data.fft_mags,
        name='FFT Magnitude',
        marker_color='royalblue'
    ))

    # Nyquist line
    nyquist = data.fs / 2
    fig.add_vline(
        x=nyquist, line_dash="dash", line_color="orange",
        annotation_text=f"Nyquist ({nyquist} Hz)", annotation_position="top right"
    )

    # Aliased frequency marker
    if data.aliased_freq > 0:
        fig.add_vline(
            x=data.aliased_freq, line_dash="dot", line_color="red",
            annotation_text=f"Alias ({data.aliased_freq:.1f} Hz)", annotation_position="top left"
        )

    fig.update_layout(
        title="Frequency Domain (FFT)",
        xaxis_title="Frequency (Hz)",
        yaxis_title="Magnitude",
        xaxis_range=[0, max(data.fft_freqs[:100])],
        height=350
    )

    return fig