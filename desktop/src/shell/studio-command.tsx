import * as Dialog from "@radix-ui/react-dialog";
import { Search } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "../components/ui/button";
import { Field } from "../components/ui/field";
import type { Messages } from "../locales";

type Command = { label: string; action: () => void };

export function StudioCommand({
  t,
  commands,
  disabled,
}: {
  t: Messages;
  commands: Command[];
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const first = useRef<HTMLButtonElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const navigated = useRef(false);
  const matching = commands.filter(({ label }) =>
    label.toLowerCase().includes(query.trim().toLowerCase()),
  );

  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (disabled || event.repeat || event.altKey || event.shiftKey) return;
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, [disabled]);

  function run(command: Command) {
    navigated.current = true;
    setOpen(false);
    command.action();
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button
          ref={trigger}
          variant="quiet"
          title="Ctrl / ⌘ + K"
          disabled={disabled}
        >
          <Search size={16} aria-hidden />
          {t.commandPalette}
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="studio-overlay" />
        <Dialog.Content
          className="studio-dialog studio-command"
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            setQuery("");
            input.current?.focus();
          }}
          onCloseAutoFocus={(event) => {
            if (!navigated.current) return;
            event.preventDefault();
            navigated.current = false;
            if (document.activeElement === document.body)
              trigger.current?.focus();
          }}
        >
          <Dialog.Title>{t.commandPalette}</Dialog.Title>
          <Dialog.Description className="sr-only">
            {t.commandSearch}
          </Dialog.Description>
          <Field
            ref={input}
            type="search"
            label={t.commandSearch}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                first.current?.focus();
              } else if (event.key === "Enter" && matching[0]) {
                event.preventDefault();
                run(matching[0]);
              }
            }}
          />
          <ul className="studio-command-list">
            {matching.map((command, index) => (
              <li key={command.label}>
                <Button
                  ref={index === 0 ? first : undefined}
                  variant="quiet"
                  onClick={() => run(command)}
                >
                  {command.label}
                </Button>
              </li>
            ))}
          </ul>
          {!matching.length && <p role="status">{t.noResults}</p>}
          <Dialog.Close asChild>
            <Button variant="secondary">{t.close}</Button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
