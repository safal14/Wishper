import { InputHTMLAttributes } from 'preact';
import { SelectProps } from './Select';
export type NumberInputSelectProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'min' | 'max' | 'step'> & SelectProps<number> & {
    value: number;
    min?: number;
    max?: number;
    step?: number;
};
export declare function NumberInputSelect({ options, value, onChange, ...props }: NumberInputSelectProps): import("preact").JSX.Element;
//# sourceMappingURL=NumberInputSelect.d.ts.map