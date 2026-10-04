import { ComponentChildren } from 'preact';
interface IconButtonProps {
    title?: string;
    onClick?: () => void;
    children: ComponentChildren;
    disabled?: boolean;
    className?: string;
}
export declare function IconButton({ children, onClick, title, className, disabled, }: IconButtonProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=IconButton.d.ts.map