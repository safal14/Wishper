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
exports.resolvePath = resolvePath;
exports.makeSureFolderExists = makeSureFolderExists;
exports.concatenateMedia = concatenateMedia;
exports.createSilentAudioFile = createSilentAudioFile;
exports.getVideoDuration = getVideoDuration;
exports.getVideoDimensions = getVideoDimensions;
exports.doesFileExist = doesFileExist;
exports.mergeAudioWithVideo = mergeAudioWithVideo;
exports.checkForAudioStream = checkForAudioStream;
exports.getSampleRate = getSampleRate;
exports.getVideoCodec = getVideoCodec;
exports.getVideoMetadata = getVideoMetadata;
const ffmpeg = require("fluent-ffmpeg");
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
const path = __importStar(require("path"));
const uuid_1 = require("uuid");
const settings_1 = require("./settings");
function resolvePath(output, assetPath) {
    let resolvedPath;
    if (assetPath.startsWith('http://') ||
        assetPath.startsWith('https://') ||
        assetPath.startsWith('data:')) {
        resolvedPath = assetPath;
    }
    else {
        resolvedPath = path.join(output, '../public', assetPath);
    }
    return resolvedPath;
}
async function makeSureFolderExists(folderPath) {
    if (await fs.promises
        .access(folderPath)
        .then(() => false)
        .catch(() => true)) {
        await fs.promises.mkdir(folderPath, { recursive: true });
    }
}
async function concatenateMedia(files, outputFile) {
    const tempFile = path.join(os.tmpdir(), `${(0, uuid_1.v4)()}.txt`);
    const fileContent = files
        .map(file => `file '${file.replace(/'/g, "\\'")}'`)
        .join('\n');
    await fs.promises.writeFile(tempFile, fileContent);
    return new Promise((resolve, reject) => {
        ffmpeg.setFfmpegPath(settings_1.ffmpegSettings.getFfmpegPath());
        const ffmpegCommand = ffmpeg();
        ffmpegCommand
            .input(tempFile)
            .inputOptions([
            '-f concat',
            '-safe 0',
            '-protocol_whitelist file,http,https,tcp,tls',
        ])
            .outputOptions(['-c copy'])
            .on('error', err => {
            console.error('Error:', err);
            fs.promises.unlink(tempFile).catch(console.error);
            reject(err); // Reject the promise on error
        })
            .on('end', () => {
            fs.promises.unlink(tempFile).catch(console.error);
            resolve(); // Resolve the promise on successful completion
        })
            .save(outputFile);
    });
}
async function createSilentAudioFile(filePath, duration) {
    ffmpeg.setFfmpegPath(settings_1.ffmpegSettings.getFfmpegPath());
    return new Promise((resolve, reject) => {
        ffmpeg()
            .addInput(`anullsrc=channel_layout=stereo:sample_rate=${48000}`)
            .inputFormat('lavfi')
            .duration(duration)
            .on('end', () => {
            resolve(filePath);
        })
            .on('error', err => {
            console.error('Error creating silent audio file:', err);
            reject(err);
        })
            .save(filePath);
    });
}
async function getVideoDuration(filePath) {
    ffmpeg.setFfprobePath(settings_1.ffmpegSettings.getFfprobePath());
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) {
                reject(err);
                return;
            }
            const duration = metadata.format.duration;
            if (duration) {
                resolve(duration);
            }
            else {
                reject(new Error('Could not determine video duration.'));
            }
        });
    });
}
async function getVideoDimensions(filePath) {
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) {
                console.error('Error getting video dimensions:', err);
                reject(new Error('Failed to get video dimensions'));
                return;
            }
            const videoStream = metadata.streams.find(stream => stream.codec_type === 'video');
            if (videoStream && videoStream.width && videoStream.height) {
                resolve({
                    width: videoStream.width,
                    height: videoStream.height,
                });
            }
            reject(new Error('Could not find video dimensions in metadata'));
        });
    });
}
async function doesFileExist(filePath) {
    try {
        await fs.promises.access(filePath, fs.constants.F_OK);
        return true;
    }
    catch {
        return false;
    }
}
async function mergeAudioWithVideo(audioPath, videoPath, outputPath, audioCodec = 'aac') {
    ffmpeg.setFfmpegPath(settings_1.ffmpegSettings.getFfmpegPath());
    return new Promise((resolve, reject) => {
        ffmpeg()
            .input(videoPath)
            .input(audioPath)
            .outputOptions([
            '-c:v',
            'copy',
            '-c:a',
            audioCodec,
            '-strict',
            'experimental',
        ])
            .on('end', () => {
            resolve();
        })
            .on('error', err => {
            console.error(`Error merging video and audio: ${err.message}`);
            reject(err);
        })
            .save(outputPath);
    });
}
async function checkForAudioStream(file) {
    ffmpeg.setFfprobePath(settings_1.ffmpegSettings.getFfprobePath());
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(file, (err, metadata) => {
            if (err) {
                console.error(`error checking for audioStream for file ${file}`, err);
                reject(err);
                return;
            }
            const audioStreams = metadata.streams.filter(s => s.codec_type === 'audio');
            resolve(audioStreams.length > 0);
        });
    });
}
async function getSampleRate(filePath) {
    ffmpeg.setFfprobePath(settings_1.ffmpegSettings.getFfprobePath());
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) {
                reject(err);
                return;
            }
            const audioStream = metadata.streams.find(s => s.codec_type === 'audio');
            if (audioStream && audioStream.sample_rate) {
                resolve(audioStream.sample_rate);
            }
            else {
                reject(new Error('No audio stream found'));
            }
        });
    });
}
async function getVideoCodec(filePath) {
    ffmpeg.setFfprobePath(settings_1.ffmpegSettings.getFfprobePath());
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) {
                reject(err);
                return;
            }
            const videoStream = metadata.streams.find(s => s.codec_type === 'video');
            if (videoStream && videoStream.codec_name) {
                resolve(videoStream.codec_name);
            }
            else {
                reject(new Error('No video stream found'));
            }
        });
    });
}
async function getVideoMetadata(filePath) {
    ffmpeg.setFfprobePath(settings_1.ffmpegSettings.getFfprobePath());
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) {
                reject(err);
                return;
            }
            const videoStream = metadata.streams.find(s => s.codec_type === 'video');
            if (videoStream &&
                videoStream.codec_name &&
                videoStream.width &&
                videoStream.height) {
                resolve({
                    codec: videoStream.codec_name,
                    width: videoStream.width,
                    height: videoStream.height,
                });
            }
            else {
                reject(new Error('Unable to retrieve complete video information'));
            }
        });
    });
}
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoidXRpbHMuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi9zcmMvdXRpbHMudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7QUFTQSxrQ0FZQztBQUVELG9EQVNDO0FBRUQsNENBaUNDO0FBRUQsc0RBb0JDO0FBRUQsNENBaUJDO0FBRUQsZ0RBdUJDO0FBRUQsc0NBT0M7QUFFRCxrREE2QkM7QUFFRCxrREFpQkM7QUFFRCxzQ0FpQkM7QUFFRCxzQ0FpQkM7QUFFRCw0Q0E0QkM7QUFwUUQsd0NBQXlDO0FBQ3pDLHVDQUF5QjtBQUN6Qix1Q0FBeUI7QUFDekIsMkNBQTZCO0FBQzdCLCtCQUFrQztBQUNsQyx5Q0FBMEM7QUFJMUMsU0FBZ0IsV0FBVyxDQUFDLE1BQWMsRUFBRSxTQUFpQjtJQUMzRCxJQUFJLFlBQW9CLENBQUM7SUFDekIsSUFDRSxTQUFTLENBQUMsVUFBVSxDQUFDLFNBQVMsQ0FBQztRQUMvQixTQUFTLENBQUMsVUFBVSxDQUFDLFVBQVUsQ0FBQztRQUNoQyxTQUFTLENBQUMsVUFBVSxDQUFDLE9BQU8sQ0FBQyxFQUM3QixDQUFDO1FBQ0QsWUFBWSxHQUFHLFNBQVMsQ0FBQztJQUMzQixDQUFDO1NBQU0sQ0FBQztRQUNOLFlBQVksR0FBRyxJQUFJLENBQUMsSUFBSSxDQUFDLE1BQU0sRUFBRSxXQUFXLEVBQUUsU0FBUyxDQUFDLENBQUM7SUFDM0QsQ0FBQztJQUNELE9BQU8sWUFBWSxDQUFDO0FBQ3RCLENBQUM7QUFFTSxLQUFLLFVBQVUsb0JBQW9CLENBQUMsVUFBa0I7SUFDM0QsSUFDRSxNQUFNLEVBQUUsQ0FBQyxRQUFRO1NBQ2QsTUFBTSxDQUFDLFVBQVUsQ0FBQztTQUNsQixJQUFJLENBQUMsR0FBRyxFQUFFLENBQUMsS0FBSyxDQUFDO1NBQ2pCLEtBQUssQ0FBQyxHQUFHLEVBQUUsQ0FBQyxJQUFJLENBQUMsRUFDcEIsQ0FBQztRQUNELE1BQU0sRUFBRSxDQUFDLFFB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