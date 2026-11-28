import { useId, type ComponentProps } from "react";

type FieldProps = ComponentProps<"input"> & {
  label: string;
  hint?: string;
  error?: string;
};

export function Field({
  id,
  label,
  hint,
  error,
  "aria-describedby": describedBy,
  ...props
}: FieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const messageId = hint || error ? `${inputId}-message` : undefined;

  return (
    <div className="ulei-field">
      <label htmlFor={inputId}>{label}</label>
      <input
        {...props}
        id={inputId}
        className={`rounded-control ${props.className ?? ""}`}
        aria-invalid={error ? true : props["aria-invalid"]}
        aria-describedby={[describedBy, messageId].filter(Boolean).join(" ") || undefined}
      />
      {messageId && (
        <p id={messageId} className={error ? "text-danger" : "text-muted"}>
          {error || hint}
        </p>
      )}
    </div>
  );
}
