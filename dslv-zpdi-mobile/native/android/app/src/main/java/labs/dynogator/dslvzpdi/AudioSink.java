package labs.dynogator.dslvzpdi;

import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioTrack;

/**
 * 48 kHz mono PCM to the Pixel speaker. No JNI.
 */
final class AudioSink {
    static final int RATE = 48_000;

    private AudioTrack track;
    private volatile boolean playing;

    synchronized void start() {
        if (playing && track != null) return;
        int min = AudioTrack.getMinBufferSize(
                RATE, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT);
        int buf = Math.max(min, RATE / 5) * 2;
        track = new AudioTrack.Builder()
                .setAudioAttributes(new AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                        .build())
                .setAudioFormat(new AudioFormat.Builder()
                        .setSampleRate(RATE)
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build())
                .setBufferSizeInBytes(buf)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build();
        track.play();
        playing = true;
    }

    void write(short[] pcm, int n) {
        AudioTrack t = track;
        if (!playing || t == null || n <= 0) return;
        t.write(pcm, 0, n, AudioTrack.WRITE_NON_BLOCKING);
    }

    synchronized void stop() {
        playing = false;
        AudioTrack t = track;
        track = null;
        if (t == null) return;
        try {
            t.pause();
            t.flush();
            t.stop();
            t.release();
        } catch (Exception ignored) {
        }
    }

    boolean isPlaying() {
        return playing;
    }
}
