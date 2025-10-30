Цел: Централизирана база данни за управление на жилищни сгради, живущи, разходи, фактури, домофонни обаждания и потребителски роли с разширяеми права.
База: PostgreSQL (JSONB, ENUM, FK, индекси)

## Основна структура
buildings
 ├── units
 │    ├── memberships (users ↔ units)
 │    ├── meters
 │    ├── expense_allocations
 │    └── invoices/payments
 ├── expense_categories
 ├── expenses
 └── announcements

users
 ├── user_profiles
 ├── user_settings
 ├── roles (site-wide)
 ├── memberships (building roles)
 └── intercom_endpoints


### 1. Таблици и отношения
#### buildings

| Поле         | Тип          | Описание                                                   |
| ------------ | ------------ | ---------------------------------------------------------- |
| `id`         | BIGSERIAL PK | Уникален идентификатор                                     |
| `name`       | TEXT         | Име на сградата                                            |
| `address`    | JSONB        | `{street, number, city, postcode}`                         |
| `entrances`  | JSONB        | `["A","B","C"]`                                            |
| `settings`   | JSONB        | Глобални настройки за сграда (пример: quiet_hours, policy) |
| `created_at` | TIMESTAMPTZ  | Автоматично време на създаване                             |

#### units
| Поле              | Тип                 | Описание                       |
| ----------------- | ------------------- | ------------------------------ |
| `id`              | BIGSERIAL PK        | Уникален идентификатор         |
| `building_id`     | FK → `buildings.id` | Принадлежност към сграда       |
| `entrance`        | TEXT                | Вход (A/B/В и др.)             |
| `floor`           | INT                 | Етаж                           |
| `number`          | TEXT                | Номер на апартамента           |
| `area_m2`         | NUMERIC             | Площ                           |
| `shares`          | NUMERIC             | Идеални части                  |
| `occupancy_count` | INT                 | Брой живущи                    |
| `intercom_ext`    | TEXT                | Вътрешен номер (например 1205) |
| `settings`        | JSONB               | Локални настройки              |

### users 

| Поле            | Тип           | Описание                            |
| --------------- | ------------- | ----------------------------------- |
| `id`            | BIGSERIAL PK  | Уникален ID                         |
| `email`         | CITEXT UNIQUE | Имейл (без чувствителност към case) |
| `phone`         | TEXT          | Телефон                             |
| `password_hash` | TEXT          | Хеширана парола                     |
| `is_active`     | BOOLEAN       | Активен акаунт                      |
| `is_superuser`  | BOOLEAN       | Глобален админ                      |
| `settings`      | JSONB         | Настройки (тема, предпочитания)     |
| `created_at`    | TIMESTAMPTZ   | Дата на създаване                   |

### memberships
Връзка между потребител и конкретно жилище

| Поле         | Тип                  | Описание                               |
| ------------ | -------------------- | -------------------------------------- |
| `user_id`    | FK → `users.id`      | Потребител                             |
| `unit_id`    | FK → `units.id`      | Апартамент                             |
| `role`       | ENUM                 | `owner`, `tenant`, `family`, `manager` |
| `is_primary` | BOOLEAN              | Основен обитател                       |
| `since`      | DATE                 | От кога живее                          |
| `until`      | DATE                 | До кога (ако е временно)               |
| PRIMARY KEY  | `(user_id, unit_id)` |                                        |

### intercom_endpoints

| Поле               | Тип             | Описание                                                      |
| ------------------ | --------------- | ------------------------------------------------------------- |
| `id`               | BIGSERIAL PK    | Уникален ID                                                   |
| `unit_id`          | FK → `units.id` | Към кой апартамент е                                          |
| `type`             | TEXT            | `'webrtc'`, `'sip'`, `'phone'`                                |
| `address`          | TEXT            | `sip:user@domain`, `tel:+359...`                              |
| `display_name`     | TEXT            | Псевдоним на таблото                                          |
| `is_public`        | BOOLEAN         | Публичен/скрит                                                |
| `call_permissions` | JSONB           | правила `{allow: ["manager","unit:101"], block: ["unknown"]}` |


### expense_categories
| Поле                | Тип          | Описание                                              |
| ------------------- | ------------ | ----------------------------------------------------- |
| `id`                | BIGSERIAL PK |                                                       |
| `building_id`       | FK           |                                                       |
| `code`              | TEXT UNIQUE  | напр. `cleaning`, `lift`, `repair`                    |
| `name`              | TEXT         | Име на разхода                                        |
| `allocation_method` | TEXT         | `'shares'`, `'per_unit'`, `'per_person'`, `'metered'` |
| `settings`          | JSONB        | Формули, тарифи                                       |

### expenses / expense_allocations

| Таблица               | Полета                                  | Описание                |
| --------------------- | --------------------------------------- | ----------------------- |
| `expenses`            | `period`, `category_id`, `amount_total` | Обща сума за категория  |
| `expense_allocations` | `unit_id`, `amount`, `formula_snapshot` | Разпределение по жилища |

### invoices / payments

| Таблица    | Полета                                                   | Описание              |
| ---------- | -------------------------------------------------------- | --------------------- |
| `invoices` | `unit_id`, `period`, `amount_due`, `due_date`, `status`  | Такси към апартаменти |
| `payments` | `invoice_id`, `amount`, `method`, `paid_at`, `reference` | Плащания              |

### announcements

| Поле                            | Тип   | Описание             |
| ------------------------------- | ----- | -------------------- |
| `building_id`                   | FK    | Към коя сграда       |
| `title`                         | TEXT  | Заглавие             |
| `body`                          | TEXT  | Съдържание           |
| `visible_from`, `visible_until` | DATE  | Период на показване  |
| `audience`                      | JSONB | За кои входове/етажи |

## 2. Роли и права

### A) Глобални роли в системата (Site roles)

| Роля         | Описание                                              | Права                                      |
| ------------ | ----------------------------------------------------- | ------------------------------------------ |
| `superadmin` | Пълен достъп до всички сгради, потребители, настройки | CREATE/DELETE Buildings, Manage Users      |
| `staff`      | Техническа поддръжка (глобално, но ограничено)        | Четене/редакция на сгради, без изтриване   |
| `accountant` | Финансов контрол                                      | Четене/запис на разходи, фактури, плащания |
| `developer`  | Технически API достъп                                 | Създаване на API токени, логове            |
| `resident`   | Обикновен живущ                                       | Достъп само до своето жилище/сграда        |

Глобалните роли се държат в roles + user_roles (много към много).
### B) Локални роли в сграда (Building roles / Membership role)

| Роля         | Описание            | Права в сграда                              |
| ------------ | ------------------- | ------------------------------------------- |
| `manager`    | Домоуправител       | Управлява разходи, покани, достъп до отчети |
| `owner`      | Собственик          | Гласува, вижда всички разходи на сградата   |
| `tenant`     | Наемател            | Вижда само своите такси и сметки            |
| `family`     | Член на семейството | Ограничен достъп, само известия             |
| `accountant` | Назначено лице      | Достъп до плащания, разходи, експорти       |
| `guest`      | Временен достъп     | Само прочит/известия, без действия          |

Тези роли се държат в memberships.role и могат да бъдат ограничавани в policies (JSONB).

## 3. Модел на достъп и разрешения (Access Policy)

A) По йерархия

SuperAdmin
  ├── Building Manager
  │     ├── Accountant
  │     ├── Owner
  │     └── Tenant / Family / Guest

B) Права (Permission Matrix)

| Действие                  | Superadmin | Manager             | Owner | Tenant | Accountant |
| ------------------------- | ---------- | ------------------- | ----- | ------ | ---------- |
| Създаване на сграда       | ✅          | ❌                   | ❌     | ❌      | ❌          |
| Управление на потребители | ✅          | ✅ (само в сградата) | ❌     | ❌      | ❌          |
| Добавяне на разходи       | ✅          | ✅                   | ❌     | ❌      | ✅          |
| Одобрение на плащания     | ✅          | ✅                   | ❌     | ❌      | ✅          |
| Преглед на разходи        | ✅          | ✅                   | ✅     | ✅      | ✅          |
| Промяна на настройки      | ✅          | ✅                   | ❌     | ❌      | ❌          |
| Достъп до домофон         | ✅          | ✅                   | ✅     | ✅      | ✅          |
| Известия и съобщения      | ✅          | ✅                   | ✅     | ✅      | ✅          |
| Изтриване на данни        | ✅          | ❌                   | ❌     | ❌      | ❌          |

## 4. Гъвкавост и разширения

| Категория             | Разширение                                            | Как се добавя                                      |
| --------------------- | ----------------------------------------------------- | -------------------------------------------------- |
| **Права**             | Нови роли (например `technician`, `cleaning_company`) | Добавяне в `roles` таблица и JSON политика         |
| **Обаждания**         | SIP/VoIP интеграция                                   | Добавяне на тип `sip` в `intercom_endpoints`       |
| **Финанси**           | Различни схеми на начисления                          | Нов `allocation_method` + функция за изчисление    |
| **Измервания**        | IoT / автоматични отчети                              | Нови таблици `meters`, `meter_readings`, `tariffs` |
| **История и логове**  | `audit_logs` таблица                                  | Trigger-и за INSERT/UPDATE/DELETE                  |
| **Файлове/документи** | Съхранение на документи                               | `files` таблица с owner, type, url                 |
| **API tokens**        | JWT или OAuth таблица                                 | `api_tokens(user_id, token, scopes)`               |

## 6. Резервно копие и поддръжка

VACUUM – оптимизация след изтривания
pg_stat_statements – следене на бавни заявки
Roles management – чрез GRANT и REVOKE за read/write потребители

## 7. Примерна структура на админ интерфейс

/admin
 ├── Buildings
 │     ├── Units
 │     ├── Members
 │     ├── Expenses
 │     ├── Invoices
 │     └── Meters
 ├── Users
 │     ├── Roles & Permissions
 │     └── Activity Log
 ├── Announcements
 └── Settings

## 8. Разширение за IoT и метрики

meter_readings – за автоматично записване на показания (възможна интеграция с Home Assistant или ESPHome)

alerts – известия при надвишени стойности

webhooks – за интеграция с външни услуги (напр. плащания, известия)

## 9. Примерен Кратък речник на термините

| Термин                | Описание                           |
| --------------------- | ---------------------------------- |
| **Unit**              | Жилищен обект (апартамент, офис)   |
| **Membership**        | Връзка между потребител и жилище   |
| **Building Role**     | Роля на живущия в дадена сграда    |
| **Site Role**         | Глобална роля в системата          |
| **Expense Category**  | Вид разход в сградата              |
| **Allocation**        | Начин на разпределение на разхода  |
| **Invoice**           | Фактура към обитател               |
| **Intercom Endpoint** | Точка за WebRTC/SIP обаждания      |
| **Announcement**      | Известие или съобщение за живущите |

## 10. Обобщение

PostgreSQL → мащабируема, сигурна база с JSONB и ENUM.

Йерархична структура: Site → Building → Unit → User.

Гъвкави роли и права → лесно разширение.

Подготовка за IoT, обаждания, плащания, статистика.

Готово за Flask, FastAPI или GraphQL backend.
