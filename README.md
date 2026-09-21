# Пошук будинку в Тернополі

Щоденний звіт про приватні будинки та земельні ділянки в Тернополі й вибраному передмісті.

- [Актуальний звіт на GitHub Pages](https://andriy232.github.io/ternopil_house/)
- Локальний звіт: `latest_report/index.html`
- Архіви запусків: `%TEMP%\house_search\<час_пошуку>`

Windows Task Scheduler запускає `run-daily.ps1` щодня о 09:00 за київським часом. Після успішного повного запуску сценарій публікує `latest_report`, створює Git-коміт за наявності змін і виконує push у `main`. GitHub Actions розгортає вміст `latest_report` на GitHub Pages.
