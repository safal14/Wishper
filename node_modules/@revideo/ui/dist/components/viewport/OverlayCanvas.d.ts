import { CanvasHTMLAttributes } from 'preact';
import { PluginDrawFunction } from '../../plugin';
interface OverlayCanvasProps extends CanvasHTMLAttributes<HTMLCanvasElement> {
    drawHooks: (() => PluginDrawFunction)[];
}
export declare function OverlayCanvas({ className, drawHooks, ...props }: OverlayCanvasProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=OverlayCanvas.d.ts.map