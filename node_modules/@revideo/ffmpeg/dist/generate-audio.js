"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.audioCodecs = void 0;
exports.generateAudio = generateAudio;
exports.mergeMedia = mergeMedia;
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const ffmpeg_exporter_server_1 = require("./ffmpeg-exporter-server");
const settings_1 = require("./settings");
const utils_1 = require("./utils");
const ffmpeg = require("fluent-ffmpeg");
exports.audioCodecs = {
    mp4: 'aac',
    webm: 'libopus',
    proRes: 'aac',
};
const SAMPLE_RATE = 48000;
function getAssetPlacement(frames) {
    const assets = [];
    // A map to keep track of the first and last currentTime for each asset.
    const assetTimeMap = new Map();
    for (let frame = 0; frame < frames.length; frame++) {
        for (const asset of frames[frame]) {
            if (!assetTimeMap.has(asset.key)) {
                // If the asset is not in the map, add it with its current time as both start and end.
                assetTimeMap.set(asset.key, {
                    start: asset.currentTime,
                    end: asset.currentTime,
                });
                assets.push({
                    key: asset.key,
                    src: asset.src,
                    type: asset.type,
                    startInVideo: frame,
                    endInVideo: frame,
                    duration: 0, // Placeholder, will be recalculated later based on frames
                    durationInSeconds: 0, // Placeholder, will be calculated based on currentTime
                    playbackRate: asset.playbackRate,
                    volume: asset.volume,
                    trimLeftInSeconds: asset.currentTime,
                });
            }
            else {
                // If the asset is already in the map, update the end time.
                const timeInfo = assetTimeMap.get(asset.key);
                if (timeInfo) {
                    timeInfo.end = asset.currentTime;
                    assetTimeMap.set(asset.key, timeInfo);
                }
                const existingAsset = assets.find(a => a.key === asset.key);
                if (existingAsset) {
                    existingAsset.endInVideo = frame;
                }
            }
        }
    }
    // Calculate the duration based on frame count and durationInSeconds based on currentTime.
    assets.forEach(asset => {
        const timeInfo = assetTimeMap.get(asset.key);
        if (timeInfo) {
            // Calculate durationInSeconds based on the start and end currentTime values.
            asset.durationInSeconds =
                (timeInfo.end - timeInfo.start) / asset.playbackRate;
        }
        // Recalculate the original duration based on frame count.
        asset.duration = asset.endInVideo - asset.startInVideo + 1;
    });
    return assets;
}
function calculateAtempoFilters(playbackRate) {
    const atempoFilters = [];
    // Calculate how many times we need to 100x the speed
    let rate = playbackRate;
    while (rate > 100.0) {
        atempoFilters.push('atempo=100.0');
        rate /= 100.0;
    }
    // Add the last atempo filter with the remaining rate
    if (rate > 1.0) {
        atempoFilters.push(`atempo=${rate}`);
    }
    // Calculate how many times we need to halve the speed
    rate = playbackRate;
    while (rate < 0.5) {
        atempoFilters.push('atempo=0.5');
        rate *= 2.0;
    }
    // Add the last atempo filter with the remaining rate
    if (rate < 1.0) {
        atempoFilters.push(`atempo=${rate}`);
    }
    return atempoFilters;
}
async function prepareAudio(outputDir, tempDir, asset, startFrame, endFrame, fps) {
    // Construct the output path
    const sanitizedKey = asset.key.replace(/[/[\]]/g, '-');
    const outputPath = path.join(tempDir, `${sanitizedKey}.wav`);
    const trimLeft = asset.trimLeftInSeconds / asset.playbackRate;
    const trimRight = 1 / fps +
        Math.min(trimLeft + asset.durationInSeconds, trimLeft + (endFrame - startFrame) / fps);
    const padStart = (asset.startInVideo / fps) * 1000;
    const assetSampleRate = await (0, utils_1.getSampleRate)((0, utils_1.resolvePath)(outputDir, asset.src));
    const padEnd = Math.max(0, (assetSampleRate * (endFrame - startFrame + 1)) / fps -
        (assetSampleRate * asset.duration) / fps -
        (assetSampleRate * padStart) / 1000);
    const atempoFilters = calculateAtempoFilters(asset.playbackRate); // atempo filter value must be >=0.5 and <=100. If the value is higher or lower, this function sets multiple atempo filters
    const resolvedPath = (0, utils_1.resolvePath)(outputDir, asset.src);
    await new Promise((resolve, reject) => {
        const audioFilters = [
            ...atempoFilters,
            `atrim=start=${trimLeft}:end=${trimRight}`,
            `apad=pad_len=${padEnd}`,
            `adelay=${padStart}|${padStart}|${padStart}`,
            `volume=${asset.volume}`,
        ].join(',');
        ffmpeg.setFfmpegPath(settings_1.ffmpegSettings.getFfmpegPath());
        ffmpeg(resolvedPath)
            .audioChannels(2)
            .audioCodec('pcm_s16le')
            .audioFrequency(SAMPLE_RATE)
            .outputOptions([`-af`, audioFilters])
            .on('end', () => {
            resolve();
        })
            .on('error', err => {
            console.error(`Error processing audio for asset key: ${asset.key}`, err);
            reject(err);
        })
            .save(outputPath);
    });
    return outputPath;
}
async function mergeAudioTracks(tempDir, audioFilenames) {
    return new Promise((resolve, reject) => {
        ffmpeg.setFfmpegPath(settings_1.ffmpegSettings.getFfmpegPath());
        const command = ffmpeg();
        audioFilenames.forEach(filename => {
            command.input(filename);
        });
        command
            .complexFilter([
            `amix=inputs=${audioFilenames.length}:duration=longest,volume=${audioFilenames.length}`,
        ])
            .outputOptions(['-c:a', 'pcm_s16le'])
            .on('end', () => {
            resolve();
        })
            .on('error', err => {
            console.error(`Error merging audio tracks: ${err.message}`);
            reject(err);
        })
            .save(path.join(tempDir, `audio.wav`));
    });
}
async function generateAudio({ outputDir, tempDir, assets, startFrame, endFrame, fps, }) {
    const fullTempDir = path.join(os.tmpdir(), tempDir);
    await (0, utils_1.makeSureFolderExists)(outputDir);
    await (0, utils_1.makeSureFolderExists)(fullTempDir);
    const assetPositions = getAssetPlacement(assets);
    const audioFilenames = [];
    for (const asset of assetPositions) {
        let hasAudioStream = true;
        if (asset.type !== 'audio') {
            hasAudioStream = await (0, utils_1.checkForAudioStream)((0, utils_1.resolvePath)(outputDir, asset.src));
        }
        if (asset.playbackRate !== 0 && asset.volume !== 0 && hasAudioStream) {
            const filename = await prepareAudio(outputDir, fullTempDir, asset, startFrame, endFrame, fps);
            audioFilenames.push(filename);
        }
    }
    if (audioFilenames.length > 0) {
        await mergeAudioTracks(fullTempDir, audioFilenames);
    }
    return audioFilenames;
}
async function mergeMedia(outputFilename, outputDir, tempDir, format) {
    const fullTempDir = path.join(os.tmpdir(), tempDir);
    await (0, utils_1.makeSureFolderExists)(outputDir);
    await (0, utils_1.makeSureFolderExists)(fullTempDir);
    const audioWavExists = fs.existsSync(path.join(fullTempDir, `audio.wav`));
    if (audioWavExists) {
        await (0, utils_1.mergeAudioWithVideo)(path.join(fullTempDir, `audio.wav`), path.join(fullTempDir, `visuals.${ffmpeg_exporter_server_1.extensions[format]}`), path.join(outputDir, `${outputFilename}.${ffmpeg_exporter_server_1.extensions[format]}`), exports.audioCodecs[format]);
    }
    else {
        const destination = path.join(outputDir, `${outputFilename}.${ffmpeg_exporter_server_1.extensions[format]}`);
        await fs.promises.copyFile(path.join(fullTempDir, `visuals.${ffmpeg_exporter_server_1.extensions[format]}`), destination);
    }
    if (fullTempDir.endsWith('-undefined')) {
        await fs.promises
            .rm(fullTempDir, { recursive: true, force: true })
            .catch(() => { });
    }
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiZ2VuZXJhdGUtYXVkaW8uanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi9zcmMvZ2VuZXJhdGUtYXVkaW8udHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0FBdU5BLHNDQWdEQztBQUVELGdDQWlDQztBQXpTRCx1Q0FBeUI7QUFDekIsdUNBQXlCO0FBQ3pCLDJDQUE2QjtBQUM3QixxRUFBb0Q7QUFDcEQseUNBQTBDO0FBRTFDLG1DQU1pQjtBQUNqQix3Q0FBeUM7QUFFNUIsUUFBQSxXQUFXLEdBQ3RCO0lBQ0UsR0FBRyxFQUFFLEtBQUs7SUFDVixJQUFJLEVBQUUsU0FBUztJQUNmLE1BQU0sRUFBRSxLQUFLO0NBQ2QsQ0FBQztBQWVKLE1BQU0sV0FBVyxHQUFHLEtBQUssQ0FBQztBQUUxQixTQUFTLGlCQUFpQixDQUFDLE1BQXFCO0lBQzlDLE1BQU0sTUFBTSxHQUFpQixFQUFFLENBQUM7SUFFaEMsd0VBQXdFO0lBQ3hFLE1BQU0sWUFBWSxHQUFHLElBQUksR0FBRyxFQUF3QyxDQUFDO0lBRXJFLEtBQUssSUFBSSxLQUFLLEdBQUcsQ0FBQyxFQUFFLEtBQUssR0FBRyxNQUFNLENBQUMsTUFBTSxFQUFFLEtBQUssRUFBRSxFQUFFLENBQUM7UUFDbkQsS0FBSyxNQUFNLEtBQUssSUFBSSxNQUFNLENBQUMsS0FBSyxDQUFDLEVBQUUsQ0FBQztZQUNsQyxJQUFJLENBQUMsWUFBWSxDQUFDLEdBQUcsQ0FBQyxLQUFLLENBQUMsR0FBRyxDQUFDLEVBQUUsQ0FBQztnQkFDakMsc0ZBQXNGO2dCQUN0RixZQUFZLENBQUMsR0FBRyxDQUFDLEtBQUssQ0FBQyxHQUFHLEVBQUU7b0JBQzFCLEtBQUssRUFBRSxLQUFLLENBQUMsV0FBVztvQkFDeEIsR0FBRyxFQUFFLEtBQUssQ0FBQyxXQUFXO2lCQUN2QixDQUFDLENBQUM7Z0JBQ0gsTUFBTSxDQUFDLElBQUksQ0FBQztvQkFDVixHQUFHLEVBQUUs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