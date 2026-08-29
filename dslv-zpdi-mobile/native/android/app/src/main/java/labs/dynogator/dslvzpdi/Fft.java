package labs.dynogator.dslvzpdi;

/**
 * 512-point radix-2 FFT on HackRF signed 8-bit IQ → power spectrum in dBm.
 * Pure Java; no JNI (Pixel 9 16 KB pages).
 */
final class Fft {
    static final int N = 512;
    static final int BINS = 192;

    private final float[] re = new float[N];
    private final float[] im = new float[N];
    private final float[] window = new float[N];
    private final int[] rev = new int[N];
    private final float[] wr;
    private final float[] wi;

    Fft() {
        int bits = 9;
        for (int i = 0; i < N; i++) {
            rev[i] = Integer.reverse(i) >>> (32 - bits);
            window[i] = 0.54f - 0.46f * (float) Math.cos(2.0 * Math.PI * i / (N - 1));
        }
        wr = new float[N / 2];
        wi = new float[N / 2];
        for (int i = 0; i < N / 2; i++) {
            double a = -2.0 * Math.PI * i / N;
            wr[i] = (float) Math.cos(a);
            wi[i] = (float) Math.sin(a);
        }
    }

    /** IQ interleaved signed bytes. Writes N dBm bins into {@code db}. */
    synchronized void powerDbm(byte[] iq, int off, int bytes, float[] db) {
        int samples = Math.min(N, Math.max(0, bytes / 2));
        for (int i = 0; i < N; i++) {
            float xr = 0;
            float xi = 0;
            if (i < samples) {
                int p = off + i * 2;
                xr = (iq[p] / 127.0f) * window[i];
                xi = (iq[p + 1] / 127.0f) * window[i];
            }
            re[rev[i]] = xr;
            im[rev[i]] = xi;
        }
        for (int len = 2; len <= N; len <<= 1) {
            int half = len >> 1;
            int step = N / len;
            for (int i = 0; i < N; i += len) {
                int k = 0;
                for (int j = 0; j < half; j++) {
                    float tr = wr[k] * re[i + j + half] - wi[k] * im[i + j + half];
                    float ti = wr[k] * im[i + j + half] + wi[k] * re[i + j + half];
                    re[i + j + half] = re[i + j] - tr;
                    im[i + j + half] = im[i + j] - ti;
                    re[i + j] += tr;
                    im[i + j] += ti;
                    k += step;
                }
            }
        }
        for (int i = 0; i < N; i++) {
            int src = (i + N / 2) % N;
            float p = re[src] * re[src] + im[src] * im[src];
            db[i] = 10.0f * (float) Math.log10(p + 1e-12f) - 8.0f;
        }
    }

    static void collapse(float[] fftN, float[] bins) {
        int n = fftN.length;
        int m = bins.length;
        for (int i = 0; i < m; i++) {
            float lo = i * (float) n / m;
            float hi = (i + 1) * (float) n / m;
            int a = (int) Math.floor(lo);
            int b = Math.min(n, (int) Math.ceil(hi));
            float s = 0;
            int c = 0;
            for (int k = a; k < b; k++) {
                s += fftN[k];
                c++;
            }
            bins[i] = c == 0 ? -120 : s / c;
        }
    }
}
