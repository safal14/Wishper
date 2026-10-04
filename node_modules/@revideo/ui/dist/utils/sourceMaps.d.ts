import { SourceMapConsumer } from 'source-map-js';
declare module 'source-map-js' {
    interface SourceMapConsumer {
        raw: any;
    }
}
export interface StackTraceEntry {
    file: string;
    uri: string;
    line: number;
    column: number;
    isExternal: boolean;
    functionName?: string;
    source?: string;
    sourceMap?: SourceMapConsumer;
}
export declare function resolveStackTrace(stack: string, firstOnly: true): Promise<StackTraceEntry>;
export declare function resolveStackTrace(stack: string): Promise<StackTraceEntry[]>;
export declare function openFileInEditor(entry: StackTraceEntry): Promise<void>;
export declare function getSourceCodeFrame(entry: StackTraceEntry): string | null;
export declare function findAndOpenFirstUserFile(stack: string): Promise<void>;
//# sourceMappingURL=sourceMaps.d.ts.map