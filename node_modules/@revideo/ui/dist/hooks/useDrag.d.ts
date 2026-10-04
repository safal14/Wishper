interface MoveCallback {
    (dx: number, dy: number, x: number, y: number): void;
}
interface DropCallback {
    (event: MouseEvent): void;
}
export declare function useDrag(onMove: MoveCallback, onDrop?: DropCallback, button?: number | null): [(event: MouseEvent) => void, boolean];
export {};
//# sourceMappingURL=useDrag.d.ts.map