import { PluginTabConfig } from '../../plugin';
export interface ElementSwitchProps<T extends string> {
    value: T;
    cases: Partial<Record<T, PluginTabConfig['paneComponent']>>;
}
export declare function ElementSwitch<T extends string>({ value, cases, }: ElementSwitchProps<T>): import("preact").JSX.Element;
//# sourceMappingURL=ElementSwitch.d.ts.map