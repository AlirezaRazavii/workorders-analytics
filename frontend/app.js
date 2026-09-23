// dashboard: fetch analytics data from the api and render charts/tables

const API = "http://127.0.0.1:8080";

const CATEGORY_COLORS = [
  "#2563eb", "#0ea5e9", "#14b8a6", "#f59e0b",
  "#ef4444", "#8b5cf6", "#64748b",
];

// short display names only, full names stay in the database
const SHORT_CATEGORY = {
  "بهره برداری": "بهره‌برداری",
  "لوازم اندازه گیری": "لوازم اندازه‌گیری",
  "تعمیرات اساسی": "تعمیرات اساسی",
  "سیم به کابل": "سیم به کابل",
  "نیرورسانی": "نیرورسانی",
  "تلفات": "تلفات",
  "توسعه و احداث و اصلاح و روشنایی معابر و برگشتی و طرح جامع بم": "توسعه و احداث",
};

const SHORT_STATUS = {
  "در دست اجرا": "در دست اجرا",
  "تهیه صورت وضعیت": "تهیه صورت وضعیت",
  "صورت وضعیت نزد مشاور": "نزد مشاور",
  "صورت وضعیت نزد ستاد": "نزد ستاد",
  "صورت وضعیت نزد مالی": "نزد مالی",
};

Chart.defaults.font.family = "Tahoma";
Chart.defaults.font.size = 12;

const charts = {};
let cityTrendLoaded = false;
let currentDateId = null;

const fa = (n) => Number(n ?? 0).toLocaleString("fa-IR");
const periodLabel = (p) => `${p.month_name} ${p.year_label}`;

async function getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> HTTP ${res.status}`);
  return res.json();
}

function drawChart(key, canvasId, config) {
  if (charts[key]) charts[key].destroy();
  charts[key] = new Chart(document.getElementById(canvasId), config);
}

//renderers

function renderKpis(k) {
  document.getElementById("kpiPeriod").textContent = periodLabel(k);
  document.getElementById("kpiTotal").textContent = fa(k.total_open);

  const change = document.getElementById("kpiChange");
  if (k.mom_change == null) {
    change.textContent = "ماه اول — مبنای مقایسه ندارد";
    change.className = "value muted";
  } else {
    // a drop in open orders means progress, so it is shown in green
    const good = k.mom_change <= 0;
    const arrow = k.mom_change > 0 ? "▲" : "▼";
    change.textContent = `${arrow} ${fa(Math.abs(k.mom_change))} (${k.mom_change_pct}٪)`;
    change.className = `value ${good ? "good" : "bad"}`;
  }

  document.getElementById("kpiTopCategory").textContent =
    k.top_category ? `${k.top_category.label} — ${fa(k.top_category.value)}` : "—";
  document.getElementById("kpiTopCity").textContent =
    k.top_city ? `${k.top_city.city_name} — ${fa(k.top_city.value)}` : "—";
}

function renderTrendChart(trend) {
  drawChart("trend", "trendChart", {
    type: "line",
    data: {
      labels: trend.map(periodLabel),
      datasets: [{
        label: "کل دستورکارهای باز",
        data: trend.map((p) => p.value),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.10)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { rtl: true, textDirection: "rtl" },
      },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderCategoryChart(items) {
  drawChart("category", "categoryChart", {
    type: "doughnut",
    data: {
      labels: items.map((i) => SHORT_CATEGORY[i.label] || i.label),
      datasets: [{
        data: items.map((i) => i.value),
        backgroundColor: CATEGORY_COLORS,
        borderColor: "#ffffff",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "55%",
      plugins: {
        legend: { position: "left", rtl: true, labels: { padding: 10 } },
        tooltip: {
          rtl: true,
          textDirection: "rtl",
          callbacks: {
            label: (c) => {
              const item = items[c.dataIndex];
              return ` ${fa(item.value)} عدد — ${item.share ?? 0}٪`;
            },
          },
        },
      },
    },
  });
}

function renderStatusChart(items) {
  drawChart("status", "statusChart", {
    type: "bar",
    data: {
      labels: items.map((i) => SHORT_STATUS[i.label] || i.label),
      datasets: [{
        label: "تعداد دستورکار",
        data: items.map((i) => i.value),
        backgroundColor: "#0ea5e9",
        borderRadius: 6,
        maxBarThickness: 60,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { rtl: true, textDirection: "rtl" },
      },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderCityChart(items) {
  drawChart("city", "cityChart", {
    type: "bar",
    data: {
      labels: items.map((i) => i.city_name),
      datasets: [{
        label: "تعداد دستورکار باز",
        data: items.map((i) => i.value),
        backgroundColor: "#2563eb",
        borderRadius: 4,
      }],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { rtl: true, textDirection: "rtl" },
      },
      scales: { x: { beginAtZero: true } },
    },
  });
}

async function loadCityTrend(cityCode) {
  const trend = await getJson(`${API}/api/city-trend?city_code=${cityCode}`);
  drawChart("cityTrend", "cityTrendChart", {
    type: "line",
    data: {
      labels: trend.map(periodLabel),
      datasets: [{
        label: "دستورکارهای باز",
        data: trend.map((p) => p.value),
        borderColor: "#f59e0b",
        backgroundColor: "rgba(245, 158, 11, 0.12)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { rtl: true, textDirection: "rtl" },
      },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function makeCell(tag, text, className) {
  const el = document.createElement(tag);
  el.textContent = text;
  if (className) el.className = className;
  return el;
}

// ---------- matrix table with sorting ----------

// sort state per table: key is null (city number order),
// "total" or a column name; dir is "asc" or "desc"
const matrixStates = {};

// extract the numeric part of a city name ("شهر 12" -> 12)
function cityNumber(name) {
  const faDigits = "۰۱۲۳۴۵۶۷۸۹";
  const latin = String(name).replace(/[۰-۹]/g, (d) => faDigits.indexOf(d));
  const match = latin.match(/\d+/);
  return match ? Number(match[0]) : Number.MAX_SAFE_INTEGER;
}

function sortMatrixRows(rows, state) {
  const sorted = [...rows];
  if (state.key === null) {
    sorted.sort((a, b) =>
      cityNumber(a.city_name) - cityNumber(b.city_name) || a.city_code - b.city_code);
  } else if (state.key === "total") {
    sorted.sort((a, b) => (state.dir === "asc" ? a.total - b.total : b.total - a.total));
  } else {
    sorted.sort((a, b) => {
      const av = a.values[state.key] ?? 0;
      const bv = b.values[state.key] ?? 0;
      return state.dir === "asc" ? av - bv : bv - av;
    });
  }
  return sorted;
}

// header click cycle: most -> least -> default (city number) order
// opts.onCellClick: optional handler, makes data cells clickable
function renderMatrixTable(tableId, rows, labelFn, opts) {
  const state = matrixStates[tableId] || (matrixStates[tableId] = { key: null, dir: "desc" });

  const table = document.getElementById(tableId);
  const cols = rows.length ? Object.keys(rows[0].values) : [];
  const max = Math.max(1, ...rows.flatMap((r) => Object.values(r.values)));
  const sorted = sortMatrixRows(rows, state);
  const arrow = (key) => (state.key === key ? (state.dir === "desc" ? " ▼" : " ▲") : "");

  const toggle = (key) => () => {
    if (state.key !== key) {
      state.key = key;
      state.dir = "desc";
    } else if (state.dir === "desc") {
      state.dir = "asc";
    } else {
      state.key = null;
      state.dir = "desc";
    }
    renderMatrixTable(tableId, rows, labelFn, opts);
  };

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");

  const cityTh = document.createElement("th");
  cityTh.textContent = "شهر";
  cityTh.title = "ترتیب بر اساس شماره شهر";
  cityTh.classList.add("sortable");
  cityTh.onclick = () => {
    state.key = null;
    state.dir = "desc";
    renderMatrixTable(tableId, rows, labelFn, opts);
  };
  headRow.appendChild(cityTh);

  cols.forEach((c) => {
    const th = document.createElement("th");
    th.textContent = (labelFn(c) || c) + arrow(c);
    th.title = "مرتب‌سازی: بیشترین، کمترین، پیش‌فرض";
    th.classList.add("sortable");
    th.onclick = toggle(c);
    headRow.appendChild(th);
  });

  const totalTh = document.createElement("th");
  totalTh.textContent = "جمع" + arrow("total");
  totalTh.classList.add("sortable");
  totalTh.onclick = toggle("total");
  headRow.appendChild(totalTh);

  thead.appendChild(headRow);

  const tbody = document.createElement("tbody");
  sorted.forEach((row) => {
    const tr = document.createElement("tr");
    tr.appendChild(makeCell("td", row.city_name, "city"));
    cols.forEach((c) => {
      const v = row.values[c] ?? 0;
      const td = makeCell("td", fa(v));
      const ratio = v / max;
      td.style.background = `rgba(37, 99, 235, ${(ratio * 0.75).toFixed(3)})`;
      if (ratio > 0.5) td.classList.add("light-text");
      if (opts && opts.onCellClick) {
        td.classList.add("clickable");
        td.title = "نمایش تفکیک دسته‌ای";
        td.onclick = () => opts.onCellClick(row, c);
      }
      tr.appendChild(td);
    });
    tr.appendChild(makeCell("td", fa(row.total), "total"));
    tbody.appendChild(tr);
  });

  table.replaceChildren(thead, tbody);
}

// ---------- city drill-down modal ----------

async function openCityDrilldown(cityRow, statusName) {
  const detail = await getJson(
    `${API}/api/city-detail?city_code=${cityRow.city_code}&date_id=${currentDateId}`
  );
  // map detail rows to the matrix-table shape so the same
  // renderer and sorting logic can be reused
  const rows = detail.map((r) => ({
    city_code: r.category_order,
    city_name: SHORT_CATEGORY[r.category_name] || r.category_name,
    values: r.values,
    total: r.total,
  }));
  matrixStates["drilldownTable"] = { key: statusName, dir: "desc" };
  renderMatrixTable("drilldownTable", rows, (s) => SHORT_STATUS[s] || s);

  document.getElementById("drilldownTitle").textContent =
    `تفکیک دسته‌ها — ${cityRow.city_name}`;
  document.getElementById("drilldownSubtitle").textContent =
    `پیش‌مرتب بر اساس «${SHORT_STATUS[statusName] || statusName}» — برای تغییر ترتیب روی سرستون‌ها کلیک کنید`;
  document.getElementById("drilldownModal").classList.add("open");
}

function closeDrilldown() {
  document.getElementById("drilldownModal").classList.remove("open");
}

document.getElementById("drilldownClose").onclick = closeDrilldown;
document.getElementById("drilldownModal").onclick = (e) => {
  if (e.target.id === "drilldownModal") closeDrilldown();
};
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDrilldown();
});

function renderEtl(run) {
  const box = document.getElementById("etlInfo");
  const ok = run.run_status === "success";
  const ended = run.finished_at ? new Date(run.finished_at).toLocaleString("fa-IR") : "—";
  box.innerHTML =
    `<span class="badge ${ok ? "ok" : "bad"}">${ok ? "موفق" : "ناموفق"}</span>` +
    `<span>اجرا شماره ${fa(run.run_id)}</span>` +
    `<span>${fa(run.rows_loaded)} رکورد در جدول Fact</span>` +
    `<span>${fa(run.checks_total)} اعتبارسنجی / ${fa(run.checks_failed)} خطا</span>` +
    `<span>پایان اجرا: ${ended}</span>`;
}

//data flow 

async function loadAll(dateId) {
    currentDateId = dateId;
    const [kpis, trend, byCategory, byStatus, byCity, matrix, cityStatus, etl] =
    await Promise.all([
      getJson(`${API}/api/kpis?date_id=${dateId}`),
      getJson(`${API}/api/trend`),
      getJson(`${API}/api/by-category?date_id=${dateId}`),
      getJson(`${API}/api/by-status?date_id=${dateId}`),
      getJson(`${API}/api/by-city?date_id=${dateId}`),
      getJson(`${API}/api/matrix?date_id=${dateId}`),
      getJson(`${API}/api/city-status?date_id=${dateId}`),
      getJson(`${API}/api/etl-status`),
    ]);

  renderKpis(kpis);
  renderTrendChart(trend);
  renderCategoryChart(byCategory);
  renderStatusChart(byStatus);
  renderCityChart(byCity);
  renderMatrixTable("matrixTable", matrix, (c) => SHORT_CATEGORY[c] || c);
  renderMatrixTable("statusMatrixTable", cityStatus, (s) => SHORT_STATUS[s] || s, {
    onCellClick: (row, status) => openCityDrilldown(row, status),
  });
  renderEtl(etl);

  // default the city selector to the busiest city of the selected month
  const citySelect = document.getElementById("citySelect");
  if (!cityTrendLoaded && byCity.length) {
    citySelect.value = byCity[0].city_code;
    cityTrendLoaded = true;
  }
  await loadCityTrend(citySelect.value);
}

async function init() {
  try {
    const [periods, cities] = await Promise.all([
      getJson(`${API}/api/periods`),
      getJson(`${API}/api/cities`),
    ]);

    const monthSelect = document.getElementById("monthSelect");
    periods.forEach((p) => monthSelect.appendChild(new Option(periodLabel(p), p.date_id)));
    monthSelect.value = periods[periods.length - 1].date_id;
    monthSelect.addEventListener("change", () => loadAll(monthSelect.value));

    const citySelect = document.getElementById("citySelect");
    cities
      .slice()
      .sort((a, b) => cityNumber(a.city_name) - cityNumber(b.city_name))
      .forEach((c) => citySelect.appendChild(new Option(c.city_name, c.city_code)));
    citySelect.addEventListener("change", () => loadCityTrend(citySelect.value));

    await loadAll(monthSelect.value);
  } catch (err) {
    const banner = document.getElementById("errorBanner");
    banner.hidden = false;
    banner.textContent =
      `ارتباط با API برقرار نشد (${err.message}). ` +
      "مطمئن شوید سرور روی پورت 8000 در حال اجراست.";
  }
}

document.addEventListener("DOMContentLoaded", init);