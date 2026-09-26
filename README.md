# STALKER 2 Save Checker

Показывает, какие из 77 флешек с чертежами улучшений не найдены в
**S.T.A.L.K.E.R. 2: Heart of Chornobyl**.

## Как запустить

Нужны **Windows** и **Python 3.10 или новее**.

1. Нажмите **Code → Download ZIP** и распакуйте архив.
2. Откройте распакованную папку.
3. Запустите `check_stalker2_blueprints.bat` двойным кликом.

Либо откройте PowerShell в этой папке и выполните:

```powershell
py stalker2_blueprint_checker.py --download-oodle
```

Скрипт сам найдёт `CampaignsSave.sav` и покажет счётчик, недостающие флешки и
команды для их спавна. Сейв не изменяется и никуда не отправляется.

После подбора флешки сделайте новый сейв либо выйдите в меню/из игры, чтобы
`CampaignsSave.sav` успел обновиться.

<details>
<summary><strong>Подробнее</strong></summary>

### Где ищется сейв

По умолчанию выбирается самый свежий файл внутри:

```text
%LOCALAPPDATA%\Stalker2\Saved\*\SaveGames\CampaignsSave.sav
```

Другой сейв можно передать явно:

```powershell
py stalker2_blueprint_checker.py `
  --save "D:\Backups\CampaignsSave.sav" `
  --download-oodle
```

### Oodle-декодер

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

### Дополнительные режимы

Вывести результат в JSON:

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

Появившийся предмет необходимо подобрать с земли. Добавление напрямую в
инвентарь может не обновить статистику.

### Что именно считается

Встроенный перечень содержит ровно 77 записей из `Blueprints.Items` в
`Statistics.cfg` версии игры 2.0.6.

`Blueprint_FaustPsyResist_Quest_1_1` намеренно не входит в этот перечень: это
квестовый чертёж, который может присутствовать в `Analytics`, но не увеличивает
счётчик флешек в КПК.

После обновлений игры, меняющих `Statistics.cfg`, список в
`COUNTED_BLUEPRINTS` необходимо сверить заново.

### Тесты

```powershell
py -m pip install pytest ruff
py -m pytest
py -m ruff check .
```

</details>
