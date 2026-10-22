#!/usr/bin/env node
/** Play the delivered MP4 continuously in Chromium and retain visual evidence.
 * Screenshots are taken during playback; no seeks or pauses occur after play().
 * Headless playback proves browser media decoding, not subjective audibility.
 */
import puppeteer from 'puppeteer-core';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const base = path.dirname(fileURLToPath(import.meta.url));
const out = path.resolve(process.env.OPENING_OUT || path.join(base, '../out/opening-v3'));
const final = path.join(out, 'rd-ai-fast-track-opening-v3.mp4');
const evidence = path.join(out, 'playback');
const reportPath = path.join(out, 'playback-validation.json');
const targets = [1.5, 4.7, 9.5, 14.5, 19.5, 25, 31.5, 38.5, 44];
const expected = { width: 1920, height: 1080, duration: 46 };
const playbackTimeoutMs = 55000;

if (process.argv.includes('--help')) {
  console.log('node playback-check.mjs\nCHROME_PATH: Chrome/Chromium executable. OPENING_OUT: output directory.\nPlays the final MP4 continuously, unmuted, and writes playback-validation.json plus nine screenshots.');
  process.exit(0);
}
if (process.argv.length > 2) throw new Error('Unknown argument; use --help.');
if (!existsSync(final)) throw new Error('Final MP4 is not ready: ' + final);
const candidates = [process.env.CHROME_PATH,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'].filter(Boolean);
const chrome = candidates.find(existsSync);
if (!chrome) throw new Error('Chrome/Chromium not found. Set CHROME_PATH.');
mkdirSync(evidence, { recursive: true });
const sha256 = createHash('sha256').update(readFileSync(final)).digest('hex');
const report = {
  status: 'FAIL', file: final, sha256, source_url: pathToFileURL(final).href,
  browser_executable: chrome, expected, playback_timeout_ms: playbackTimeoutMs,
  viewport: { width: 1920, height: 1080, deviceScaleFactor: 1 },
  method: 'Uninterrupted real-time HTMLVideoElement playback with screenshots during playback; no seeking after play().',
  audio_scope: 'HTML video unmuted at volume 1; this automated headless check makes no subjective audibility claim.',
  screenshot_samples: [], page_errors: [], media_errors: [],
};
let browser;
try {
  browser = await puppeteer.launch({
    executablePath: chrome, headless: true,
    args: ['--autoplay-policy=no-user-gesture-required', '--hide-scrollbars',
      '--force-device-scale-factor=1', '--force-color-profile=srgb',
      '--disable-background-timer-throttling', '--disable-renderer-backgrounding'],
  });
  report.browser_version = await browser.version();
  const page = await browser.newPage();
  await page.setViewport(report.viewport);
  page.on('pageerror', error => report.page_errors.push(error.message));
  await page.goto(report.source_url, { waitUntil: 'load', timeout: 30000 });
  await page.waitForSelector('video', { timeout: 10000 });
  report.metadata = await page.evaluate(async source => {
    const video = document.querySelector('video');
    video.pause();
    document.documentElement.style.cssText = 'margin:0;padding:0;width:100%;height:100%;background:#080808;overflow:hidden';
    document.body.style.cssText = 'margin:0;padding:0;width:100%;height:100%;background:#080808;overflow:hidden';
    video.style.cssText = 'display:block;position:fixed;inset:0;margin:0;padding:0;width:100vw;height:100vh;object-fit:contain;background:#080808';
    video.controls = false;
    video.autoplay = false;
    video.loop = false;
    video.muted = false;
    video.volume = 1;
    video.playbackRate = 1;
    video.preload = 'auto';
    window.__playback = { events: [], mediaErrors: [], playResolved: false,
      ended: false, startedPerformance: null, loadedmetadata: false };
    const state = window.__playback;
    const errorRecord = () => video.error ? { code: video.error.code, message: video.error.message } : null;
    for (const type of ['loadedmetadata', 'canplay', 'play', 'playing', 'pause', 'waiting', 'stalled', 'seeking', 'seeked', 'ended', 'error']) {
      video.addEventListener(type, () => {
        const error = errorRecord();
        state.events.push({ type, currentTime: video.currentTime,
          wall_seconds: state.startedPerformance === null ? null : (performance.now() - state.startedPerformance) / 1000,
          readyState: video.readyState, error });
        if (type === 'loadedmetadata') state.loadedmetadata = true;
        if (type === 'ended') state.ended = true;
        if (type === 'error') state.mediaErrors.push(error || { code: null, message: 'Unknown media error' });
      });
    }
    const metadata = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('loadedmetadata timed out')), 20000);
      video.addEventListener('loadedmetadata', () => {
        clearTimeout(timer);
        resolve({ width: video.videoWidth, height: video.videoHeight,
          duration: video.duration, readyState: video.readyState,
          muted: video.muted, volume: video.volume, playbackRate: video.playbackRate });
      }, { once: true });
      video.addEventListener('error', () => {
        clearTimeout(timer);
        reject(new Error('Media error loading MP4: ' + JSON.stringify(errorRecord())));
      }, { once: true });
    });
    video.src = source;
    video.load();
    return await metadata;
  }, report.source_url);
  if (report.metadata.width !== expected.width || report.metadata.height !== expected.height ||
      Math.abs(report.metadata.duration - expected.duration) > 1 / 30) {
    throw new Error('Browser metadata differs from expected Full HD / 46 seconds.');
  }
  await page.evaluate(async () => {
    const video = document.querySelector('video');
    window.__playback.startedPerformance = performance.now();
    await video.play();
    window.__playback.playResolved = true;
  });
  const wallStart = Date.now();
  async function observe() {
    return await page.evaluate(() => {
      const video = document.querySelector('video');
      const q = video.getVideoPlaybackQuality?.();
      return { currentTime: video.currentTime, duration: video.duration,
        paused: video.paused, ended: video.ended, readyState: video.readyState,
        networkState: video.networkState, muted: video.muted, volume: video.volume,
        playbackRate: video.playbackRate,
        decoded_frames: typeof video.webkitDecodedFrameCount === 'number' ? video.webkitDecodedFrameCount : q?.totalVideoFrames ?? null,
        dropped_frames: typeof video.webkitDroppedFrameCount === 'number' ? video.webkitDroppedFrameCount : q?.droppedVideoFrames ?? null,
        playback_quality: q ? { totalVideoFrames: q.totalVideoFrames,
          droppedVideoFrames: q.droppedVideoFrames, corruptedVideoFrames: q.corruptedVideoFrames } : null,
        error: video.error ? { code: video.error.code, message: video.error.message } : null,
        wall_seconds: (performance.now() - window.__playback.startedPerformance) / 1000 };
    });
  }
  for (const [index, target] of targets.entries()) {
    const remaining = playbackTimeoutMs - (Date.now() - wallStart);
    if (remaining <= 0) throw new Error('Continuous playback exceeded 55 seconds.');
    await page.waitForFunction(time => {
      const video = document.querySelector('video');
      return video.currentTime >= time || video.ended || video.error;
    }, { polling: 50, timeout: remaining }, target);
    const before = await observe();
    if (before.error || before.ended) throw new Error('Playback ended or failed before sample ' + target);
    const name = `cut${String(index + 1).padStart(2, '0')}_${target.toFixed(2)}s.png`;
    await page.screenshot({ path: path.join(evidence, name), type: 'png' });
    const after = await observe();
    report.screenshot_samples.push({ cut: index + 1, target_seconds: target,
      file: path.join('playback', name), screenshot_width: 1920, screenshot_height: 1080,
      before, after });
    console.log(`Playback CUT ${index + 1}: ${before.currentTime.toFixed(3)}s, decoded ${before.decoded_frames} frames`);
  }
  const remaining = playbackTimeoutMs - (Date.now() - wallStart);
  if (remaining <= 0) throw new Error('Continuous playback exceeded 55 seconds.');
  await page.waitForFunction(() => {
    const video = document.querySelector('video');
    return video.ended || video.error;
  }, { polling: 50, timeout: remaining });
  report.final = await observe();
  const state = await page.evaluate(() => window.__playback);
  report.events = state.events;
  report.loadedmetadata = state.loadedmetadata;
  report.play_promise_resolved = state.playResolved;
  report.ended_event = state.ended;
  report.media_errors = state.mediaErrors;
  report.playback_wall_seconds = (Date.now() - wallStart) / 1000;
  const playbackEvents = state.events.filter(event => event.wall_seconds !== null);
  report.seeks_during_playback = playbackEvents.filter(event => event.type === 'seeking').length;
  report.pauses_during_playback = playbackEvents.filter(event => event.type === 'pause' && event.currentTime < expected.duration - 1 / 30).length;
  if (!report.loadedmetadata || !state.playResolved || !state.ended || !report.final.ended ||
      report.final.error || state.mediaErrors.length || report.page_errors.length ||
      report.seeks_during_playback || report.pauses_during_playback ||
      !report.final.decoded_frames || report.final.muted || report.final.volume !== 1 ||
      Math.abs(report.final.currentTime - expected.duration) > 1 / 30) {
    throw new Error('Playback validation failed; inspect the retained report.');
  }
  report.status = 'PASS';
} catch (error) {
  report.failure = String(error.stack || error);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
}
console.log(`${report.status}: ${reportPath}`);
if (report.failure) console.error(report.failure);
