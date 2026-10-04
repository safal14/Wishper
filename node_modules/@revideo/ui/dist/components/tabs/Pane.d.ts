import { ComponentChildren, HTMLAttributes } from 'preact';
export interface PaneProps extends HTMLAttributes<HTMLDivElement> {
    title: string;
    id?: string;
    children: ComponentChildren;
}
export declare function Pane({ title, id, children, ...props }: PaneProps): import("preact").JSX.Element;
//# sourceMappingURL=Pane.d.ts.map