/**
 * Get a matrix that transforms the overlay canvas space to the scene space.
 *
 * @remarks
 * When drawing a viewport overlay, the canvas overlays the entire preview
 * panel, no matter the zoom and pan of the scene itself. This ensures that
 * the gizmos drawn on top have high resolution no matter how zoomed-in the user
 * is.
 *
 * This matrix is used to transform the drawn points so that they appear where
 * they should be in the scene.
 */
export declare function useViewportMatrix(): DOMMatrix;
//# sourceMappingURL=useViewportMatrix.d.ts.map