import os
import time
from string import Template

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


API_BASE_URL = os.getenv("UI_API_BASE_URL", "http://localhost:8080")
IDENTITY_URL = os.getenv("UI_IDENTITY_URL", "http://localhost:8090")
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "car-rental-ui")
REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:3000/callback")

app = FastAPI(title="Car Rental UI", version="1.0.0")


@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)
    print(f"ui-service {request.method} {request.url.path} -> {response.status_code} ({elapsed_ms} ms)")
    return response


PAGE = Template(
    """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Аренда автомобилей</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #1b2430;
      background: #eef2f7;
      --ink: #1b2430;
      --muted: #617086;
      --line: #d9e0ea;
      --surface: #ffffff;
      --soft: #f7f9fc;
      --blue: #245dd8;
      --blue-dark: #0f2c6e;
      --green: #1f8a5b;
      --red: #b42332;
      --amber: #a16207;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-width: 320px; background: #eef2f7; }
    button, input, select { font: inherit; }
    button { cursor: pointer; }
    .shell { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    .topbar {
      background: #152033;
      color: #fff;
      border-bottom: 1px solid rgba(255,255,255,.1);
    }
    .topbar-inner {
      width: min(1240px, 100%);
      margin: 0 auto;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
    }
    .brand { display: flex; align-items: center; gap: 12px; min-width: 0; }
    .brand-mark {
      width: 38px;
      height: 38px;
      border-radius: 8px;
      background: #f2b705;
      color: #172033;
      display: grid;
      place-items: center;
      font-weight: 900;
      letter-spacing: 0;
    }
    .brand h1 { margin: 0; font-size: 20px; line-height: 1.1; letter-spacing: 0; }
    .brand p { margin: 3px 0 0; color: #b9c6d8; font-size: 13px; }
    .account { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-end; }
    .user-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 36px;
      padding: 7px 10px;
      border: 1px solid rgba(255,255,255,.16);
      border-radius: 8px;
      background: rgba(255,255,255,.08);
      color: #f8fbff;
      max-width: 300px;
      overflow-wrap: anywhere;
    }
    main {
      width: min(1240px, 100%);
      margin: 0 auto;
      padding: 28px 24px 42px;
    }
    .intro {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: end;
      gap: 18px;
      margin-bottom: 22px;
    }
    .intro h2 { margin: 0; font-size: clamp(24px, 3vw, 38px); line-height: 1.05; letter-spacing: 0; }
    .intro p { margin: 8px 0 0; color: var(--muted); max-width: 700px; }
    .btn {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 8px;
      min-height: 40px;
      padding: 9px 13px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      font-weight: 700;
      transition: background .15s ease, border-color .15s ease, transform .15s ease;
    }
    .btn:hover { transform: translateY(-1px); border-color: #aebbd0; }
    .btn.primary { background: var(--blue); border-color: var(--blue); color: #fff; }
    .btn.primary:hover { background: #1f52bf; }
    .btn.danger { border-color: #f0b8be; color: var(--red); background: #fff7f8; }
    .btn.ghost { background: rgba(255,255,255,.08); color: #fff; border-color: rgba(255,255,255,.18); }
    .btn:disabled { opacity: .55; cursor: not-allowed; transform: none; }
    .nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }
    .tabs {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 5px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
    }
    .tab {
      border: 0;
      background: transparent;
      color: var(--muted);
      border-radius: 8px;
      min-height: 36px;
      padding: 7px 12px;
      font-weight: 800;
    }
    .tab.active { color: #fff; background: var(--blue-dark); }
    .filters {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      margin-bottom: 18px;
    }
    .field, .select, .date-field {
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      padding: 9px 12px;
    }
    .field { min-width: min(330px, 100%); }
    .date-field { width: 155px; }
    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--muted);
      min-height: 42px;
    }
    .notice, .error {
      border-radius: 8px;
      padding: 12px 14px;
      margin-bottom: 16px;
      border: 1px solid;
      line-height: 1.45;
    }
    .notice { color: #11406f; background: #e9f3ff; border-color: #c8def8; }
    .error { color: #8f1f2e; background: #fff1f2; border-color: #fecdd3; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 14px; }
    .card {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      box-shadow: 0 14px 36px rgba(21, 32, 51, .07);
    }
    .car-card { display: grid; gap: 14px; min-height: 224px; }
    .card-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
    .card h3 { margin: 0; font-size: 19px; line-height: 1.2; letter-spacing: 0; }
    .muted { color: var(--muted); }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 5px 9px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: var(--soft);
      color: #344258;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }
    .pill.good { color: #0f6b45; background: #eaf8f0; border-color: #bee8d0; }
    .pill.warn { color: var(--amber); background: #fff8e6; border-color: #fde68a; }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .price { font-size: 22px; font-weight: 900; color: #162033; }
    .empty {
      border: 1px dashed #b7c3d5;
      border-radius: 8px;
      background: rgba(255,255,255,.72);
      padding: 28px;
      color: var(--muted);
      text-align: center;
    }
    .panel {
      display: grid;
      gap: 18px;
    }
    .section-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 4px 0 12px;
    }
    .section-title h3 { margin: 0; font-size: 20px; }
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }
    .metric {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 15px;
    }
    .metric span { display: block; color: var(--muted); font-size: 13px; font-weight: 700; }
    .metric strong { display: block; margin-top: 8px; font-size: 28px; }
    .form {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .form label { display: grid; gap: 6px; color: var(--muted); font-size: 13px; font-weight: 800; }
    .form input { width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; min-height: 42px; }
    .form .wide { grid-column: 1 / -1; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
    }
    table { width: 100%; border-collapse: collapse; min-width: 1040px; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e7edf5; vertical-align: top; }
    td { overflow-wrap: anywhere; }
    th { background: #f7f9fc; color: #43516a; font-size: 13px; }
    tr:last-child td { border-bottom: 0; }
    .login-page { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    .login-main {
      display: grid;
      align-items: center;
      grid-template-columns: minmax(0, 1.1fr) minmax(280px, .9fr);
      gap: 32px;
      width: min(1120px, 100%);
      margin: 0 auto;
      padding: 44px 24px;
    }
    .login-copy h2 { margin: 0; font-size: clamp(34px, 5vw, 58px); line-height: 1; letter-spacing: 0; color: #172033; }
    .login-copy p { color: var(--muted); font-size: 18px; max-width: 620px; line-height: 1.55; }
    .login-box {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 18px 46px rgba(21, 32, 51, .08);
    }
    .login-box h3 { margin: 0 0 8px; font-size: 22px; }
    .login-box p { margin: 0 0 18px; color: var(--muted); line-height: 1.5; }
    .actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
    .auth-toggle {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 5px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      margin-bottom: 16px;
    }
    .auth-toggle button {
      border: 0;
      background: transparent;
      border-radius: 6px;
      min-height: 36px;
      color: var(--muted);
      font-weight: 800;
    }
    .auth-toggle button.active { background: #fff; color: var(--blue-dark); box-shadow: 0 6px 18px rgba(21, 32, 51, .08); }
    .auth-form { grid-template-columns: 1fr; margin-bottom: 14px; padding: 0; border: 0; background: transparent; }
    .ticket {
      margin-top: 12px;
      padding: 12px;
      border: 1px solid #d9e0ea;
      border-radius: 8px;
      background: #f7f9fc;
      color: #344258;
      line-height: 1.45;
    }
    .mini { font-size: 13px; color: var(--muted); }
    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 20;
      display: grid;
      place-items: center;
      padding: 18px;
      background: rgba(15, 23, 42, .54);
    }
    .modal {
      width: min(460px, 100%);
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 24px 70px rgba(15, 23, 42, .28);
      padding: 22px;
    }
    .modal h3 { margin: 0 0 14px; text-align: center; font-size: 22px; }
    .modal-summary {
      display: grid;
      gap: 10px;
      padding: 14px;
      border: 1px solid #d9e0ea;
      border-radius: 8px;
      background: #f7f9fc;
      margin-bottom: 14px;
    }
    .modal-row { display: flex; justify-content: space-between; gap: 12px; color: var(--muted); }
    .modal-row strong { color: var(--ink); text-align: right; }
    .modal-total {
      border-radius: 8px;
      background: #e9f3ff;
      color: #123c6b;
      padding: 12px 14px;
      font-weight: 800;
      margin-bottom: 16px;
    }
    .modal-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 760px) {
      .topbar-inner { padding: 14px 16px; align-items: flex-start; }
      .intro { grid-template-columns: 1fr; align-items: start; }
      main { padding: 22px 16px 32px; }
      .login-main { grid-template-columns: 1fr; padding: 28px 16px; }
      .form { grid-template-columns: 1fr; }
      .account { justify-content: flex-start; }
      .modal-actions { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <script>
    const CONFIG = {
      apiBase: "$API_BASE_URL",
      identityUrl: "$IDENTITY_URL",
      clientId: "$CLIENT_ID",
      redirectUri: "$REDIRECT_URI"
    };
    if (location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
      CONFIG.apiBase = location.origin;
      CONFIG.identityUrl = location.origin;
      CONFIG.redirectUri = location.origin + "/callback";
    }

    const h = React.createElement;
    const tokenStore = {
      get: function () { return localStorage.getItem("access_token"); },
      set: function (token) { localStorage.setItem("access_token", token); },
      clear: function () { localStorage.removeItem("access_token"); }
    };

    function decodeToken(token) {
      try {
        let part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        part = part.padEnd(Math.ceil(part.length / 4) * 4, "=");
        return JSON.parse(atob(part));
      } catch (err) {
        return {};
      }
    }

    function isoDate(offsetDays) {
      const date = new Date(Date.now() + offsetDays * 86400000);
      return date.toISOString().slice(0, 10);
    }

    function money(value) {
      return new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 }).format(value || 0);
    }

    function rentalDays(from, to) {
      const start = new Date(from + "T00:00:00");
      const end = new Date(to + "T00:00:00");
      const days = Math.round((end - start) / 86400000);
      return Number.isFinite(days) && days > 0 ? days : 0;
    }

    function statusClass(status) {
      return status === "IN_PROGRESS" ? "pill good" : "pill warn";
    }

    function statusText(status) {
      const labels = {
        IN_PROGRESS: "Активна",
        FINISHED: "Завершена",
        CANCELED: "Отменена",
        PAID: "Оплачено",
        CANCELED_PAYMENT: "Отменено"
      };
      return labels[status] || status || "Неизвестно";
    }

    function carIsAvailable(car) {
      return car.available !== undefined ? Boolean(car.available) : Boolean(car.availability);
    }

    function App() {
      const [token, setToken] = React.useState(tokenStore.get());
      const [tab, setTab] = React.useState("cars");
      const [cars, setCars] = React.useState([]);
      const [rentals, setRentals] = React.useState([]);
      const [stats, setStats] = React.useState(null);
      const [events, setEvents] = React.useState([]);
      const [users, setUsers] = React.useState([]);
      const [query, setQuery] = React.useState("");
      const [showAll, setShowAll] = React.useState(false);
      const [dateFrom, setDateFrom] = React.useState(isoDate(0));
      const [dateTo, setDateTo] = React.useState(isoDate(3));
      const [message, setMessage] = React.useState("");
      const [error, setError] = React.useState("");
      const [busy, setBusy] = React.useState(false);
      const [authMode, setAuthMode] = React.useState("signin");
      const [bookingCar, setBookingCar] = React.useState(null);

      const claims = token ? decodeToken(token) : {};
      const roles = (claims.roles || []).map(function (role) { return String(role).toLowerCase(); });
      const isAdmin = roles.includes("admin");
      const username = claims.preferred_username || claims.sub || "user";

      async function api(path, options) {
        const opts = options || {};
        const headers = Object.assign({}, opts.headers || {});
        if (token) headers.Authorization = "Bearer " + token;
        if (opts.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
        const res = await fetch(CONFIG.apiBase + path, Object.assign({}, opts, { headers: headers }));
        if (res.status === 204) return null;
        const text = await res.text();
        let data = null;
        try { data = text ? JSON.parse(text) : null; } catch (err) { data = text; }
        if (!res.ok) {
          const detail = data && data.detail ? data.detail : (text || "Request failed");
          throw new Error(detail);
        }
        return data;
      }

      async function loadCars(nextShowAll) {
        const flag = typeof nextShowAll === "boolean" ? nextShowAll : showAll;
        const data = await api("/api/v1/cars?page=1&size=40&showAll=" + String(flag));
        setCars(data.items || []);
      }

      async function loadRentals() {
        const data = await api("/api/v1/rental");
        setRentals(Array.isArray(data) ? data : (data.items || []));
      }

      async function loadAdmin() {
        setError("");
        const results = await Promise.allSettled([
          api("/api/v1/statistics/summary"),
          api("/api/v1/statistics/events"),
          api("/api/v1/users")
        ]);
        if (results[0].status === "fulfilled") setStats(results[0].value);
        if (results[1].status === "fulfilled") setEvents(results[1].value || []);
        if (results[2].status === "fulfilled") setUsers(results[2].value || []);
        const failures = results.filter(function (item) { return item.status === "rejected"; });
        if (failures.length) setError(failures.map(function (item) { return item.reason.message; }).join("; "));
      }

      React.useEffect(function () {
        const params = new URLSearchParams(location.search);
        const code = params.get("code");
        if (location.pathname === "/callback" && code) {
          setBusy(true);
          fetch(CONFIG.apiBase + "/api/v1/callback?code=" + encodeURIComponent(code) + "&redirect_uri=" + encodeURIComponent(CONFIG.redirectUri))
            .then(function (res) {
              return res.text().then(function (text) {
                let data = text ? JSON.parse(text) : {};
                if (!res.ok) throw new Error(data.detail || text || "Could not finish sign in");
                return data;
              });
            })
            .then(function (data) {
              tokenStore.set(data.access_token);
              setToken(data.access_token);
              history.replaceState(null, "", "/");
            })
            .catch(function (err) { setError(err.message); })
            .finally(function () { setBusy(false); });
        }
      }, []);

      React.useEffect(function () {
        if (!token) return;
        setError("");
        Promise.allSettled([loadCars(), loadRentals()]).then(function (results) {
          const failed = results.find(function (item) { return item.status === "rejected"; });
          if (failed) setError(failed.reason.message);
        });
      }, [token]);

      function login() {
        const params = new URLSearchParams({
          response_type: "code",
          client_id: CONFIG.clientId,
          redirect_uri: CONFIG.redirectUri,
          scope: "openid profile email",
          state: String(Date.now())
        });
        location.href = CONFIG.identityUrl + "/oauth/authorize?" + params.toString();
      }

      async function register(ev) {
        ev.preventDefault();
        const formEl = ev.currentTarget;
        setBusy(true);
        setError("");
        setMessage("");
        const form = new FormData(formEl);
        const payload = Object.fromEntries(form.entries());
        try {
          await fetch(CONFIG.apiBase + "/api/v1/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          }).then(function (res) {
            return res.text().then(function (text) {
              const data = text ? JSON.parse(text) : {};
              if (!res.ok) throw new Error(data.detail || text || "Не удалось создать аккаунт");
              return data;
            });
          });
          formEl.reset();
          setAuthMode("signin");
          setMessage("Аккаунт создан. Теперь войдите через провайдер идентификации с указанными логином и паролем.");
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      }

      function openBooking(car) {
        setError("");
        setMessage("");
        const days = rentalDays(dateFrom, dateTo);
        if (!days) {
          setError("Выберите корректный период аренды.");
          return;
        }
        if (!carIsAvailable(car)) {
          setError("Этот автомобиль сейчас занят. Выберите доступный автомобиль.");
          return;
        }
        setBookingCar(car);
      }

      function closeBooking() {
        if (!busy) setBookingCar(null);
      }

      async function rent(car) {
        setBusy(true);
        setError("");
        setMessage("");
        try {
          const days = rentalDays(dateFrom, dateTo);
          if (!days) throw new Error("Выберите корректный период аренды.");
          if (!carIsAvailable(car)) throw new Error("Этот автомобиль сейчас занят. Выберите доступный автомобиль.");
          const booking = await api("/api/v1/rental", {
            method: "POST",
            body: JSON.stringify({ carUid: car.carUid, dateFrom: dateFrom, dateTo: dateTo })
          });
          const payment = booking.payment || {};
          setMessage("Бронирование оплачено: " + car.brand + " " + car.model + ", " + money(payment.price || car.price * days) + ". Статус платежа: " + statusText(payment.status || "PAID") + ".");
          setBookingCar(null);
          await loadCars();
          await loadRentals();
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      }

      async function finishRental(rental) {
        setBusy(true);
        setError("");
        try {
          await api("/api/v1/rental/" + rental.rentalUid + "/finish", { method: "POST" });
          setMessage("Аренда завершена.");
          await loadRentals();
          await loadCars();
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      }

      async function cancelRental(rental) {
        setBusy(true);
        setError("");
        try {
          await api("/api/v1/rental/" + rental.rentalUid, { method: "DELETE" });
          setMessage("Аренда отменена.");
          await loadRentals();
          await loadCars();
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      }

      async function addUser(ev) {
        ev.preventDefault();
        const formEl = ev.currentTarget;
        setBusy(true);
        setError("");
        setMessage("");
        const form = new FormData(formEl);
        const payload = Object.fromEntries(form.entries());
        try {
          await api("/api/v1/users", { method: "POST", body: JSON.stringify(payload) });
          formEl.reset();
          setMessage("Пользователь " + payload.username + " создан. Теперь он может войти через провайдер идентификации.");
          await loadAdmin();
        } catch (err) {
          setError(err.message);
        } finally {
          setBusy(false);
        }
      }

      async function switchTab(name) {
        setTab(name);
        setMessage("");
        setError("");
        if (name === "cars") await loadCars().catch(function (err) { setError(err.message); });
        if (name === "rentals") await loadRentals().catch(function (err) { setError(err.message); });
        if (name === "admin") await loadAdmin();
      }

      const filteredCars = cars.filter(function (car) {
        const needle = query.trim().toLowerCase();
        if (!needle) return true;
        return [car.brand, car.model, car.registrationNumber, car.type].join(" ").toLowerCase().includes(needle);
      });

      if (!token) {
        return h("div", { className: "login-page" },
          h("header", { className: "topbar" },
            h("div", { className: "topbar-inner" },
              h("div", { className: "brand" },
                h("div", { className: "brand-mark" }, "CR"),
                h("div", null, h("h1", null, "Аренда автомобилей"), h("p", null, "Курсовой проект с OpenID Connect"))
              ),
              h("button", { className: "btn ghost", onClick: login, disabled: busy }, busy ? "Входим..." : "Войти")
            )
          ),
          h("main", { className: "login-main" },
            h("section", { className: "login-copy" },
              h("h2", null, "Бронируйте автомобили, управляйте арендой и смотрите статистику.")
            ),
            h("section", { className: "login-box" },
              h("div", { className: "auth-toggle" },
                h("button", { className: authMode === "signin" ? "active" : "", onClick: function () { setAuthMode("signin"); setError(""); setMessage(""); } }, "Вход"),
                h("button", { className: authMode === "register" ? "active" : "", onClick: function () { setAuthMode("register"); setError(""); setMessage(""); } }, "Регистрация")
              ),
              h("h3", null, authMode === "signin" ? "Безопасный вход" : "Создать аккаунт"),
              authMode === "register" && h("p", null, "Новые аккаунты создаются с ролью Пользователь и могут сразу войти в систему."),
              error && h("div", { className: "error" }, error),
              message && h("div", { className: "notice" }, message),
              authMode === "signin" && h("button", { className: "btn primary", onClick: login, disabled: busy }, busy ? "Подождите..." : "Войти через провайдер"),
              authMode === "register" && h("form", { className: "form auth-form", onSubmit: register },
                h("label", null, "Логин", h("input", { name: "username", placeholder: "new.user", required: true })),
                h("label", null, "Email", h("input", { name: "email", type: "email", placeholder: "user@example.com", required: true })),
                h("label", null, "Имя", h("input", { name: "fullName", placeholder: "Иван Иванов" })),
                h("label", null, "Пароль", h("input", { name: "password", type: "password", placeholder: "Минимум 6 символов", required: true, minLength: 6 })),
                h("button", { className: "btn primary", disabled: busy }, busy ? "Создаем..." : "Создать аккаунт")
              )
            )
          )
        );
      }

      return h("div", { className: "shell" },
        h("header", { className: "topbar" },
          h("div", { className: "topbar-inner" },
            h("div", { className: "brand" },
              h("div", { className: "brand-mark" }, "CR"),
              h("div", null, h("h1", null, "Аренда автомобилей"), h("p", null, "Автомобили, бронирования и отчеты"))
            ),
            h("div", { className: "account" },
              h("span", { className: "user-chip" }, username, isAdmin ? h("span", { className: "pill good" }, "Админ") : h("span", { className: "pill" }, "Пользователь")),
              h("button", { className: "btn ghost", onClick: function () { tokenStore.clear(); setToken(null); setCars([]); setRentals([]); } }, "Выйти")
            )
          )
        ),
        h("main", null,
          h("div", { className: "intro" },
            h("div", null,
              h("h2", null, tab === "admin" ? "Администрирование" : (tab === "rentals" ? "Мои бронирования" : "Доступные автомобили")),
              h("p", null, tab === "admin" ? "Создавайте пользователей и смотрите отчет по событиям Kafka." : "Выберите даты, забронируйте автомобиль и отслеживайте аренды в одном месте.")
            ),
            h("div", { className: "actions" },
              h("input", { className: "date-field", type: "date", value: dateFrom, onChange: function (ev) { setDateFrom(ev.target.value); } }),
              h("input", { className: "date-field", type: "date", value: dateTo, onChange: function (ev) { setDateTo(ev.target.value); } })
            )
          ),
          error && h("div", { className: "error" }, error),
          message && h("div", { className: "notice" }, message),
          h("div", { className: "nav" },
            h("div", { className: "tabs" },
              ["cars", "rentals"].concat(isAdmin ? ["admin"] : []).map(function (name) {
                const label = name === "cars" ? "Автомобили" : (name === "rentals" ? "Бронирования" : "Админ");
                return h("button", { key: name, className: "tab " + (tab === name ? "active" : ""), onClick: function () { switchTab(name); } }, label);
              })
            ),
            h("button", { className: "btn", disabled: busy, onClick: function () { tab === "admin" ? loadAdmin() : Promise.allSettled([loadCars(), loadRentals()]); } }, "Обновить")
          ),
          tab === "cars" && h("section", null,
            h("div", { className: "filters" },
              h("input", { className: "field", placeholder: "Поиск по марке, модели, номеру или типу", value: query, onChange: function (ev) { setQuery(ev.target.value); } }),
              h("label", { className: "toggle" },
                h("input", { type: "checkbox", checked: showAll, onChange: function (ev) { setShowAll(ev.target.checked); loadCars(ev.target.checked).catch(function (err) { setError(err.message); }); } }),
                "Показать занятые"
              )
            ),
            filteredCars.length ? h("div", { className: "grid" }, filteredCars.map(function (car) {
              const days = rentalDays(dateFrom, dateTo);
              const total = days ? car.price * days : 0;
              const available = carIsAvailable(car);
              return h("article", { className: "card car-card", key: car.carUid },
                h("div", { className: "card-head" },
                  h("div", null,
                    h("h3", null, car.brand + " " + car.model),
                    h("div", { className: "muted" }, car.registrationNumber)
                  ),
                  h("span", { className: available ? "pill good" : "pill warn" }, available ? "Доступна" : "Занята")
                ),
                h("div", { className: "meta" },
                  h("span", { className: "pill" }, car.type),
                  h("span", { className: "pill" }, String(car.power || 0) + " л.с.")
                ),
                h("div", { className: "row" },
                  h("span", { className: "price" }, money(car.price) + " / день"),
                  h("button", { className: "btn primary", disabled: busy || !available || !days, onClick: function () { openBooking(car); } }, busy ? "Подождите..." : (!available ? "Занята" : "Забронировать и оплатить"))
                ),
                h("div", { className: "ticket" },
                  h("strong", null, days ? money(total) : "Выберите даты"),
                  h("div", { className: "mini" }, days ? "Период: " + String(days) + " дн. Платеж создается автоматически." : "Дата окончания должна быть позже даты начала.")
                )
              );
            })) : h("div", { className: "empty" }, "По выбранным фильтрам автомобилей нет.")
          ),
          tab === "rentals" && h("section", null,
            rentals.length ? h("div", { className: "grid" }, rentals.map(function (rental) {
              const carName = rental.car ? rental.car.brand + " " + rental.car.model : rental.carUid;
              const payment = rental.payment || {};
              return h("article", { className: "card", key: rental.rentalUid },
                h("div", { className: "card-head" },
                  h("div", null,
                    h("h3", null, carName),
                    h("div", { className: "muted" }, rental.dateFrom + " - " + rental.dateTo)
                  ),
                  h("span", { className: statusClass(rental.status) }, statusText(rental.status))
                ),
                h("div", { className: "ticket" },
                  h("strong", null, "Платеж: " + statusText(payment.status)),
                  h("div", { className: "mini" }, money(payment.price || 0))
                ),
                h("div", { className: "row", style: { marginTop: "18px" } },
                  h("button", { className: "btn", disabled: busy || rental.status !== "IN_PROGRESS", onClick: function () { finishRental(rental); } }, "Завершить"),
                  h("button", { className: "btn danger", disabled: busy || rental.status === "CANCELED", onClick: function () { cancelRental(rental); } }, "Отменить")
                )
              );
            })) : h("div", { className: "empty" }, "У вас пока нет бронирований.")
          ),
          tab === "admin" && h("section", { className: "panel" },
            h("div", null,
              h("div", { className: "section-title" }, h("h3", null, "Отчет по статистике")),
              h("div", { className: "summary-grid" },
                h("div", { className: "metric" }, h("span", null, "Всего событий"), h("strong", null, stats ? stats.totalEvents : 0)),
                h("div", { className: "metric" }, h("span", null, "Типов действий"), h("strong", null, stats ? Object.keys(stats.actions || {}).length : 0)),
                h("div", { className: "metric" }, h("span", null, "Пользователей в отчете"), h("strong", null, stats ? Object.keys(stats.users || {}).length : 0))
              )
            ),
            h("div", null,
              h("div", { className: "section-title" }, h("h3", null, "Создать пользователя")),
              h("form", { className: "form", onSubmit: addUser },
                h("label", null, "Логин", h("input", { name: "username", placeholder: "new.user", required: true })),
                h("label", null, "Email", h("input", { name: "email", type: "email", placeholder: "user@example.com", required: true })),
                h("label", null, "Имя", h("input", { name: "fullName", placeholder: "Иван Иванов" })),
                h("label", null, "Пароль", h("input", { name: "password", type: "password", placeholder: "Временный пароль", required: true })),
                h("div", { className: "wide row" },
                  h("span", { className: "muted" }, "Новые аккаунты получают роль Пользователь по умолчанию."),
                  h("button", { className: "btn primary", disabled: busy }, busy ? "Создаем..." : "Создать пользователя")
                )
              )
            ),
            h("div", null,
              h("div", { className: "section-title" }, h("h3", null, "Пользователи")),
              h("div", { className: "table-wrap" },
                h("table", null,
                  h("thead", null, h("tr", null, ["Логин", "Email", "Имя", "Роль"].map(function (name) { return h("th", { key: name }, name); }))),
                  h("tbody", null, users.map(function (user) {
                    return h("tr", { key: user.username },
                      h("td", null, user.username),
                      h("td", null, user.email),
                      h("td", null, user.fullName),
                      h("td", null, h("span", { className: user.role === "Admin" ? "pill good" : "pill" }, user.role === "Admin" ? "Админ" : "Пользователь"))
                    );
                  }))
                )
              )
            ),
            h("div", null,
              h("div", { className: "section-title" }, h("h3", null, "Последние события")),
              h("div", { className: "table-wrap" },
                h("table", null,
                  h("thead", null, h("tr", null, ["Время", "Пользователь", "Метод", "URL", "Статус", "Действие", "Данные"].map(function (name) { return h("th", { key: name }, name); }))),
                  h("tbody", null, events.map(function (event) {
                    return h("tr", { key: event.id },
                      h("td", null, new Date(event.createdAt).toLocaleString()),
                      h("td", null, event.username),
                      h("td", null, event.method || "-"),
                      h("td", null, event.url || "-"),
                      h("td", null, event.status || "-"),
                      h("td", null, event.action),
                      h("td", null, JSON.stringify(event.payload))
                    );
                  }))
                )
              )
            )
          )
        ),
        bookingCar && h("div", { className: "modal-backdrop", role: "presentation", onClick: closeBooking },
          h("div", { className: "modal", role: "dialog", "aria-modal": "true", "aria-label": "Подтверждение бронирования", onClick: function (ev) { ev.stopPropagation(); } },
            h("h3", null, "Покупка бронирования"),
            h("div", { className: "modal-summary" },
              h("div", { className: "modal-row" }, h("span", null, "Автомобиль"), h("strong", null, bookingCar.brand + " " + bookingCar.model)),
              h("div", { className: "modal-row" }, h("span", null, "Номер"), h("strong", null, bookingCar.registrationNumber)),
              h("div", { className: "modal-row" }, h("span", null, "Период"), h("strong", null, dateFrom + " - " + dateTo)),
              h("div", { className: "modal-row" }, h("span", null, "Дней"), h("strong", null, String(rentalDays(dateFrom, dateTo))))
            ),
            h("div", { className: "modal-total" }, "К оплате: " + money((bookingCar.price || 0) * rentalDays(dateFrom, dateTo))),
            h("div", { className: "modal-actions" },
              h("button", { className: "btn primary", disabled: busy, onClick: function () { rent(bookingCar); } }, busy ? "Покупаем..." : "Купить"),
              h("button", { className: "btn", disabled: busy, onClick: closeBooking }, "Закрыть")
            )
          )
        )
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(h(App));
  </script>
</body>
</html>"""
)


@app.get("/manage/health")
async def health_check():
    return {"status": "OK"}


@app.get("/{path:path}", response_class=HTMLResponse)
async def spa(path: str = ""):
    return HTMLResponse(
        PAGE.safe_substitute(
            API_BASE_URL=API_BASE_URL,
            IDENTITY_URL=IDENTITY_URL,
            CLIENT_ID=CLIENT_ID,
            REDIRECT_URI=REDIRECT_URI,
        )
    )
