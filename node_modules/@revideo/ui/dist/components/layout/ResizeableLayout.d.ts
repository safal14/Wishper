import { Signal } from '@preact/signals';
import { ComponentChild } from 'preact';
interface ResizeableLayoutProps {
    id: string;
    vertical?: boolean;
    hidden: Signal<boolean>;
    offset?: number;
    children: [ComponentChild, ComponentChild];
}
export declare function ResizeableLayout({ id, children: [start, end], vertical, offset, hidden, }: ResizeableLayoutProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=ResizeableLayout.d.ts.map