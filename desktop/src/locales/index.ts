import en from "./en.json";
import ru from "./ru.json";

export type Locale = "ru" | "en";
export type Messages = Record<keyof typeof en, string>;

const messages: Record<Locale, Messages> = { ru, en };

export function getMessages(locale: Locale): Messages {
  return messages[locale];
}
