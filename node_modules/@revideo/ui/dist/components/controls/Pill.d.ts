import { ComponentChildren } from 'preact';
export interface PillProps {
    children: ComponentChildren;
    checked: boolean;
    onChange: (value: boolean) => void;
    titleOn?: string;
    titleOff?: string;
}
export declare function Pill({ children, checked, onChange, titleOn, titleOff, }: PillProps): import("preact").JSX.Element;
//# sourceMappingURL=Pill.d.ts.map