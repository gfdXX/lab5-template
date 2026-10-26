# РСОИ, ЛР5 и курсовая: система бронирования автомобилей с OAuth2

![Python](https://img.shields.io/badge/Python-FastAPI-009688?logo=fastapi&logoColor=white)
![OpenID Connect](https://img.shields.io/badge/OAuth2-OpenID_Connect_%2B_JWT-F78C40?logo=openid&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-events-231F20?logo=apachekafka&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Helm-326CE5?logo=kubernetes&logoColor=white)

Лабораторная работа №5 и курсовая работа «Система бронирования автомобилей» по курсу «Распределённые системы обработки информации», МГТУ им. Н.Э. Баумана (2025–2026).

- Условие ЛР5 — в [ASSIGNMENT.md](ASSIGNMENT.md).
- Пояснительная записка к курсовой — [report/pdf/report.pdf](report/pdf/report.pdf).

## Что сделано

Сервис аренды автомобилей из ЛР2–ЛР4 доведён до полноценной системы ([`services/`](services)):

| Сервис | Порт | Ответственность |
|---|---|---|
| Identity Provider | 8090 | собственный провайдер OpenID Connect: `/.well-known/openid-configuration`, JWKS, выдача токенов, регистрация и управление пользователями |
| Gateway | 8080 | единая точка входа, проверка JWT, оркестрация запросов, отдача статистики |
| Cars / Rental / Payment | 8070 / 8060 / 8050 | автомобили, аренды, оплаты |
| Statistics | 8040 | принимает события из Kafka и строит сводку |
| UI | 3000 | веб-интерфейс (SPA на React): поиск и бронирование машин, мои аренды, панель администратора со статистикой и пользователями |

- **Авторизация OAuth2**: Resource Owner Password flow (`/api/v1/authorize`) и Authorization Code с входом через страницу провайдера (`/api/v1/callback`), токены — JWT, сервисы валидируют их локально по JWKS, без запроса к провайдеру; токен пробрасывается между сервисами, все `/api/**` закрыты, кроме `authorize` и `callback`;
- **роли**: `User` и `Admin`, администратор создаётся при старте Identity Provider (логин и пароль задаются `ADMIN_USERNAME` / `ADMIN_PASSWORD`);
- **события**: Gateway публикует события (регистрация пользователя, создание пользователя администратором, создание, завершение и отмена аренды) в топик Kafka `car-rental-events`, Statistics их агрегирует;
- **деплой**: docker-compose локально, Helm-чарты для Kubernetes (как в [ЛР4](https://github.com/gfdXX/lab4-template)).

## Запуск

```bash
git clone https://github.com/gfdXX/lab5-template.git
cd lab5-template
docker compose up --build
```

| Что | Адрес |
|---|---|
| UI | http://localhost:3000 |
| Gateway API | http://localhost:8080 |
| Identity Provider | http://localhost:8090 |
| Statistics API | http://localhost:8040 |

Получить токен и вызвать API:

```bash
curl -X POST http://localhost:8080/api/v1/authorize \
  -d "username=<u>&password=<p>&client_id=$OIDC_CLIENT_ID&client_secret=$OIDC_CLIENT_SECRET"
curl -H "Authorization: Bearer <token>" "http://localhost:8080/api/v1/cars?page=1&size=10"
```

## Настройка OAuth2 / OIDC

Сервисы принимают только запросы с заголовком `Authorization: Bearer <jwt>`: подпись и срок действия проверяются по JWKS, имя пользователя берётся из claim `preferred_username` / `email` / `name` / `sub`.

| Переменная | Назначение |
|---|---|
| `OIDC_ISSUER`, `OIDC_AUDIENCE` | ожидаемые `iss` и `aud` в токене (`aud` по умолчанию = `OIDC_CLIENT_ID`) |
| `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | учётные данные клиента в Identity Provider |
| `OIDC_TOKEN_URL` | endpoint токенов для `/api/v1/authorize` и `/api/v1/callback` |
| `OIDC_WELL_KNOWN_URL` | опционально: загрузить metadata и JWKS при старте |
| `OIDC_JWKS` / `OIDC_JWKS_URL` | статичный набор ключей или ссылка на JWKS |
| `OIDC_SCOPE` | запрашиваемые scope, по умолчанию `openid profile email` |
| `OIDC_REDIRECT_URI` | redirect_uri для Authorization Code flow |

Endpoints провайдера: `GET /oauth/authorize` (форма входа), `POST /oauth/token`, `GET /.well-known/openid-configuration`, `GET /oauth/jwks`.
Только для `Admin`: `GET/POST /api/v1/users`, `GET /api/v1/statistics/summary`, `GET /api/v1/statistics/events`.

## Kubernetes

Используются те же универсальные Helm-чарты, что и в ЛР4; отличия сервисов — в [`helm/values`](helm/values) (включая `identity-service`, `statistics-service`, `ui-service`, `kafka`). Правила Ingress:

| Путь | Сервис |
|---|---|
| `/` | UI |
| `/api`, `/manage` | Gateway |
| `/oauth`, `/.well-known` | Identity Provider |

Если в кластере нет Ingress Controller:

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace \
  --set controller.service.type=LoadBalancer --wait --timeout 5m
kubectl get svc -n ingress-nginx ingress-nginx-controller   # внешний IP
```

После выдачи внешнего IP сайт доступен по `http://<EXTERNAL-IP>/`. Если адрес есть, но сайт не открывается, проверьте доступность TCP 80/443 в группе безопасности Yandex Cloud.

## Автор

Салженикин Даниил, группа ИУ7-21М, МГТУ им. Н.Э. Баумана. Руководитель курсовой — Ступников А.А.
