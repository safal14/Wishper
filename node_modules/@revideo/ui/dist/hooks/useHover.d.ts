import { default as React } from 'react';
type UseHoverType<T extends HTMLElement> = [React.RefObject<T>, boolean];
export declare function useHover<T extends HTMLElement>(handleMouseOver?: () => void, handleMouseOut?: () => void): UseHoverType<T>;
export {};
//# sourceMappingURL=useHover.d.ts.map