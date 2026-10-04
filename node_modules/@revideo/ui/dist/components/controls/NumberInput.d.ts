import { InputHTMLAttributes } from 'preact';
type NumberInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'min' | 'max' | 'step'> & {
    value: number;
    onChange: (value: number) => void;
    min?: number;
    max?: number;
    step?: number;
};
export declare function NumberInput({ value, onChange, min, max, step, ...props }: NumberInputProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=NumberInput.d.ts.map