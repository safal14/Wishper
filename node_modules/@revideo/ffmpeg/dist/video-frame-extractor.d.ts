type VideoFrameExtractorState = 'processing' | 'done' | 'error';
/**
 * Walks through a video file and extracts frames.
 */
export declare class VideoFrameExtractor {
    private static readonly chunkLengthInSeconds;
    private readonly ffmpegPath;
    state: VideoFrameExtractorState;
    filePath: string;
    private downloadedFilePath;
    private buffer;
    private bufferOffset;
    private imageBuffers;
    private lastImage;
    private startTime;
    private startTimeOffset;
    private duration;
    private toTime;
    private fps;
    private framesProcessed;
    private width;
    private height;
    private frameSize;
    private codec;
    private process;
    private terminated;
    static downloadedVideoMap: Map<string, {
        localPath: string;
        startTimeOffset: number;
    }>;
    constructor(filePath: string, startTime: number, fps: number, duration: number);
    static downloadVideoChunk(url: string, startTime: number, endTime: number): Promise<unknown>;
    getTime(): number;
    getLastTime(): number;
    getLastFrame(): Buffer<ArrayBufferLike> | null;
    getWidth(): number;
    getHeight(): number;
    private getEndTime;
    private getArgs;
    private createFfmpegProcess;
    /**
     * We call this in the case that the time requested is greater than the
     * duration of the video. In this case, we want to display the first frame
     * of the video.
     *
     * Note: This does NOT match the behavior of the old implementation
     * inside of 2d/src/lib/components/Video.ts. In the old implementation, the
     * last frame is shown instead of the first frame.
     */
    private createFfmpegProcessToExtractFirstFrame;
    private processData;
    popImage(): Promise<Buffer<ArrayBufferLike> | null>;
    private handleClose;
    private handleError;
    destroy(): void;
}
export {};
//# sourceMappingURL=video-frame-extractor.d.ts.map