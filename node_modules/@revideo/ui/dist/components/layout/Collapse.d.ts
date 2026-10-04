import { ComponentChildren, HTMLAttributes } from 'preact';
export interface CollapseProps extends HTMLAttributes<HTMLDivElement> {
    open: boolean;
    children: ComponentChildren;
    animated?: boolean;
}
export declare function Collapse({ animated, ...props }: CollapseProps): import("preact").JSX.Element;
//# sourceMappingURL=Collapse.d.ts.map