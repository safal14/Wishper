import { InputHTMLAttributes } from 'preact';
interface TimestampProps extends InputHTMLAttributes<HTMLInputElement> {
    frame: number;
    title: string;
    frameTitle: string;
    reverse?: boolean;
}
export declare function Timestamp({ frame, reverse, title, frameTitle, ...rest }: TimestampProps): import("preact").JSX.Element;
export {};
//# sourceMappingURL=Timestamp.d.ts.map