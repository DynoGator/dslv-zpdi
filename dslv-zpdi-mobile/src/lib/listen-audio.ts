import type { DemodMode } from "./types";

/** Preview-only demod stand-in. Native APK plays real HackRF PCM via AudioTrack. */
export function startSimListen(sdr: { demod: DemodMode; centerHz: number; volume: number }): () => void {
  const ctx = new AudioContext();
  const master = ctx.createGain();
  master.gain.value = (sdr.volume ?? 0.7) * 0.22;
  master.connect(ctx.destination);

  const noise = ctx.createBufferSource();
  const buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const data = buf.getChannelData(0);
  let pink = 0;
  for (let i = 0; i < data.length; i++) {
    pink = 0.97 * pink + Math.random() * 0.06;
    data[i] = (Math.random() * 2 - 1) * 0.18 + pink;
  }
  noise.buffer = buf;
  noise.loop = true;

  const lp = ctx.createBiquadFilter();
  const hp = ctx.createBiquadFilter();
  hp.type = "highpass";
  lp.type = "lowpass";
  noise.connect(hp);
  hp.connect(lp);

  const osc = ctx.createOscillator();
  const oscGain = ctx.createGain();
  osc.connect(oscGain);
  oscGain.connect(master);

  if (sdr.demod === "WFM") {
    lp.frequency.value = 15000;
    hp.frequency.value = 30;
    osc.type = "sine";
    osc.frequency.value = 440 + (sdr.centerHz % 200);
    oscGain.gain.value = 0.09;
    const lfo = ctx.createOscillator();
    const lfoG = ctx.createGain();
    lfo.frequency.value = 5.2;
    lfoG.gain.value = 18;
    lfo.connect(lfoG);
    lfoG.connect(osc.frequency);
    lfo.start();
  } else if (sdr.demod === "NFM") {
    lp.frequency.value = 3400;
    hp.frequency.value = 300;
    osc.type = "sine";
    osc.frequency.value = 880;
    oscGain.gain.value = 0.05;
  } else if (sdr.demod === "AM") {
    lp.frequency.value = 4500;
    hp.frequency.value = 80;
    osc.type = "sine";
    osc.frequency.value = 1000;
    oscGain.gain.value = 0.12;
  } else if (sdr.demod === "CW") {
    lp.frequency.value = 900;
    hp.frequency.value = 500;
    osc.type = "sine";
    osc.frequency.value = 700;
    oscGain.gain.value = 0.16;
    master.gain.value = (sdr.volume ?? 0.7) * 0.12;
  } else if (sdr.demod === "USB" || sdr.demod === "LSB") {
    lp.frequency.value = 2700;
    hp.frequency.value = 300;
    osc.type = "sawtooth";
    osc.frequency.value = 700;
    oscGain.gain.value = 0.03;
  } else {
    lp.frequency.value = 200;
    hp.frequency.value = 20;
    oscGain.gain.value = 0;
  }

  lp.connect(master);
  noise.start();
  osc.start();

  return () => {
    try {
      noise.stop();
      osc.stop();
    } catch {
      /* already stopped */
    }
    void ctx.close();
  };
}
