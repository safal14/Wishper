import { ComponentChildren } from 'preact';
interface IconCheckboxProps {
    children: ComponentChildren;
    titleOn?: string;
    titleOff?: string;
    onChange?: (value: boolean) => void;
    checked?: boolean;
    main?: boolean;
}
export declare function IconCheckbox({ children, titleOn, titleOff, onChange, checked, main, }: IconCheckboxProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=IconCheckbox.d.ts.map