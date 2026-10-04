export interface SelectProps<T> {
    title?: string;
    options: {
        value: T;
        text: string;
    }[];
    className?: string;
    main?: boolean;
    disabled?: boolean;
    value: T;
    onChange: (value: T) => void;
}
export declare function Select<T>({ options, value, onChange, title, main, disabled, className, }: SelectProps<T>): import("preact").JSX.Element;
//# sourceMappingURL=Select.d.ts.map