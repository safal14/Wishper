import {renderVideo} from '@revideo/renderer';
import {resolve} from 'node:path';

const [projectFile, outputFile, duration] = process.argv.slice(2);
if (!projectFile || !outputFile || !duration) {
  console.error('Usage: node scripts/render_style.mjs PROJECT OUT.mp4 DURATION');
  process.exit(2);
}

const rendered = await renderVideo({
  projectFile: resolve(projectFile),
  settings: {
    outDir: resolve(outputFile, '..'),
    outFile: outputFile.split('/').at(-1),
    projectSettings: {size: {x: 1920, y: 1080}, range: [0, Number(duration)]},
    workers: 1,
    logProgress: false,
    ffmpeg: {ffmpegPath: 'ffmpeg'},
    puppeteer: {args: ['--no-sandbox']},
  },
});
console.log(rendered);
