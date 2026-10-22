#!/usr/bin/env node
// Render the full production without altering the approved 18-second demo.
import puppeteer from 'puppeteer-core';
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import { createReadStream, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('Usage: node scripts/render-production.mjs [--still 1.5,19,236] [--layout-check] [--duration SECONDS]');
  console.log('Duration, dimensions and fps default to production/storyboard.json.');
  console.log('Full render: out/production/video_silent.mp4; stills: out/production/stills/');
  process.exit(0);
}
function option(name) {
  const index = args.indexOf(name);
  if (index < 0) return undefined;
  if (!args[index + 1] || args[index + 1].startsWith('--')) throw new Error(`${name} requires a value`);
  return args[index + 1];
}
for (const arg of args.filter((item) => item.startsWith('--'))) {
  if (!['--still', '--duration', '--layout-check'].includes(arg)) throw new Error(`Unknown option: ${arg}`);
}
const storyboardPath = path.join(root, 'production', 'storyboard.json');
const storyboardSource = readFileSync(storyboardPath, 'utf8');
const storyboard = JSON.parse(storyboardSource);
const htmlPath = path.join(root, 'production', 'src', 'index.html');
const htmlSource = readFileSync(htmlPath);
const motionReferencePath = path.join(root, 'production', 'concept', 'motion-reference-20261014.json');
const motionReferenceInput = existsSync(motionReferencePath) ? {
  file: path.relative(root, motionReferencePath),
  sha256: createHash('sha256').update(readFileSync(motionReferencePath)).digest('hex'),
} : null;
const conceptCropDir = path.join(root, 'production', 'assets', 'concept-crops');
const conceptCropPaths = existsSync(conceptCropDir)
  ? readdirSync(conceptCropDir).filter((name) => /\.(png|jpe?g|webp)$/i.test(name)).sort().map((name) => '../assets/concept-crops/' + name)
  : [];
const taskAssetPaths = [...new Set([
  ...storyboard.tasks.flatMap((task) => [task.source_image || '../../' + task.source_file, task.before_asset]),
  '../assets/hero.png', '../assets/ending.png', ...conceptCropPaths,
].filter(Boolean))];
const taskAssetInputs = taskAssetPaths.map((source) => {
  const localPath = path.resolve(path.dirname(htmlPath), source);
  return { file: path.relative(root, localPath), sha256: createHash('sha256').update(readFileSync(localPath)).digest('hex') };
});
function verifyTaskAssetInputs() {
  for (const record of [...taskAssetInputs, ...(motionReferenceInput ? [motionReferenceInput] : [])]) {
    if (createHash('sha256').update(readFileSync(path.join(root, record.file))).digest('hex') !== record.sha256) {
      throw new Error(`Task image changed during render: ${record.file}`);
    }
  }
}
const width = Number(storyboard.width || storyboard.video?.width || 1920);
const height = Number(storyboard.height || storyboard.video?.height || 1080);
const fps = Number(storyboard.fps || storyboard.video?.fps || 30);
const duration = Number(option('--duration') ?? storyboard.duration_seconds ?? storyboard.video?.duration_seconds);
if (![width, height, fps].every((n) => Number.isInteger(n) && n > 0)
    || !Number.isFinite(duration) || duration <= 0 || !Number.isInteger(fps * duration)) {
  throw new Error('Invalid dimensions, fps, or duration in storyboard');
}
const stillTimes = option('--still')?.split(',').map(Number);
if (args.includes('--layout-check') && !stillTimes) throw new Error('--layout-check requires --still sample times');
if (stillTimes && (!stillTimes.length || stillTimes.some((t) => !Number.isFinite(t) || t < 0 || t >= duration))) {
  throw new Error(`Still times must be between 0 and ${duration} seconds`);
}
const outDir = path.join(root, 'out', 'production');
mkdirSync(outDir, { recursive: true });
const chromePath = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
let browser;
let ffmpeg;
let ffmpegFailure;
let server;
try {
  // The HTML fetches storyboard JSON; serve local project assets on loopback so
  // Chromium applies normal same-origin rules instead of file:// restrictions.
  const mimeTypes = {
    '.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8',
    '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml',
    '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf',
  };
  server = createServer((request, response) => {
    try {
      const urlPath = decodeURIComponent(new URL(request.url, 'http://127.0.0.1').pathname);
      const localPath = path.resolve(root, '.' + urlPath);
      const relative = path.relative(root, localPath);
      if (relative.startsWith('..') || path.isAbsolute(relative) || !statSync(localPath).isFile()) {
        response.writeHead(404).end('Not found');
        return;
      }
      response.writeHead(200, { 'Content-Type': mimeTypes[path.extname(localPath)] || 'application/octet-stream' });
      const stream = createReadStream(localPath);
      stream.on('error', () => response.destroy());
      stream.pipe(response);
    } catch {
      response.writeHead(404).end('Not found');
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--hide-scrollbars', '--force-device-scale-factor=1', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 1 });
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  const response = await page.goto(`http://127.0.0.1:${server.address().port}/production/src/index.html?render=1`, {
    waitUntil: 'load', timeout: 60000,
  });
  if (response && !response.ok()) throw new Error(`HTML failed to load: ${response.status()}`);
  await page.evaluate(async () => {
    if (!('__ready' in window) || typeof window.__seek !== 'function') throw new Error('Production HTML must expose __ready and __seek');
    await Promise.race([
      Promise.resolve(window.__ready),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Production HTML readiness timed out')), 60000)),
    ]);
    await document.fonts.ready;
    const imageFailures = [...document.images].filter((image) => !image.complete || !image.naturalWidth).map((image) => image.src);
    if (imageFailures.length) throw new Error(`Image assets failed to load: ${imageFailures.join(', ')}`);
  });
  if (pageErrors.length) throw new Error(`Page errors: ${pageErrors.join('; ')}`);
  async function seek(time) {
    await page.evaluate(async (t) => { await window.__seek(t); }, time);
    if (pageErrors.length) throw new Error(`Page errors: ${pageErrors.join('; ')}`);
  }
  if (stillTimes) {
    const dir = path.join(outDir, 'stills');
    mkdirSync(dir, { recursive: true });
    const layoutRecords = [];
    for (const t of stillTimes) {
      await seek(t);
      const output = path.join(dir, `still_${t.toFixed(2)}.png`);
      await page.screenshot({ path: output, type: 'png', optimizeForSpeed: true });
      console.log(`wrote ${output}`);
      if (args.includes('--layout-check')) {
        layoutRecords.push(await page.evaluate((time) => {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          const issues = [];
          let visibleTextNodes = 0;
          let node;
          while ((node = walker.nextNode())) {
            const content = node.textContent.trim();
            const element = node.parentElement;
            if (!content || !element || ['SCRIPT', 'STYLE'].includes(element.tagName)) continue;
            let opacity = 1;
            const ancestors = [];
            for (let current = element; current; current = current.parentElement) {
              const style = getComputedStyle(current);
              opacity *= Number(style.opacity);
              if (style.display === 'none' || style.visibility === 'hidden') opacity = 0;
              ancestors.push({ element: current, style });
            }
            if (opacity < 0.05) continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            const rectangles = [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
            if (!rectangles.length) continue;
            visibleTextNodes++;
            const label = element.id || element.tagName.toLowerCase() + (element.getAttribute('class') ? '.' + element.getAttribute('class').replaceAll(' ', '.') : '');
            for (const rect of rectangles) {
              const bounds = { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
              if (rect.left < -2 || rect.top < -2 || rect.right > innerWidth + 2 || rect.bottom > innerHeight + 2) {
                issues.push({ type: 'text_outside_viewport', element: label, text: content.slice(0, 150), bounds });
              }
              for (const ancestor of ancestors) {
                const clipsX = ['hidden', 'clip', 'scroll', 'auto'].includes(ancestor.style.overflowX);
                const clipsY = ['hidden', 'clip', 'scroll', 'auto'].includes(ancestor.style.overflowY);
                if (!clipsX && !clipsY) continue;
                const box = ancestor.element.getBoundingClientRect();
                if ((clipsX && (rect.left < box.left - 2 || rect.right > box.right + 2))
                    || (clipsY && (rect.top < box.top - 2 || rect.bottom > box.bottom + 2))) {
                  issues.push({ type: 'text_clipped_by_ancestor', element: label, text: content.slice(0, 150),
                    ancestor: ancestor.element.id || ancestor.element.tagName.toLowerCase(), bounds });
                  break;
                }
              }
            }
          }
          return { time, visible_text_nodes: visibleTextNodes, issues,
            viewport: { width: innerWidth, height: innerHeight },
            document: { scroll_width: document.documentElement.scrollWidth, scroll_height: document.documentElement.scrollHeight } };
        }, t));
      }
    }
    if (args.includes('--layout-check')) {
      const reportPath = path.join(outDir, 'layout-check.json');
      const issueCount = layoutRecords.reduce((sum, record) => sum + record.issues.length, 0);
      verifyTaskAssetInputs();
      writeFileSync(reportPath, JSON.stringify({ status: issueCount ? 'REVIEW' : 'PASS', issue_count: issueCount,
        storyboard_sha256: createHash('sha256').update(storyboardSource).digest('hex'),
        html_sha256: createHash('sha256').update(htmlSource).digest('hex'), task_image_inputs: taskAssetInputs,
        motion_reference_input: motionReferenceInput,
        scope: 'Visible text bounds at sampled times; screenshot review also required', records: layoutRecords }, null, 2) + '\n');
      console.log(`layout check: ${issueCount} issues; wrote ${reportPath}`);
    }
  } else {
    const output = path.join(outDir, 'video_silent.mp4');
    const partialOutput = path.join(outDir, 'video_silent.partial.mp4');
    ffmpeg = spawn('ffmpeg', [
      '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
      '-c:v', 'libx264', '-preset', 'fast', '-crf', '17',
      '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
      '-movflags', '+faststart', partialOutput,
    ], { stdio: ['pipe', 'inherit', 'inherit'] });
    const completion = new Promise((resolve, reject) => {
      ffmpeg.once('error', reject);
      ffmpeg.once('close', (code, signal) => {
        if (code === 0) resolve();
        else reject(new Error(`ffmpeg failed with code ${code}, signal ${signal || 'none'}`));
      });
    });
    completion.catch((error) => { ffmpegFailure = error; });
    ffmpeg.stdin.on('error', (error) => { ffmpegFailure = error; });
    const total = fps * duration;
    const started = Date.now();
    for (let frame = 0; frame < total; frame++) {
      if (ffmpegFailure || ffmpeg.exitCode !== null) throw ffmpegFailure || new Error('ffmpeg exited before receiving all frames');
      await seek(frame / fps);
      const jpeg = await page.screenshot({ type: 'jpeg', quality: 94, optimizeForSpeed: true });
      if (!ffmpeg.stdin.write(jpeg)) await Promise.race([
        once(ffmpeg.stdin, 'drain'),
        completion.then(() => { throw new Error('ffmpeg closed while frames were being written'); }),
      ]);
      if (frame % fps === 0) {
        console.log(`frame ${frame}/${total}; elapsed ${((Date.now() - started) / 1000).toFixed(1)}s`);
      }
    }
    ffmpeg.stdin.end();
    await completion;
    const probe = spawnSync('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', partialOutput], { encoding: 'utf8' });
    if (probe.error || probe.status !== 0) throw probe.error || new Error(`ffprobe failed: ${probe.stderr}`);
    const metadata = JSON.parse(probe.stdout);
    const video = metadata.streams.find((stream) => stream.codec_type === 'video');
    if (!video || video.width !== width || video.height !== height || video.r_frame_rate !== `${fps}/1`
        || Number(video.nb_frames) !== total || video.pix_fmt !== 'yuv420p'
        || Math.abs(Number(metadata.format.duration) - duration) > 1 / fps) {
      throw new Error('Rendered video dimensions, frame count, pixel format, or duration failed verification');
    }
    verifyTaskAssetInputs();
    renameSync(partialOutput, output);
    writeFileSync(path.join(outDir, 'render-validation.json'), JSON.stringify({
      status: 'PASS', file: 'out/production/video_silent.mp4', width, height, fps,
      duration_seconds: duration, frames: total, pixel_format: video.pix_fmt,
      elapsed_seconds: (Date.now() - started) / 1000,
      storyboard_sha256: createHash('sha256').update(storyboardSource).digest('hex'),
      html_sha256: createHash('sha256').update(htmlSource).digest('hex'),
      task_image_inputs: taskAssetInputs, image_inputs_verified_unchanged: true,
      motion_reference_input: motionReferenceInput,
      ffmpeg_exit_verified: true,
    }, null, 2) + '\n');
    console.log(`wrote ${output}; ${total} frames; ${duration}s`);
  }
} catch (error) {
  if (ffmpeg && ffmpeg.exitCode === null) ffmpeg.kill('SIGTERM');
  throw error;
} finally {
  if (browser) await browser.close();
  if (server) await new Promise((resolve) => server.close(resolve));
}
