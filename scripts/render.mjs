// Renders src/index.html frame by frame with headless Chrome and pipes the frames to ffmpeg.
//   node scripts/render.mjs                 -> out/video_silent.mp4
//   node scripts/render.mjs --still 1.5,8   -> out/stills/still_1.50.png, still_8.00.png
import puppeteer from 'puppeteer-core';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const FPS = 30, DURATION = 18, W = 1920, H = 1080;
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const stillArg = process.argv.indexOf('--still');

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--hide-scrollbars', '--force-device-scale-factor=1', '--force-color-profile=srgb'],
});
const page = await browser.newPage();
await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto(pathToFileURL(path.join(root, 'src', 'index.html')).href + '?render=1');
await page.evaluate(() => window.__ready);

if (stillArg > -1) {
  const dir = path.join(root, 'out', 'stills');
  mkdirSync(dir, { recursive: true });
  for (const t of process.argv[stillArg + 1].split(',').map(Number)) {
    await page.evaluate((t) => window.__seek(t), t);
    await page.screenshot({ path: path.join(dir, `still_${t.toFixed(2)}.png`) });
  }
  console.log('stills written to', dir);
} else {
  mkdirSync(path.join(root, 'out'), { recursive: true });
  const out = path.join(root, 'out', 'video_silent.mp4');
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = FPS * DURATION;
  for (let f = 0; f < total; f++) {
    await page.evaluate((t) => window.__seek(t), f / FPS);
    const png = await page.screenshot({ type: 'png', optimizeForSpeed: true });
    if (!ff.stdin.write(png)) await once(ff.stdin, 'drain');
    if (f % 60 === 0) console.log(`frame ${f}/${total}`);
  }
  ff.stdin.end();
  await once(ff, 'close');
  console.log('wrote', out);
}
await browser.close();
