import streamlit as st

def show_aliasing_alert(fs, f):
    nyquist = 2 * f
    if fs < nyquist:
        aliased = abs(f - round(f / fs) * fs)
        st.error(f"Aliasing Detected! Sampling rate {fs} Hz is below the Nyquist limit of {nyquist} Hz. Your {f} Hz signal will appear as a false {aliased:.1f} Hz signal.")
        with st.expander("What does this mean?"):
            st.markdown(f"""
**Aliasing** happens when you sample a signal too slowly.

- Your signal frequency: **{f} Hz**
- Minimum safe sampling rate (Nyquist): **{nyquist} Hz**
- Your sampling rate: **{fs} Hz** too low!
- The signal will be mistaken for: **{aliased:.1f} Hz**

Think of it like a spinning wheel on a video — if the camera does not take enough frames per second, the wheel appears to spin backwards. Same idea here.
            """)
    elif fs == nyquist:
        st.warning(f"Right at the Nyquist Limit — fs = {fs} Hz = exactly 2 x {f} Hz. Theoretically safe but risky in practice. Try going a bit higher.")
        with st.expander("What does this mean?"):
            st.markdown(f"""
**The Nyquist theorem** says you need to sample at more than twice the signal frequency.

- Your signal: **{f} Hz**
- Nyquist minimum: **{nyquist} Hz**
- You are right on the edge — any noise or timing error could cause aliasing.

In practice, engineers sample at 4-10x the signal frequency to be safe.
            """)
    else:
        st.success(f"Clean Sampling — fs = {fs} Hz is safely above the Nyquist limit of {nyquist} Hz. No aliasing.")
        with st.expander("Why is this good?"):
            st.markdown(f"""
**No aliasing** because your sampling rate is high enough.

- Your signal: **{f} Hz**
- Nyquist minimum: **{nyquist} Hz**
- Your sampling rate: **{fs} Hz** safely above!

The orange dots on the time domain chart are capturing the wave accurately. The reconstructed signal will match the original.
            """)

def show_signal_stats(data):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Signal Frequency", f"{data.f} Hz")
    col2.metric("Sampling Rate", f"{data.fs} Hz")
    col3.metric("Nyquist Limit", f"{2 * data.f} Hz")

    if data.aliased_freq > 0:
        col4.metric("Aliased Frequency", f"{data.aliased_freq:.1f} Hz", delta="Aliasing detected", delta_color="inverse")
    else:
        col4.metric("Aliased Frequency", "None", delta="Clean signal", delta_color="normal")