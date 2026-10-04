import { ComponentChildren } from 'preact';
export interface TimelineState {
    /**
     * Length of the visible area in pixels.
     */
    viewLength: number;
    /**
     * Scroll offset from the left in pixels. Measured from frame 0.
     */
    offset: number;
    /**
     * First frame covered by the infinite scroll.
     */
    firstVisibleFrame: number;
    /**
     * Last frame covered by the infinite scroll.
     */
    lastVisibleFrame: number;
    /**
     * Frames per pixel rounded to the closest power of two.
     */
    density: number;
    /**
     * Frames per timeline segment.
     */
    segmentDensity: number;
    /**
     * Convert frames to percents.
     */
    framesToPercents: (value: number) => number;
    /**
     * Convert frames to pixels.
     */
    framesToPixels: (value: number) => number;
    /**
     * Convert pixels to frames.
     */
    pixelsToFrames: (value: number) => number;
    /**
     * Convert current pointer position to frames.
     */
    pointerToFrames: (value: number) => number;
}
export declare function TimelineContextProvider({ state, children, }: {
    state: TimelineState;
    children: ComponentChildren;
}): import("preact").JSX.Element;
export declare function useTimelineContext(): TimelineState;
//# sourceMappingURL=timeline.d.ts.map