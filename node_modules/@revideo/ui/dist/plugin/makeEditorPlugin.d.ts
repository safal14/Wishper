import { EditorPlugin } from './EditorPlugin';
/**
 * A helper function for exporting editor plugins.
 *
 * @param plugin - The plugin configuration.
 *
 * @example
 * ```ts
 * export default makePlugin({
 *   name: 'my-custom-plugin',
 * });
 * ```
 *
 * @experimental
 */
export declare function makeEditorPlugin(plugin: EditorPlugin | (() => EditorPlugin)): () => EditorPlugin;
//# sourceMappingURL=makeEditorPlugin.d.ts.map