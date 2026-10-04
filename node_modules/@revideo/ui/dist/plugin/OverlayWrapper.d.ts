import { HTMLAttributes } from 'preact';
type PreviewCanvasProps = HTMLAttributes<HTMLDivElement>;
/**
 * A wrapper for custom overlays.
 *
 * @remarks
 * Used to implement {@link PluginOverlayConfig.component}.
 *
 * @param className - The class name to apply to the overlay.
 * @param rest - Any other props to pass to the div. Can be used to hook up
 *               pointer events.
 */
export declare function OverlayWrapper({ className, ...rest }: PreviewCanvasProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=OverlayWrapper.d.ts.map