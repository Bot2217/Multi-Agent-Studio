# Как предложить изменение

Ядро «Улей» (репозиторий Multi-Agent-Studio) открыто на условиях GNU AGPL-3.0 или более поздней версии. Коммерческие лицензии и «Улей Pro» выдаёт автор, Bot2217.

## Что нужно перед запросом на слияние

1. Прочитайте [CLA.md](CLA.md).
2. Откройте pull request.
3. В комментарии к этому pull request напишите ровно эту фразу:

   ```
   I have read the CLA Document and I hereby sign the CLA
   ```

   Без этой подписи проверка CLA не пройдёт. Подписи хранятся в `signatures/cla.json` на ветке `cla-signatures`. Файл создаёт действие GitHub при первой подписи, его не нужно добавлять вручную.

Владелец Bot2217, соавтор Vlasov-Timofey и боты `cursor[bot]`, `dependabot[bot]`, `github-actions[bot]` в списке исключений и подпись не ставят.

## Как устроен запрос

1. Склонируйте репозиторий и сделайте ветку от `main`.
2. Меняйте только то, что нужно для задачи.
3. Локально прогоните проверки, которые гоняет CI:

   ```bash
   python -m pip install -r requirements.txt -r requirements-dev.txt
   ruff format --check .
   ruff check .
   pytest -q
   ```

4. Откройте pull request в `main` и подпишите CLA комментарием выше.

Не присылайте секретные ключи, файлы `.env` и приватный ключ подписи обновлений.
