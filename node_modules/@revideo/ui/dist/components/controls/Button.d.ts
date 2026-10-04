import { ButtonHTMLAttributes } from 'preact';
export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'loading'> {
    main?: boolean;
    loading?: boolean;
}
export declare function Button({ main, loading, className, ...props }: ButtonProps): import("preact").JSX.Element;
//# sourceMappingURL=Button.d.ts.map