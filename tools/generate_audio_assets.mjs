import fs from 'node:fs';
import path from 'node:path';

const RATE = 44100;
const OUT = path.resolve('assets/audio/sfx');
fs.mkdirSync(OUT, {recursive: true});

let seed = 0x51f15e;
const noise = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 0xffffffff * 2 - 1;
};
const clamp = v => Math.max(-1, Math.min(1, v));
const env = (t, duration, attack = .008, release = .12) =>
  Math.min(1, t / attack) * Math.min(1, (duration - t) / release);
const sine = (frequency, t) => Math.sin(Math.PI * 2 * frequency * t);

function writeWav(name, duration, sample) {
  const count = Math.ceil(duration * RATE);
  const dataSize = count * 2;
  const wav = Buffer.alloc(44 + dataSize);
  wav.write('RIFF', 0);
  wav.writeUInt32LE(36 + dataSize, 4);
  wav.write('WAVEfmt ', 8);
  wav.writeUInt32LE(16, 16);
  wav.writeUInt16LE(1, 20);
  wav.writeUInt16LE(1, 22);
  wav.writeUInt32LE(RATE, 24);
  wav.writeUInt32LE(RATE * 2, 28);
  wav.writeUInt16LE(2, 32);
  wav.writeUInt16LE(16, 34);
  wav.write('data', 36);
  wav.writeUInt32LE(dataSize, 40);
  for (let i = 0; i < count; i++) {
    const t = i / RATE;
    wav.writeInt16LE(Math.round(clamp(sample(t, duration)) * 32767), 44 + i * 2);
  }
  fs.writeFileSync(path.join(OUT, name), wav);
}

// Short, dry sounds intentionally leave headroom so the in-game group gain can mix them.
writeWav('hammer-swing.wav', .34, (t, d) => {
  const sweep = 950 * Math.exp(-8 * t) + 90;
  return env(t, d, .004, .16) * (noise() * .19 + sine(sweep, t) * .12) * Math.exp(-4.5 * t);
});

writeWav('laser-fire.wav', .24, (t, d) => {
  const f = 1480 * Math.exp(-7.5 * t) + 210;
  return env(t, d, .002, .08) * (sine(f, t) * .48 + sine(f * 2.01, t) * .13) * Math.exp(-7 * t);
});

writeWav('cannon-fire.wav', .58, (t, d) => {
  const thump = sine(96 * Math.exp(-2.5 * t) + 34, t) * .68;
  return env(t, d, .002, .24) * (thump + noise() * .26 * Math.exp(-8 * t)) * Math.exp(-3.4 * t);
});

writeWav('plasma-fire.wav', .38, (t, d) => {
  const f = 360 + 560 * t;
  return env(t, d, .006, .14) * (sine(f, t) * .42 + sine(f * .49, t) * .18 + noise() * .08) * Math.exp(-3.3 * t);
});

writeWav('meteor-call.wav', .82, (t, d) => {
  const f = 74 + 260 * t * t;
  return env(t, d, .018, .28) * (sine(f, t) * .42 + sine(f * 1.51, t) * .2 + noise() * .08) * (.8 - .25 * t);
});

writeWav('void-fire.wav', .72, (t, d) => {
  const f = 230 * Math.exp(-2.7 * t) + 38;
  return env(t, d, .012, .3) * (sine(f, t) * .42 + sine(41 + 9 * t, t) * .28 + noise() * .07);
});

for (let variant = 0; variant < 2; variant++) {
  writeWav(`impact-hard-${variant + 1}.wav`, .32, (t, d) => {
    const f = (variant ? 176 : 143) * Math.exp(-5 * t) + 52;
    return env(t, d, .001, .14) * (noise() * .43 + sine(f, t) * .45) * Math.exp(-8 * t);
  });
  writeWav(`impact-energy-${variant + 1}.wav`, .3, (t, d) => {
    const f = (variant ? 620 : 510) * Math.exp(-5 * t) + 120;
    return env(t, d, .001, .13) * (sine(f, t) * .48 + noise() * .2) * Math.exp(-7 * t);
  });
}

writeWav('explosion-impact.wav', .86, (t, d) => {
  const body = sine(72 * Math.exp(-2 * t) + 28, t) * .56;
  return env(t, d, .002, .32) * (body + noise() * .42 * Math.exp(-4.2 * t)) * Math.exp(-2.4 * t);
});

writeWav('void-impact.wav', .94, (t, d) => {
  const f = 58 + 150 * Math.exp(-3.5 * t);
  return env(t, d, .008, .36) * (sine(f, t) * .5 + sine(f * 2.03, t) * .18 + noise() * .12) * Math.exp(-2.1 * t);
});

for (let variant = 0; variant < 3; variant++) {
  writeWav(`footstep-sand-${variant + 1}.wav`, .26, (t, d) => {
    const crunch = noise() * (Math.sin(Math.PI * Math.min(1, t / .055)) ** 2) * Math.exp(-10 * t);
    const body = sine(82 + variant * 9, t) * Math.exp(-19 * t);
    return env(t, d, .002, .1) * (crunch * .37 + body * .27);
  });
}

console.log(`Generated 15 WAV files in ${OUT}`);
