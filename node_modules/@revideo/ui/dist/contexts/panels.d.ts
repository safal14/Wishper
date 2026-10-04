import { ReadonlySignal } from '@preact/signals';
import { ComponentChildren } from 'preact';
import { PluginInspectorConfig, PluginTabConfig } from '../plugin';
interface Panel {
    current: ReadonlySignal<string | null>;
    isHidden: ReadonlySignal<boolean>;
    set(value: string | null): void;
}
interface Panels {
    sidebar: Panel;
    bottom: Panel;
    tabs: PluginTabConfig[];
    inspectors: PluginInspectorConfig[];
}
export declare function usePanels(): Panels;
export declare function PanelsProvider({ children }: {
    children: ComponentChildren;
}): import("preact").JSX.Element;
export {};
//# sourceMappingURL=panels.d.ts.map