import { AnchorHTMLAttributes, ButtonHTMLAttributes, ComponentChildren, HTMLAttributes, Ref } from 'preact';
interface TabsState {
    tab: string | null;
    setTab: (tab: string | null) => void;
}
export declare function Tabs({ className, ...props }: HTMLAttributes<HTMLDivElement>): import("preact").JSX.Element;
export interface TabGroupProps extends TabsState {
    children: ComponentChildren;
}
export declare function TabGroup({ children, ...rest }: TabGroupProps): import("preact").JSX.Element;
export interface TabProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    children: ComponentChildren;
    forwardRef?: Ref<HTMLButtonElement>;
    tab: string;
}
export declare function Tab({ className, tab, forwardRef, ...props }: TabProps): import("preact").JSX.Element;
export interface TabLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
    children: ComponentChildren;
    disabled?: boolean;
}
export declare function TabLink({ className, href, disabled, ...props }: TabLinkProps): import("preact").JSX.Element;
export declare function Space(): import("preact").JSX.Element;
export {};
//# sourceMappingURL=Tabs.d.ts.map