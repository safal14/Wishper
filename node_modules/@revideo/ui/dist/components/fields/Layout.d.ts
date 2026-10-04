import { ComponentChildren, HTMLAttributes } from 'preact';
export interface FieldSetProps {
    children: ComponentChildren;
    header: ComponentChildren;
    nested?: boolean;
}
export declare function FieldSet({ children, header, nested }: FieldSetProps): import("preact").JSX.Element;
export interface FieldValueProps extends HTMLAttributes<HTMLDivElement> {
    children: ComponentChildren;
    alignRight?: boolean;
    grow?: boolean;
}
export declare function FieldValue({ children, alignRight, grow, ...props }: FieldValueProps): import("preact").JSX.Element;
export interface FieldProps {
    label?: string;
    children: ComponentChildren;
    copy?: string;
}
export declare function Field({ label, copy, children }: FieldProps): import("preact").JSX.Element;
export interface FieldSurfaceProps extends HTMLAttributes<HTMLDivElement> {
    disabled?: boolean;
    open?: boolean;
}
export declare function FieldSurface({ disabled, open, className, ...props }: FieldSurfaceProps): import("preact").JSX.Element;
export interface NumericFieldProps extends FieldProps {
    children: number;
    precision?: number;
}
export declare function NumericField({ children, precision, ...props }: NumericFieldProps): import("preact").JSX.Element;
//# sourceMappingURL=Layout.d.ts.map