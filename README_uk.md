# BLUETTI Інтеграція для Home Assistant

[🇨🇳 简体中文](./README_zh.md) | [🇩🇪 German](./README_de.md) | [🇬🇧 English](./README.md) | 
[🇳🇱 Dutch](./README_nl.md) | [🇺🇦 Ukrainian](./README_uk.md)

Інтеграція BLUETTI Power Station - це офіційний компонент Home Assistant, який підтримується компанією BLUETTI. Вона дозволяє використовувати розумні станції живлення BLUETTI в Home Assistant.

Репозиторій інтеграції на GitHub:
[https://github.com/bluetti-official/bluetti-home-assistant](https://github.com/bluetti-official/bluetti-home-assistant).

## ✨ Можливості

- ✅ Перемикач живлення
- ✅ Статус інвертора
- ✅ Рівень заряду батареї (SOC)
- ✅ Перемикач AC
- ✅ Перемикач DC
- ✅ Головний вимикач живлення
- ✅ AC ECO
- ✅ DC ECO
- ✅ Перемикач режимів роботи: Backup, Self-consumption, Peak та Off-Peak
- ✅ Режим сну
- ✅ ФВ-вхідна потужність
- ✅ мережева вхідна потужність
- ✅ AC Змінна вихідна потужність
- ✅ DC Змінна вихідна потужність

## 🎮 Список підтримуваних станцій

> [!NOTE]
>
> У майбутньому буде додано більше моделей.

|        Модель станції        |             Назва продукту              | Статус інвертора | SOC батареї | Перемикач AC | Перемикач DC | Головний перемикач | AC ECO  | DC ECO  |   Режим роботи    |     Режим сну     | ФВ-вхідна потужність | мережева вхідна потужність | AC Змінна вихідна потужність | DC Змінна вихідна потужність |
|:----------------------------:|:---------------------------------------:|:----------------:|:-----------:|:------------:|:------------:|:------------------:|:-------:|:-------:|:-----------------:|:-----------------:|:--------------------:|:--------------------------:|:----------------------------:|:----------------------------:| 
|            AP300             |                Apex 300                 |                  |      ✅      |      ✅       |              |                    |    ✅    |         |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|            EL300             |           Elite 300,AORA 300            |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|        EL320,AORA320         |           Elite 320,AORA 320            |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|            EL400             |                Elite 400                |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|            EP13K             |                  EP13k                  |        ✅         |      ✅      |              |              |         ✅          |         |         |         ✅         |                   |                      |                            |                              |                              |
|            EP2000            |                  EP200                  |        ✅         |      ✅      |              |              |         ✅          |         |         |         ✅         |                   |                      |                            |                              |                              |
|             EP6K             |                  EP6k                   |        ✅         |      ✅      |              |              |         ✅          |         |         |         ✅         |                   |                      |                            |                              |                              |
|            EP760             |                  EP760                  |        ✅         |      ✅      |              |              |         ✅          |         |         |                   |                   |                      |                            |                              |                              |
|           EP500Pro           |                EP500Pro                 |                  |      ✅      |      ✅       |      ✅       |                    |         |         |         ✅         |                   |          ✅           |             ✅              |              ✅               |              ✅               |
|              FP              |             Fridge Product              |        ✅         |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |                      |                            |                              |                              |
|  PR100V2,EL100V2,AORA100V2   | Premium 100 V2,Elite 100 V2,AORA 100 V2 |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
| PR200V2,Elite 200 V2,AORA200 | Premium 200 V2,Elite 200 V2,AORA 200 V2 |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|        PR30V2,EL30V2         |  Premium 30 V2,Elite 30 V2,AORA 30 V2   |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|             RV5              |                   RV5                   |        ✅         |      ✅      |      ✅       |      ✅       |                    |         |         |         ✅         |         ✅         |          ✅           |             ✅              |              ✅               |              ✅               |
|      Balco260,Balco500       |            Balco260,Balco500            |        ✅         |      ✅      |      ✅       |              |                    |         |         |         ✅         |                   |          ✅           |             ✅              |              ✅               |                              |
|         AC300,AC500          |               AC300,AC500               |                  |      ✅      |      ✅       |      ✅       |                    |         |         |         ✅         |                   |          ✅           |             ✅              |              ✅               |              ✅               |
|        AC200PL,AC200L        |             AC200PL,AC200L              |                  |      ✅      |      ✅       |      ✅       |                    |    ✅    |    ✅    |         ✅         |                   |          ✅           |             ✅              |              ✅               |              ✅               |

## 📦 Встановлення інтеграції

Є два способи встановити `BLUETTI Power Station Integration`.

### Ручне встановлення

1. Перейдіть до каталогу конфігурації `Home Assistant`

   ```bash
   cd /<ha workspaces>/core/config/custom_components
   ```

2. Клонуйте `BLUETTI Power Station Integration` GitHub репозиторій.

   ```bash
   git clone https://github.com/bluetti-official/bluetti-home-assistant.git
   ```

3. Або завантажте інтегрований zip-файл і розпакуйте його в каталог
користувацької інтеграції `Home Assistant`:

   ```bash
   unzip xxx.zip -d /<ha workspaces>/core/config/custom_components/bluetti
   ```

4. Перезавантажте систему `Home Assistant`.

### Установка за допомогою HACS

Оскільки `BLUETTI Power Station Integration` ще не було додано до
офіційного репозиторію HACS, необхідно вручну додати власний репозиторій.
HACS — це плагін Home Assistant (користувачам спочатку потрібно встановити HACS),
подібний до магазину додатків. За допомогою цього магазину додатків можна
встановити інші інтеграції сторонніх розробників.

1. Виконайте кроки "HACS -> Інтеграція -> Власний репозиторій (знаходиться у
   верхньому правому куті сторінки)".

2. Додайте репозиторій і оберіть тип:
   - **Repository**:
     [https://github.com/bluetti-official/bluetti-home-assistant.git](https://github.com/bluetti-official/bluetti-home-assistant.git)
   - **Type:** Інтеграція

3. Потім на сторінці "Integration" HACS ви побачите інтеграцію «BLUETTI».
Натисніть, щоб встановити.

4. Нарешті, перезавантажте вашу `Home Assistant` систему.

## ⚙️ Налаштування інтеграції

1. Виконайте кроки "Налаштування -> Пристрої та сервіси", натисніть, щоб перейти на сторінку `Integration List`.

   <img src="./doc/images/1-setting_devices_and_services.png" width="880">

2. Натисніть кнопку "Додати інтеграцію", тоді зробіть пошук по назві бренду
   `bluetti`; оберіть інтеграцію `BLUETTI` та виконайте авторизацію (OAUTH) на сторінці входу.

   <img src="./doc/images/2-search_and_add_integration.png" width="880">

3. Ви повинні погодитися, що `Home Assistant` буде мати доступ до вашого BLUETTI облікового запису та встановить з'єднання з хмарним сервісом BLUETTI.

   <img src="./doc/images/3-oauth_agree_to_connect_with_bluetti.png">

4. Увійдіть у свій обліковий запис BLUETTI, щоб авторизуватися та увійти 

   <img src="./doc/images/4-oauth_enter_bluetti_account.png">

5. Ви повинні погодитися, що `Home Assistant` буде пов'язаний з вашим обліковим записом BLUETTI.

   <img src="./doc/images/5-oauth_link_account_to_ha.png">

6. Виберіть пристрої станції живлення BLUETTI, які потрібно використовувати та керувати в Home Assistant.

   <img src="./doc/images/6-choose_bluetti_devices.png" width="880">
   <img src="./doc/images/7-bluetti_device_in_ha.png" width="880">

## ❓ Часті питання (FAQ)

### Не може знайти `BLUETTI Integration` після встановлення?

Будь ласка перевірте чи правильний шлях `custom_components` та що `Home Assistant` було перезавантажено.

### Пристрій завжди офлайн або немає з’єднання з серверами BLUETTI?

Будь ласка перевірте **network**, **ports** та **firewall** та переконайтеся, що `Home Assistant` має доступ до вашого пристрою станції живлення.

### Як оновити `BLUETTI Integration`?

1. Перейдіть на сторінку керування HACS для виконання оновлення.
2. Оновлення за допомогою `git`

   ```bash
   cd /<ha workspaces>/config/custom_components/bluetti
   git pull
   ```

## Повідомлення

### Для режиму власного споживання Balco260 потрібно підключити лічильник електроенергії


## 📮 Підтримка та Відгуки

💬 Є проблеми або пропозиції? Створіть запит на GitHub:
[https://github.com/bluetti-official/bluetti-home-assistant/issues](https://github.com/bluetti-official/bluetti-home-assistant/issues)
