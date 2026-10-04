import { ButtonProps } from './Button';
import { SelectProps } from './Select';
export type ButtonSelectProps<T> = Omit<ButtonProps, 'value' | 'onChange'> & SelectProps<T>;
export declare function ButtonSelect<T extends string | number>({ options, value, onChange, main, disabled, ...props }: ButtonSelectProps<T>): import("preact").JSX.Element;
//# sourceMappingURL=ButtonSelect.d.ts.map