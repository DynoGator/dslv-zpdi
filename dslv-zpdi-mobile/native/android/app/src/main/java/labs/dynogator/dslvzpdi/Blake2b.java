package labs.dynogator.dslvzpdi;

/**
 * RFC 7693 BLAKE2b-256. SPEC-010 payload checksum. Pure Java.
 */
final class Blake2b {
    private static final long[] IV = {
            0x6a09e667f3bcc908L, 0xbb67ae8584caa73bL,
            0x3c6ef372fe94f82bL, 0xa54ff53a5f1d36f1L,
            0x510e527fade682d1L, 0x9b05688c2b3e6c1fL,
            0x1f83d9abfb41bd6bL, 0x5be0cd19137e2179L
    };
    private static final byte[][] SIGMA = {
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15},
            {14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3},
            {11, 8, 12, 0, 5, 2, 15, 13, 10, 14, 3, 6, 7, 1, 9, 4},
            {7, 9, 3, 1, 13, 12, 11, 14, 2, 6, 5, 10, 4, 0, 15, 8},
            {9, 0, 5, 7, 2, 4, 10, 15, 14, 1, 11, 12, 6, 8, 3, 13},
            {2, 12, 6, 10, 0, 11, 8, 3, 4, 13, 7, 5, 15, 14, 1, 9},
            {12, 5, 1, 15, 14, 13, 4, 10, 0, 7, 6, 3, 9, 2, 8, 11},
            {13, 11, 7, 14, 12, 1, 3, 9, 5, 0, 15, 4, 8, 6, 2, 10},
            {6, 15, 14, 9, 11, 3, 0, 8, 12, 2, 13, 7, 1, 4, 10, 5},
            {10, 2, 8, 4, 7, 6, 1, 5, 15, 11, 9, 14, 3, 12, 13, 0},
            {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15},
            {14, 10, 4, 8, 9, 15, 13, 6, 1, 12, 0, 2, 11, 7, 5, 3}
    };

    static byte[] hash256(byte[] data) {
        long[] h = IV.clone();
        h[0] ^= 0x01010020L; // fanout=1, depth=1, digest=32
        int off = 0;
        long t = 0;
        if (data.length == 0) {
            compress(h, new byte[128], 0, 0, true);
        } else {
            while (off + 128 < data.length) {
                t += 128;
                compress(h, data, off, t, false);
                off += 128;
            }
            int remaining = data.length - off;
            t += remaining;
            byte[] last = new byte[128];
            System.arraycopy(data, off, last, 0, remaining);
            compress(h, last, 0, t, true);
        }
        byte[] out = new byte[32];
        for (int i = 0; i < 4; i++) {
            long v = h[i];
            for (int b = 0; b < 8; b++) {
                out[i * 8 + b] = (byte) (v >>> (8 * b));
            }
        }
        return out;
    }

    static String hex256(byte[] data) {
        return hex(hash256(data));
    }

    static String hex(byte[] b) {
        char[] c = new char[b.length * 2];
        final char[] a = "0123456789abcdef".toCharArray();
        for (int i = 0; i < b.length; i++) {
            c[i * 2] = a[(b[i] >> 4) & 0xf];
            c[i * 2 + 1] = a[b[i] & 0xf];
        }
        return new String(c);
    }

    private static void compress(long[] h, byte[] block, int off, long t, boolean last) {
        long[] v = new long[16];
        long[] m = new long[16];
        System.arraycopy(h, 0, v, 0, 8);
        System.arraycopy(IV, 0, v, 8, 8);
        v[12] ^= t;
        if (last) v[14] = ~v[14];
        for (int i = 0; i < 16; i++) {
            int p = off + i * 8;
            m[i] = (block[p] & 0xffL)
                    | ((block[p + 1] & 0xffL) << 8)
                    | ((block[p + 2] & 0xffL) << 16)
                    | ((block[p + 3] & 0xffL) << 24)
                    | ((block[p + 4] & 0xffL) << 32)
                    | ((block[p + 5] & 0xffL) << 40)
                    | ((block[p + 6] & 0xffL) << 48)
                    | ((block[p + 7] & 0xffL) << 56);
        }
        for (int r = 0; r < 12; r++) {
            byte[] s = SIGMA[r];
            g(v, 0, 4, 8, 12, m[s[0]], m[s[1]]);
            g(v, 1, 5, 9, 13, m[s[2]], m[s[3]]);
            g(v, 2, 6, 10, 14, m[s[4]], m[s[5]]);
            g(v, 3, 7, 11, 15, m[s[6]], m[s[7]]);
            g(v, 0, 5, 10, 15, m[s[8]], m[s[9]]);
            g(v, 1, 6, 11, 12, m[s[10]], m[s[11]]);
            g(v, 2, 7, 8, 13, m[s[12]], m[s[13]]);
            g(v, 3, 4, 9, 14, m[s[14]], m[s[15]]);
        }
        for (int i = 0; i < 8; i++) h[i] ^= v[i] ^ v[i + 8];
    }

    private static void g(long[] v, int a, int b, int c, int d, long x, long y) {
        v[a] = v[a] + v[b] + x;
        v[d] = Long.rotateRight(v[d] ^ v[a], 32);
        v[c] = v[c] + v[d];
        v[b] = Long.rotateRight(v[b] ^ v[c], 24);
        v[a] = v[a] + v[b] + y;
        v[d] = Long.rotateRight(v[d] ^ v[a], 16);
        v[c] = v[c] + v[d];
        v[b] = Long.rotateRight(v[b] ^ v[c], 63);
    }
}
