import { ComponentChildren } from 'preact';
export type Shortcut = {
    key: string;
    action: string;
    available?: () => boolean;
};
export type ShortcutModules = 'global' | 'timeline' | 'viewport' | 'none';
type ShortcutsByModule = Record<ShortcutModules, Shortcut[]>;
type ShortcutsState = {
    currentModule: ShortcutModules;
    shortcuts: ShortcutsByModule;
    setCurrentModule?: (module: ShortcutModules) => void;
};
export declare function ShortcutsProvider({ children }: {
    children: ComponentChildren;
}): import("preact").JSX.Element;
export declare function useShortcuts(): ShortcutsState;
export {};
//# sourceMappingURL=shortcuts.d.ts.map