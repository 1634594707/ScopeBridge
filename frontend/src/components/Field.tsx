import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "../lib/cn";

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  htmlFor?: string;
  children: ReactNode;
  className?: string;
}

export function Field({ label, hint, error, htmlFor, children, className }: FieldProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={htmlFor} className="text-[13px] font-medium text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-[12px] text-flag-bad">{error}</p>
      ) : hint ? (
        <p className="text-[12px] leading-relaxed text-ink-faint">{hint}</p>
      ) : null}
    </div>
  );
}

const controlBase =
  "w-full rounded-md border border-line bg-paper-card px-3 text-sm text-ink placeholder:text-ink-faint/70 transition-colors duration-150 hover:border-ink/20 focus:border-pine focus:outline-none focus:ring-2 focus:ring-pine/15";

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...rest} className={cn(controlBase, "h-10", className)} />;
}

export function TextArea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...rest}
      className={cn(controlBase, "min-h-[112px] resize-y py-2.5 leading-relaxed", className)}
    />
  );
}

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...rest} className={cn(controlBase, "h-10 cursor-pointer pr-8", className)}>
      {children}
    </select>
  );
}
