# STALKER 2 Save Checker

Небольшой read-only чекер для флешек с чертежами улучшений в
**S.T.A.L.K.E.R. 2: Heart of Chornobyl**.

Он читает `CampaignsSave.sav`, сравнивает раздел `Analytics` с перечнем из
`Statistics.cfg` и показывает:

- сколько из 77 засчитываемых флешек найдено;
- ID недостающих флешек;
- готовые команды их физического спавна через консоль игры;
- состояние `RoyalFlush`, если оно читается из сейва.

Сейв **не изменяется** и **никуда не отправляется**.

## Быстрый запуск

Требования: Windows и Python 3.10 или новее.

1. Скачайте репозиторий через **Code → Download ZIP** и распакуйте его.
2. Запустите `check_stalker2_blueprints.bat` двойным кликом.

BAT-файл запускает Python-скрипт и не даёт окну закрыться, чтобы результат
можно было прочитать.

## Ручной запуск

```powershell
py stalker2_blueprint_checker.py --download-oodle
```

Скрипт автоматически ищет самый свежий файл здесь:

```text
%LOCALAPPDATA%\Stalker2\Saved\*\SaveGames\CampaignsSave.sav
```

Можно передать другой сейв явно:

```powershell
py stalker2_blueprint_checker.py `
  --save "D:\Backups\CampaignsSave.sav" `
  --download-oodle
```

После подбора флешки сделайте новый сейв либо выйдите в меню/из игры. Иначе
лежащий на диске `CampaignsSave.sav` может ещё показывать старый счётчик.

## Oodle-декодер

Для распаковки сейва требуется `oo2core_9_win64.dll`. Репозиторий не
распространяет эту DLL. Флаг `--download-oodle` скачивает закреплённый архив
Unpaker v1.1.0 и обязательно проверяет SHA-256 архива и самой DLL.

После первой загрузки DLL хранится локально:

```text
%LOCALAPPDATA%\stalker2-blueprint-checker\oo2core_9_win64.dll
```

Если DLL уже есть, её можно указать самостоятельно:

```powershell
py stalker2_blueprint_checker.py --oodle-dll "C:\Tools\oo2core_9_win64.dll"
```

## Дополнительные режимы

JSON для обработки другими программами:

```powershell
py stalker2_blueprint_checker.py --json --download-oodle
```

Записать команды спавна недостающих флешек в файл:

```powershell
py stalker2_blueprint_checker.py `
  --write-commands missing-blueprints.txt `
  --download-oodle
```

Команды имеют вид:

```text
XSpawnItemNearPlayerBySID Blueprint_Exoskeleton_Neutral_Armor_Upgrade_3
```

Предмет необходимо подобрать с земли. Добавление напрямую в инвентарь может
не обновить статистику.

## Что именно считается

Встроенный перечень содержит ровно 77 записей из `Blueprints.Items` в
`Statistics.cfg` версии игры 2.0.6.

`Blueprint_FaustPsyResist_Quest_1_1` намеренно не входит в этот перечень: это
квестовый чертёж, который может присутствовать в `Analytics`, но не увеличивает
счётчик флешек в КПК.

После обновлений игры, меняющих `Statistics.cfg`, список в
`COUNTED_BLUEPRINTS` необходимо сверить заново.

## Тесты

```powershell
py -m pip install pytest ruff
py -m pytest
py -m ruff check .
```
