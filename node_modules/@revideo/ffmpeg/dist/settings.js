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
exports.ffmpegSettings = void 0;
const ffmpegInstaller = __importStar(require("@ffmpeg-installer/ffmpeg"));
const ffprobeInstaller = __importStar(require("@ffprobe-installer/ffprobe"));
const ffmpegLogLevels = [
    'quiet',
    'panic',
    'fatal',
    'error',
    'warning',
    'info',
    'verbose',
    'debug',
    'trace',
];
class FfmpegSettingState {
    constructor() {
        this.ffmpegPath = ffmpegInstaller.path;
        this.ffprobePath = ffprobeInstaller.path;
        // Use the FFMPEG_PATH environment variable if it is set
        if (process.env.FFMPEG_PATH) {
            this.ffmpegPath = process.env.FFMPEG_PATH;
        }
        // Use the FFPROBE_PATH environment variable if it is set
        if (process.env.FFPROBE_PATH) {
            this.ffprobePath = process.env.FFPROBE_PATH;
        }
        this.logLevel = 'error';
        // Use the FFMPEG_LOG_LEVEL environment variable if it is set
        if (process.env.FFMPEG_LOG_LEVEL &&
            ffmpegLogLevels.includes(process.env.FFMPEG_LOG_LEVEL)) {
            this.logLevel = process.env.FFMPEG_LOG_LEVEL;
        }
    }
    getFfmpegPath() {
        return this.ffmpegPath;
    }
    setFfmpegPath(ffmpegPath) {
        this.ffmpegPath = ffmpegPath;
    }
    getFfprobePath() {
        return this.ffprobePath;
    }
    setFfprobePath(ffprobePath) {
        this.ffprobePath = ffprobePath;
    }
    getLogLevel() {
        return this.logLevel;
    }
    setLogLevel(logLevel) {
        this.logLevel = logLevel;
    }
}
exports.ffmpegSettings = new FfmpegSettingState();
//# sourceMappingURL=data:application/json;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoic2V0dGluZ3MuanMiLCJzb3VyY2VSb290IjoiIiwic291cmNlcyI6WyIuLi9zcmMvc2V0dGluZ3MudHMiXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6Ijs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7O0FBQUEsMEVBQTREO0FBQzVELDZFQUErRDtBQUUvRCxNQUFNLGVBQWUsR0FBRztJQUN0QixPQUFPO0lBQ1AsT0FBTztJQUNQLE9BQU87SUFDUCxPQUFPO0lBQ1AsU0FBUztJQUNULE1BQU07SUFDTixTQUFTO0lBQ1QsT0FBTztJQUNQLE9BQU87Q0FDQyxDQUFDO0FBVVgsTUFBTSxrQkFBa0I7SUFLdEI7UUFDRSxJQUFJLENBQUMsVUFBVSxHQUFHLGVBQWUsQ0FBQyxJQUF5QixDQUFDO1FBQzVELElBQUksQ0FBQyxXQUFXLEdBQUcsZ0JBQWdCLENBQUMsSUFBeUIsQ0FBQztRQUU5RCx3REFBd0Q7UUFDeEQsSUFBSSxPQUFPLENBQUMsR0FBRyxDQUFDLFdBQVcsRUFBRSxDQUFDO1lBQzVCLElBQUksQ0FBQyxVQUFVLEdBQUcsT0FBTyxDQUFDLEdBQUcsQ0FBQyxXQUFXLENBQUM7UUFDNUMsQ0FBQztRQUVELHlEQUF5RDtRQUN6RCxJQUFJLE9BQU8sQ0FBQyxHQUFHLENBQUMsWUFBWSxFQUFFLENBQUM7WUFDN0IsSUFBSSxDQUFDLFdBQVcsR0FBRyxPQUFPLENBQUMsR0FBRyxDQUFDLFlBQVksQ0FBQztRQUM5QyxDQUFDO1FBRUQsSUFBSSxDQUFDLFFBQVEsR0FBRyxPQUFPLENBQUM7UUFFeEIsNkRBQTZEO1FBQzdELElBQ0UsT0FBTyxDQUFDLEdBQUcsQ0FBQyxnQkFBZ0I7WUFDNUIsZUFBZSxDQUFDLFFBQVEsQ0FBQyxPQUFPLENBQUMsR0FBRyxDQUFDLGdCQUE0QixDQUFDLEVBQ2xFLENBQUM7WUFDRCxJQUFJLENBQUMsUUFBUSxHQUFHLE9BQU8sQ0FBQyxHQUFHLENBQUMsZ0JBQTRCLENBQUM7UUFDM0QsQ0FBQztJQUNILENBQUM7SUFFTSxhQUFhO1FBQ2xCLE9BQU8sSUFBSSxDQUFDLFVBQVUsQ0FBQztJQUN6QixDQUFDO0lBRU0sYUFBYSxDQUFDLFVBQWtCO1FBQ3JDLElBQUksQ0FBQyxVQUFVLEdBQUcsVUFBVSxDQUFDO0lBQy9CLENBQUM7SUFFTSxjQUFjO1FBQ25CLE9BQU8sSUFBSSxDQUFDLFdBQVcsQ0FBQztJQUMxQixDQUFDO0lBRU0sY0FBYyxDQUFDLFdBQW1CO1FBQ3ZDLElBQUksQ0FBQyxXQUFXLEdBQUcsV0FBVyxDQUFDO0lBQ2pDLENBQUM7SUFFTSxXQUFXO1FBQ2hCLE9BQU8sSUFBSSxDQUFDLFFBQVEsQ0FBQztJQUN2QixDQUFDO0lBRU0sV0FBVyxDQUFDLFFBQWtCO1FBQ25DLElBQUksQ0FBQyxRQUFRLEdBQUcsUUFBUSxDQUFDO0lBQzNCLENBQUM7Q0FDRjtBQUVZLFFBQUEsY0FBYyxHQUFHLElBQUksa0JBQWtCLEVBQUUsQ0FBQyJ9