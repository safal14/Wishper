import { ComponentChildren } from 'preact';
export interface ExpandableProps {
    title: string;
    children: ComponentChildren;
    open?: boolean;
}
export declare function Expandable({ title, children, open }: ExpandableProps): import("preact").JSX.Element;
export interface ControlledExpandableProps {
    title: string;
    children: ComponentChildren;
    open: boolean;
    setOpen: (value: boolean) => void;
}
export declare function ControlledExpandable({ title, children, open, setOpen, }: ControlledExpandableProps): import("preact").JSX.Element;
//# sourceMappingURL=Expandable.d.ts.map