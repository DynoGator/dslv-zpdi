package labs.dynogator.dslvzpdi;

/**
 * Real-time demod from HackRF 8-bit IQ → 48 kHz mono PCM.
 * WFM polar discriminator + 75 µs de-emphasis, NFM, AM envelope, USB/LSB phasing, CW.
 */
final class Demod {
    static final int OUT_RATE = 48_000;

    private volatile String mode = "WFM";
    private volatile float volume = 0.7f;
    private volatile float squelch = 0.08f;
    private volatile int inRate = 2_048_000;

    private float prevI, prevQ;
    private float deemph;
    private float dc;
    private float agc = 1f;
    private float rssi;
    private float qDelay;
    private double nco;
    private float combI, combQ;
    private int decimCount;
    private int decimR = 8;
    private float accI, accQ;
    private double resample;
    private float lastFm;
    private float audioLp;
    private int outCount;
    private boolean muted;

    void setMode(String m) {
        if (m == null || m.isEmpty()) return;
        if (!m.equals(mode)) reset();
        mode = m;
        decimR = decimFor(mode, inRate);
    }

    void setVolume(float v) {
        volume = clamp(v, 0, 1.5f);
    }

    void setSquelch(float v) {
        squelch = clamp(v, 0, 1);
    }

    void setSampleRate(int hz) {
        if (hz < 1_000_000) return;
        inRate = hz;
        decimR = decimFor(mode, inRate);
    }

    void reset() {
        prevI = prevQ = deemph = dc = qDelay = 0;
        agc = 1f;
        combI = combQ = accI = accQ = 0;
        decimCount = 0;
        nco = 0;
        resample = 0;
        lastFm = 0;
        rssi = 0;
        audioLp = 0;
    }

    float rssi() {
        return rssi;
    }

    boolean muted() {
        return muted;
    }

    /**
     * Consume interleaved signed IQ bytes. Writes up to pcm.length samples.
     * @return number of 48 kHz samples written
     */
    int process(byte[] iq, int off, int bytes, short[] pcm) {
        outCount = 0;
        int samples = bytes / 2;
        String m = mode;
        int R = Math.max(1, decimR);
        float ifRate = inRate / (float) R;
        float deemphA = (float) (1.0 / (1.0 + ifRate * 75e-6));
        double ncoStep = 0;
        if ("CW".equals(m)) ncoStep = 2.0 * Math.PI * 700.0 / ifRate;
        else if ("USB".equals(m)) ncoStep = 2.0 * Math.PI * 1500.0 / ifRate;
        else if ("LSB".equals(m)) ncoStep = -2.0 * Math.PI * 1500.0 / ifRate;

        float powerAcc = 0;
        int powerN = 0;

        for (int n = 0; n < samples && outCount < pcm.length; n++) {
            int p = off + n * 2;
            if (p + 1 >= iq.length) break;
            float i = iq[p] / 127.0f;
            float q = iq[p + 1] / 127.0f;
            powerAcc += i * i + q * q;
            powerN++;

            accI += i;
            accQ += q;
            decimCount++;
            if (decimCount < R) continue;
            float ii = accI / R;
            float qq = accQ / R;
            accI = accQ = 0;
            decimCount = 0;

            float audio;
            switch (m) {
                case "WFM":
                case "NFM":
                    audio = fm(ii, qq);
                    if ("WFM".equals(m)) {
                        deemph += deemphA * (audio - deemph);
                        audio = deemph;
                    }
                    break;
                case "AM":
                    audio = (float) Math.sqrt(ii * ii + qq * qq);
                    dc += 0.01f * (audio - dc);
                    audio = audio - dc;
                    agc = 0.995f * agc + 0.005f * Math.abs(audio);
                    audio = audio / (agc + 1e-4f) * 0.25f;
                    break;
                case "USB":
                case "LSB": {
                    float c = (float) Math.cos(nco);
                    float s = (float) Math.sin(nco);
                    nco += ncoStep;
                    if (nco > Math.PI * 2) nco -= Math.PI * 2;
                    if (nco < -Math.PI * 2) nco += Math.PI * 2;
                    float mi = ii * c - qq * s;
                    float mq = ii * s + qq * c;
                    audio = "USB".equals(m) ? mi - qDelay : mi + qDelay;
                    qDelay = mq;
                    dc += 0.002f * (audio - dc);
                    audio -= dc;
                    agc = 0.99f * agc + 0.01f * Math.abs(audio);
                    audio = audio / (agc + 1e-4f) * 0.3f;
                    break;
                }
                case "CW": {
                    float c = (float) Math.cos(nco);
                    float s = (float) Math.sin(nco);
                    nco += ncoStep;
                    if (nco > Math.PI * 2) nco -= Math.PI * 2;
                    float mix = ii * c - qq * s;
                    dc += 0.02f * (mix - dc);
                    audio = (mix - dc) * 0.8f;
                    break;
                }
                default:
                    audio = 0;
            }

            if (!"WFM".equals(m) && !"RAW".equals(m)) {
                audioLp += 0.32f * (audio - audioLp);
                audio = audioLp;
            }

            resample += OUT_RATE;
            if (resample >= ifRate) {
                resample -= ifRate;
                emit(pcm, audio);
            }
        }

        if (powerN > 0) {
            float p = powerAcc / powerN;
            rssi = 0.9f * rssi + 0.1f * p;
        }
        muted = squelch > 0.004f && rssi < squelch * squelch * 0.15f;
        if (muted) {
            for (int i = 0; i < outCount; i++) pcm[i] = 0;
        }
        return outCount;
    }

    private float fm(float i, float q) {
        float det = i * prevI + q * prevQ;
        float cross = q * prevI - i * prevQ;
        prevI = i;
        prevQ = q;
        float ang = (float) Math.atan2(cross, det + 1e-12f);
        lastFm = ang;
        return ang * 0.35f;
    }

    private void emit(short[] pcm, float audio) {
        if (outCount >= pcm.length) return;
        float v = audio * volume;
        if (v > 1) v = 1;
        if (v < -1) v = -1;
        pcm[outCount++] = (short) (v * 32000);
    }

    private static int decimFor(String mode, int rate) {
        if ("WFM".equals(mode)) {
            int r = Math.round(rate / 256_000f);
            return Math.max(4, r);
        }
        int r = Math.round(rate / 48_000f);
        return Math.max(8, r);
    }

    private static float clamp(float v, float lo, float hi) {
        return v < lo ? lo : Math.min(v, hi);
    }
}
