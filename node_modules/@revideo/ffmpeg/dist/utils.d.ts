export type AudioCodec = 'aac' | 'libopus';
export declare function resolvePath(output: string, assetPath: string): string;
export declare function makeSureFolderExists(folderPath: string): Promise<void>;
export declare function concatenateMedia(files: string[], outputFile: string): Promise<void>;
export declare function createSilentAudioFile(filePath: string, duration: number): Promise<unknown>;
export declare function getVideoDuration(filePath: string): Promise<number>;
export declare function getVideoDimensions(filePath: string): Promise<{
    width: number;
    height: number;
}>;
export declare function doesFileExist(filePath: string): Promise<boolean>;
export declare function mergeAudioWithVideo(audioPath: string, videoPath: string, outputPath: string, audioCodec?: AudioCodec): Promise<void>;
export declare function checkForAudioStream(file: string): Promise<boolean>;
export declare function getSampleRate(filePath: string): Promise<number>;
export declare function getVideoCodec(filePath: string): Promise<string>;
export declare function getVideoMetadata(filePath: string): Promise<{
    codec: string;
    width: number;
    height: number;
}>;
//# sourceMappingURL=utils.d.ts.map