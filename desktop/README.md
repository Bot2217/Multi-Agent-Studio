# Улей / Ulei

Оболочка рабочего стола. Сборка описана в [справочнике](../docs/GUIDE.md#desktop).

```bash
bash build-backend.sh
npm install
npm run tauri build
```

Имя окна и установщика — «Улей». Бинарник — `ulei`, идентификатор — `com.bot2217.ulei`. Вложения релиза называются `Ulei_0.1.3_...`.

## Дизайн-система нового окна

Из каталога `desktop/` запустите `npm ci` и `npm run storybook`.
В верхней панели Storybook выбираются палитра, режим и язык. История «Обзор»
показывает основные компоненты на примере запуска и повторного подключения.
История «Ошибка поля» открывает форму сразу в состоянии ошибки.

Исходник темы — `design/tokens.json`. После его изменения выполните
`npm run tokens`. Сгенерированный CSS подключён к токенам Tailwind в
`src/foundation.css`.

`npm run build-storybook` собирает статическое превью. Для проверки в Chromium
выполните `npx playwright install chromium`, затем `npm run test:foundation`.
При необходимости задайте абсолютный путь в `ULEI_SCREENSHOTS`, чтобы сохранить
снимки тем в обеих ширинах.

Сдача этой работы согласована через Storybook без Figma.
В группе «Улей / Студия» доступны оболочка, первый запуск, недоступный движок
и обновление. В группе «Улей / События запуска» можно пошагово проиграть
JSON из примеров контракта, неизвестный кадр и остановку.

Типы контракта генерируются из корня репозитория следующей командой.
Параметр unreachableDefinitions нужен для объявлений из секции $defs.

```bash
npx json-schema-to-typescript docs/contracts/ulei-contract-v1.schema.json --unreachableDefinitions -o desktop/src/contract/ulei-contract-v1.d.ts
```
