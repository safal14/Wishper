export interface ViewportState {
    x: number;
    y: number;
    rect: DOMRectReadOnly;
    zoom: number;
    grid: boolean;
    resolutionScale: number;
}
export declare const ViewportProvider: import('preact').Provider<ViewportState>;
export declare function useViewportContext(): ViewportState;
//# sourceMappingURL=viewport.d.ts.map