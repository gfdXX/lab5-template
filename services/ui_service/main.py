import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


API_BASE_URL = os.getenv("UI_API_BASE_URL", "http://localhost:8080")
IDENTITY_URL = os.getenv("UI_IDENTITY_URL", "http://localhost:8090")
CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "car-rental-ui")
REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "http://localhost:3000/callback")

app = FastAPI(title="Car Rental UI", version="1.0.0")


@app.get("/manage/health")
async def health_check():
    return {"status": "OK"}


@app.get("/{path:path}", response_class=HTMLResponse)
async def spa(path: str = ""):
    return HTMLResponse(
        f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Car Rental</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <style>
    :root {{ color-scheme: light; font-family: Inter, Arial, sans-serif; color: #1d2533; background: #f3f6fb; }}
    body {{ margin: 0; }}
    button, input {{ font: inherit; }}
    .shell {{ min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }}
    header {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 16px 28px; background: #162032; color: white; }}
    header h1 {{ margin: 0; font-size: 20px; }}
    main {{ padding: 28px; max-width: 1180px; width: 100%; box-sizing: border-box; margin: 0 auto; }}
    .toolbar {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .tab, .btn {{ border: 1px solid #bdc8da; background: white; color: #1d2533; border-radius: 6px; padding: 9px 12px; cursor: pointer; }}
    .tab.active, .btn.primary {{ border-color: #2364d2; background: #2364d2; color: white; }}
    .btn.danger {{ border-color: #be3a3a; color: #9f1d20; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid #d8deea; border-radius: 8px; padding: 16px; box-shadow: 0 10px 28px rgba(20, 28, 45, .05); }}
    .card h3 {{ margin: 0 0 8px; font-size: 18px; }}
    .muted {{ color: #66748a; }}
    .row {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 10px; }}
    .form {{ display: grid; gap: 12px; max-width: 520px; }}
    .form input {{ padding: 10px 12px; border: 1px solid #bdc8da; border-radius: 6px; }}
    .notice {{ padding: 12px 14px; border-radius: 6px; background: #e8f0ff; color: #153a78; margin-bottom: 16px; }}
    .error {{ padding: 12px 14px; border-radius: 6px; background: #ffecec; color: #8e1f1f; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8deea; }}
    th, td {{ text-align: left; border-bottom: 1px solid #e6ebf3; padding: 10px 12px; vertical-align: top; }}
    th {{ background: #f8fafd; }}
  </style>
</head>
<body>
  <div id="root"></div>
  <script>
    const CONFIG = {{
      apiBase: "{API_BASE_URL}",
      identityUrl: "{IDENTITY_URL}",
      clientId: "{CLIENT_ID}",
      redirectUri: "{REDIRECT_URI}"
    }};
    if (location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {{
      CONFIG.apiBase = location.origin;
      CONFIG.identityUrl = location.origin;
      CONFIG.redirectUri = location.origin + "/callback";
    }}
    const e = React.createElement;
    const tokenStore = {{
      get: () => localStorage.getItem("access_token"),
      set: token => localStorage.setItem("access_token", token),
      clear: () => localStorage.removeItem("access_token")
    }};
    function decodeToken(token) {{
      try {{ return JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))); }}
      catch {{ return {{}}; }}
    }}
    function App() {{
      const [token, setToken] = React.useState(tokenStore.get());
      const [tab, setTab] = React.useState("cars");
      const [cars, setCars] = React.useState([]);
      const [rentals, setRentals] = React.useState([]);
      const [stats, setStats] = React.useState(null);
      const [users, setUsers] = React.useState([]);
      const [message, setMessage] = React.useState("");
      const [error, setError] = React.useState("");
      const claims = token ? decodeToken(token) : {{}};
      const isAdmin = (claims.roles || []).map(x => String(x).toLowerCase()).includes("admin");
      async function api(path, options = {{}}) {{
        const headers = Object.assign({{}}, options.headers || {{}});
        if (token) headers.Authorization = "Bearer " + token;
        if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
        const res = await fetch(CONFIG.apiBase + path, Object.assign({{}}, options, {{ headers }}));
        if (res.status === 204) return null;
        const text = await res.text();
        const data = text ? JSON.parse(text) : null;
        if (!res.ok) throw new Error(data.detail || text || "Request failed");
        return data;
      }}
      async function loadCars() {{
        setError("");
        const data = await api("/api/v1/cars?page=1&size=20&showAll=false");
        setCars(data.items || []);
      }}
      async function loadRentals() {{
        setError("");
        const data = await api("/api/v1/rental");
        setRentals(Array.isArray(data) ? data : data.items || []);
      }}
      async function loadAdmin() {{
        setStats(await api("/api/v1/statistics/summary"));
        setUsers(await api("/api/v1/users"));
      }}
      React.useEffect(() => {{
        const params = new URLSearchParams(location.search);
        const code = params.get("code");
        if (location.pathname === "/callback" && code) {{
          fetch(CONFIG.apiBase + "/api/v1/callback?code=" + encodeURIComponent(code) + "&redirect_uri=" + encodeURIComponent(CONFIG.redirectUri))
            .then(r => r.json())
            .then(data => {{ tokenStore.set(data.access_token); setToken(data.access_token); history.replaceState(null, "", "/"); }})
            .catch(err => setError(err.message));
        }}
      }}, []);
      React.useEffect(() => {{ if (token) {{ loadCars().catch(err => setError(err.message)); loadRentals().catch(() => null); }} }}, [token]);
      function login() {{
        const params = new URLSearchParams({{
          response_type: "code",
          client_id: CONFIG.clientId,
          redirect_uri: CONFIG.redirectUri,
          scope: "openid profile email",
          state: String(Date.now())
        }});
        location.href = CONFIG.identityUrl + "/oauth/authorize?" + params.toString();
      }}
      async function rent(car) {{
        const today = new Date();
        const until = new Date(today.getTime() + 3 * 86400000);
        await api("/api/v1/rental", {{ method: "POST", body: JSON.stringify({{ carUid: car.carUid, dateFrom: today.toISOString().slice(0,10), dateTo: until.toISOString().slice(0,10) }}) }});
        setMessage("Rental created");
        await loadCars(); await loadRentals();
      }}
      async function addUser(ev) {{
        ev.preventDefault();
        const form = new FormData(ev.currentTarget);
        await api("/api/v1/users", {{ method: "POST", body: JSON.stringify(Object.fromEntries(form.entries())) }});
        ev.currentTarget.reset();
        await loadAdmin();
      }}
      if (!token) return e("div", {{ className: "shell" }},
        e("header", null, e("h1", null, "Car Rental"), e("button", {{ className: "btn primary", onClick: login }}, "Sign in")),
        e("main", null, e("div", {{ className: "notice" }}, "Sign in through the Identity Provider to continue."))
      );
      return e("div", {{ className: "shell" }},
        e("header", null,
          e("h1", null, "Car Rental"),
          e("div", null, e("span", null, claims.preferred_username || claims.sub), " ", e("button", {{ className: "btn", onClick: () => {{ tokenStore.clear(); setToken(null); }} }}, "Sign out"))
        ),
        e("main", null,
          error && e("div", {{ className: "error" }}, error),
          message && e("div", {{ className: "notice" }}, message),
          e("div", {{ className: "toolbar" }},
            e("div", {{ className: "tabs" }},
              ["cars","rentals"].concat(isAdmin ? ["admin"] : []).map(name => e("button", {{ className: "tab " + (tab === name ? "active" : ""), onClick: async () => {{ setTab(name); setMessage(""); if (name === "admin") await loadAdmin(); }} }}, name))
            )
          ),
          tab === "cars" && e("section", {{ className: "grid" }}, cars.map(car => e("article", {{ className: "card", key: car.carUid }},
            e("h3", null, car.brand + " " + car.model),
            e("p", {{ className: "muted" }}, car.registrationNumber + " / " + car.type),
            e("div", {{ className: "row" }}, e("strong", null, car.price + " RUB/day"), e("button", {{ className: "btn primary", onClick: () => rent(car) }}, "Rent"))
          ))),
          tab === "rentals" && e("section", {{ className: "grid" }}, rentals.map(r => e("article", {{ className: "card", key: r.rentalUid }},
            e("h3", null, r.car ? (r.car.brand + " " + r.car.model) : r.carUid),
            e("p", {{ className: "muted" }}, r.dateFrom + " - " + r.dateTo),
            e("p", null, "Status: ", e("strong", null, r.status)),
            e("div", {{ className: "row" }},
              e("button", {{ className: "btn", onClick: async () => {{ await api("/api/v1/rental/" + r.rentalUid + "/finish", {{ method: "POST" }}); await loadRentals(); }} }}, "Finish"),
              e("button", {{ className: "btn danger", onClick: async () => {{ await api("/api/v1/rental/" + r.rentalUid, {{ method: "DELETE" }}); await loadRentals(); await loadCars(); }} }}, "Cancel")
            )
          ))),
          tab === "admin" && e("section", null,
            stats && e("div", {{ className: "grid" }},
              e("article", {{ className: "card" }}, e("h3", null, "Events"), e("strong", null, stats.totalEvents)),
              e("article", {{ className: "card" }}, e("h3", null, "Actions"), e("pre", null, JSON.stringify(stats.actions, null, 2))),
              e("article", {{ className: "card" }}, e("h3", null, "Users activity"), e("pre", null, JSON.stringify(stats.users, null, 2)))
            ),
            e("h2", null, "Create user"),
            e("form", {{ className: "form", onSubmit: addUser }},
              e("input", {{ name: "username", placeholder: "username", required: true }}),
              e("input", {{ name: "email", placeholder: "email", required: true }}),
              e("input", {{ name: "fullName", placeholder: "full name" }}),
              e("input", {{ name: "password", type: "password", placeholder: "password", required: true }}),
              e("button", {{ className: "btn primary" }}, "Create")
            ),
            e("h2", null, "Users"),
            e("table", null, e("thead", null, e("tr", null, ["Username","Email","Name","Role"].map(x => e("th", null, x)))),
              e("tbody", null, users.map(u => e("tr", {{ key: u.username }}, e("td", null, u.username), e("td", null, u.email), e("td", null, u.fullName), e("td", null, u.role)))))
          )
        )
      );
    }}
    ReactDOM.createRoot(document.getElementById("root")).render(e(App));
  </script>
</body>
</html>"""
    )
