import { InputHTMLAttributes } from 'preact';
import { SelectProps } from './Select';
export type InputSelectProps<T> = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> & SelectProps<T>;
export declare function InputSelect<T extends string | number>({ options, value, onChange, ...props }: InputSelectProps<T>): import("preact").JSX.Element;
//# sourceMappingURL=InputSelect.d.ts.map