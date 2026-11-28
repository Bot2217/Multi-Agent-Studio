import { CircleAlert, CircleCheck, Inbox } from "lucide-react";
import type { ReactNode } from "react";

const stateStyles = {
  empty: { Icon: Inbox, className: "text-muted" },
  error: { Icon: CircleAlert, className: "text-danger" },
  success: { Icon: CircleCheck, className: "text-ok" },
};

type StatePanelProps = {
  kind?: keyof typeof stateStyles;
  title: string;
  description: string;
  action?: ReactNode;
  announce?: boolean;
};

export function StatePanel({
  kind = "empty",
  title,
  description,
  action,
  announce = false,
}: StatePanelProps) {
  const { Icon, className } = stateStyles[kind];
  return (
    <div className="ulei-state flex flex-col items-start gap-3 rounded-metric border border-solid border-line p-4">
      <Icon size={24} aria-hidden className={className} />
      <div className="grid gap-1" aria-live={announce ? "polite" : undefined} aria-atomic={announce || undefined}>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-sm leading-relaxed text-muted">{description}</p>
      </div>
      {action}
    </div>
  );
}
