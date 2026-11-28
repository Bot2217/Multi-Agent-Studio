import { CircleAlert, CircleCheck, CircleDashed, Radio } from "lucide-react";
import type { ReactNode } from "react";

const styles = {
  idle: { Icon: CircleDashed, className: "text-muted" },
  running: { Icon: Radio, className: "text-accent" },
  done: { Icon: CircleCheck, className: "text-ok" },
  error: { Icon: CircleAlert, className: "text-danger" },
};

export function Status({
  tone,
  children,
}: {
  tone: keyof typeof styles;
  children: ReactNode;
}) {
  const { Icon, className } = styles[tone];
  return (
    <span className={`ulei-status inline-flex items-center gap-1.5 text-sm font-medium ${className}`}>
      <Icon aria-hidden size={16} />
      {children}
    </span>
  );
}
