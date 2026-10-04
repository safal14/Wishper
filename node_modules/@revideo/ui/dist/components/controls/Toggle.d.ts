import { ButtonHTMLAttributes } from 'preact';
export interface ToggleProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onToggle'> {
    open?: boolean;
    onToggle?: (value: boolean) => void;
    animated?: boolean;
}
export declare function Toggle({ open, onToggle, animated, ...props }: ToggleProps): import("preact").JSX.Element;
//# sourceMappingURL=Toggle.d.ts.map