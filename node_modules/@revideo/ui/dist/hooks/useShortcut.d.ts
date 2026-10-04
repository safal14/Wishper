import { ShortcutModules } from '../contexts/shortcuts';
type UseHoverType<T extends HTMLElement> = [React.RefObject<T>, boolean];
export declare function useShortcut<T extends HTMLElement>(shortcutModule: ShortcutModules): UseHoverType<T>;
export {};
//# sourceMappingURL=useShortcut.d.ts.map