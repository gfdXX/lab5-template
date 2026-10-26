# РСОИ, ЛР5 и курсовая: система бронирования автомобилей с OAuth2

![Python](https://img.shields.io/badge/Python-FastAPI-009688?logo=fastapi&logoColor=white)
![OpenID Connect](https://img.shields.io/badge/OAuth2-OpenID_Connect_%2B_JWT-F78C40?logo=openid&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-events-231F20?logo=apachekafka&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-Helm-326CE5?logo=kubernetes&logoColor=white)

Лабораторная работа №5 и курсовая работа «Система бронирования автомобилей» по курсу «Распределённые системы обработки информации», МГТУ им. Н.Э. Баумана (2025–2026).

> **Код решения — в ветке [`test`](https://github.com/gfdXX/lab5-template/tree/test).**
> В `master` лежит исходный шаблон курса, условие ЛР5 — в [ASSIGNMENT.md](ASSIGNMENT.md).
> Пояснительная записка к курсовой — [`report/pdf/report.pdf`](https://github.com/gfdXX/lab5-template/blob/test/report/pdf/report.pdf).

## Что сделано

Сервис аренды автомобилей из ЛР2–ЛР4 доведён до полноценной системы:

| Сервис | Порт | Ответственность |
|---|---|---|
| Identity Provider | 8090 | собственный провайдер OpenID Connect: `/.well-known/openid-configuration`, JWKS, выдача токенов, регистрация и управление пользователями |
| Gateway | 8080 | единая точка входа, проверка JWT, оркестрация запросов, отдача статистики |
| Cars / Rental / Payment | 8070 / 8060 / 8050 | автомобили, аренды, оплаты |
| Statistics | 8040 | принимает события из Kafka и строит сводку |
| UI | 3000 | веб-интерфейс: поиск и бронирование машин, мои аренды, панель администратора со статистикой и пользователями |

- **Авторизация OAuth2**: Resource Owner Password flow (`/api/v1/authorize`) и Authorization Code с входом через страницу провайдера (`/api/v1/callback`), токены — JWT, сервисы валидируют их локально по JWKS, без запроса к провайдеру; токен пробрасывается между сервисами, все `/api/**` закрыты, кроме `authorize` и `callback`;
- **роли**: пользователь и администратор, администратор создаётся при старте Identity Provider;
- **события**: Gateway публикует события (регистрация пользователя, создание пользователя администратором, создание, завершение и отмена аренды) в топик Kafka `car-rental-events`, Statistics их агрегирует;
- **деплой**: docker-compose локально, Helm-чарты для Kubernetes (как в [ЛР4](https://github.com/gfdXX/lab4-template)).

## Запуск

```bash
git clone -b test https://github.com/gfdXX/lab5-template.git
cd lab5-template
docker compose up --build        # UI на http://localhost:3000, Gateway на http://localhost:8080
```

## Автор

Салженикин Даниил, группа ИУ7-21М, МГТУ им. Н.Э. Баумана. Руководитель курсовой — Ступников А.А.
