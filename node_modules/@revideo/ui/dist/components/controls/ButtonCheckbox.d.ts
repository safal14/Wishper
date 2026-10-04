import { ButtonProps } from './Button';
export interface ButtonCheckboxProps extends ButtonProps {
    checked?: boolean;
    onChecked?: (checked: boolean) => void;
}
export declare function ButtonCheckbox({ checked, onChecked, ...props }: ButtonCheckboxProps): import("preact").JSX.Element;
//# sourceMappingURL=ButtonCheckbox.d.ts.map