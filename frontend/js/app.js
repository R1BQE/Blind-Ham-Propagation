const API = "./api/v1";

async function readApiResponse(response, operation) {
  const contentType = response.headers.get("content-type") || "тип содержимого не указан";
  const body = await response.text();
  let data;
  try {
    data = body ? JSON.parse(body) : {};
  } catch {
    const preview = body.replace(/\s+/g, " ").trim().slice(0, 180);
    throw new Error(
      `${operation}: сервер вернул не JSON (HTTP ${response.status}; ${contentType}). ${preview}`
    );
  }
  if (!response.ok) {
    throw new Error(data.detail || `${operation}: HTTP ${response.status}.`);
  }
  return data;
}
const solarButton = document.querySelector("#solar-refresh");
const solarStatus = document.querySelector("#solar-status");
const solarReport = document.querySelector("#solar-report");
const localForm = document.querySelector("#locator-form");
const locatorInput = document.querySelector("#locator");
const locatorError = document.querySelector("#locator-error");
const localSubmit = document.querySelector("#local-submit");
const localStatus = document.querySelector("#local-status");
const localReport = document.querySelector("#local-report");
const serviceStatus = document.querySelector("#service-status");
const regionalStatus = document.querySelector("#regional-status");
const regionalDescription = document.querySelector("#regional-description");
const collectionDescription = document.querySelector("#collection-description");
const regionalReport = document.querySelector("#regional-report");
const regionalStartButton = document.querySelector("#regional-start");
const regionalCancelButton = document.querySelector("#regional-cancel");
const regionalRadiusInput = document.querySelector("#regional-radius");
const regionalDurationInput = document.querySelector("#regional-duration");

const DEFAULT_SETTINGS = { locator: "KP50DB", radiusKm: 100, periodHours: 6, durationSeconds: 60 };
let userSettings = { ...DEFAULT_SETTINGS };
let latestRegionalReport = null;
let activeRegionalSessionId = null;
let regionalPollRun = 0;

function formatPeriod(hours) {
  if (hours === 0.5) return "30 минут";
  if (hours === 1) return "1 час";
  if (hours >= 2 && hours <= 4) return `${hours} часа`;
  return `${hours} часов`;
}

function applySettings(settings) {
  const periodHours = [0.5, 1, 2, 3, 4, 5, 6].includes(Number(settings.periodHours))
    ? Number(settings.periodHours)
    : DEFAULT_SETTINGS.periodHours;
  const durationSeconds = [60, 120, 180, 300].includes(Number(settings.durationSeconds))
    ? Number(settings.durationSeconds)
    : DEFAULT_SETTINGS.durationSeconds;
  settings = { ...settings, periodHours, durationSeconds };
  userSettings = settings;
  locatorInput.value = settings.locator;
  regionalRadiusInput.value = String(settings.radiusKm);
  regionalDurationInput.value = String(settings.durationSeconds);
  collectionDescription.textContent =
    `Локатор ${settings.locator}; радиус ${settings.radiusKm} км; продолжительность ${settings.durationSeconds / 60} мин.`;
}

window.applyQthLocator = (locator) => {
  const settings = { ...userSettings, locator: String(locator).trim().toUpperCase() };
  if (latestRegionalReport && latestRegionalReport.locator !== settings.locator) {
    latestRegionalReport = null;
  }
  applySettings(settings);
  try {
    localStorage.setItem("blindHamPropagationSettings", JSON.stringify(settings));
  } catch {
    // The active page still uses the selected locator.
  }
};

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("blindHamPropagationSettings") || "null");
    if (saved && typeof saved.locator === "string"
        && Number.isFinite(Number(saved.radiusKm))) {
      applySettings({
        locator: saved.locator.trim().toUpperCase(),
        radiusKm: Number(saved.radiusKm),
        periodHours: Number(saved.periodHours) || 6,
        durationSeconds: Number(saved.durationSeconds) || 60,
      });
      return;
    }
  } catch {
    // Invalid or unavailable browser storage falls back to defaults.
  }
  applySettings({ ...DEFAULT_SETTINGS });
}

// Accessible tabs: arrow keys move between tabs and activate the selected panel.
const tabList = document.querySelector('[role="tablist"]');
const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));

function activateTab(tab, moveFocus = false) {
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    const panel = document.getElementById(item.getAttribute("aria-controls"));
    panel.hidden = !selected;
  }
  if (moveFocus) tab.focus();
  if (tab.id === "tab-local") {
    void loadLocalDashboard(locatorInput.value.trim().toUpperCase());
  }
}

tabList.addEventListener("click", (event) => {
  const tab = event.target.closest('[role="tab"]');
  if (tab && tabs.includes(tab)) activateTab(tab);
});

tabList.addEventListener("keydown", (event) => {
  const currentIndex = tabs.indexOf(document.activeElement);
  if (currentIndex < 0) return;
  let nextIndex;
  switch (event.key) {
    case "ArrowRight":
      nextIndex = (currentIndex + 1) % tabs.length;
      break;
    case "ArrowLeft":
      nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      break;
    case "Home":
      nextIndex = 0;
      break;
    case "End":
      nextIndex = tabs.length - 1;
      break;
    default:
      return;
  }
  event.preventDefault();
  activateTab(tabs[nextIndex], true);
});

function addText(parent, tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  parent.append(element);
  return element;
}

function formatValue(measurement) {
  if (!measurement || measurement.value === null || measurement.value === undefined) return "Нет данных";
  return `${measurement.value} ${measurement.unit || ""}`.trim();
}

function renderSolar(data) {
  solarReport.replaceChildren();
  addText(solarReport, "p", `Время обновления: ${new Date().toLocaleString("ru-RU")}`, "muted");
  if (typeof window.renderSolarOverview === "function") {
    solarReport.append(window.renderSolarOverview(data.hamqsl || {}, data.measurements || {}));
  } else {
    addText(solarReport, "p", "Модуль сводки солнечной активности не загружен.");
  }
  if (data.errors && Object.keys(data.errors).length) {
    const section = document.createElement("section");
    section.className = "result-card";
    addText(section, "h3", "Часть источников временно недоступна");
    const list = document.createElement("ul");
    for (const [name, message] of Object.entries(data.errors)) addText(list, "li", `${name}: ${message}`);
    section.append(list);
    solarReport.append(section);
  }
}

async function loadSolar() {
  solarButton.disabled = true;
  solarReport.setAttribute("aria-busy", "true");
  solarStatus.textContent = "Получаем данные NOAA и HamQSL…";
  try {
    const response = await fetch(`${API}/solar/activity`, { cache: "no-store" });
    if (!response.ok) throw new Error("Сервер вернул ошибку.");
    const data = await response.json();
    renderSolar(data);
    solarStatus.textContent = data.status === "partial"
      ? "Часть источников временно недоступна. Доступные данные показаны ниже."
      : "Данные солнечной активности обновлены.";
  } catch (error) {
    solarStatus.textContent = `Не удалось получить данные: ${error.message}`;
  } finally {
    solarButton.disabled = false;
    solarReport.setAttribute("aria-busy", "false");
  }
}

function formatObservationTime(value) {
  if (!value) return "время неизвестно";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ru-RU");
}

function renderBandSummary(parent, rows) {
  if (!rows?.length) return;
  const table = document.createElement("table");
  table.className = "data-table";
  const caption = document.createElement("caption");
  caption.textContent = "Распределение по диапазонам и режимам";
  table.append(caption);
  const thead = document.createElement("thead");
  const header = document.createElement("tr");
  for (const label of ["Диапазон", "Режим", "Записей о приёме", "Разных станций", "Последнее наблюдение"]) {
    const th = addText(header, "th", label);
    th.scope = "col";
  }
  thead.append(header);
  table.append(thead);
  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const value of [
      row.band,
      row.mode,
      String(row.spots),
      String(row.stations),
      formatObservationTime(row.last_seen),
    ]) addText(tr, "td", value);
    tbody.append(tr);
  }
  table.append(tbody);
  parent.append(table);
}

function formatDistanceFromLocator(value) {
  return value === null || value === undefined
    ? "Неизвестно: нет координат станции."
    : `${Number(value).toLocaleString("ru-RU")} км`;
}

function addObservationRows(parent, rows) {
  const list = document.createElement("dl");
  list.className = "measurements observation-details";
  for (const [label, value] of rows) {
    addText(list, "dt", label);
    addText(list, "dd", value);
  }
  parent.append(list);
}

function renderRegionalDirection(parent, title, description, data, roles, direction, sessionId) {
  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", title);
  addText(section, "p", description);

  addObservationRows(section, [
    ["Всего приёмов", String(data.spots)],
    ["Станций рядом", String(data.unique_local_stations)],
    ["Последний приём", formatObservationTime(data.last_seen)],
  ]);
  renderBandSummary(section, data.by_band);

  const list = document.createElement("ol");
  list.className = "observation-list";

  if (data.stations?.length) {
    addText(section, "h4", "Станции");

    for (const item of data.stations) {
      const entry = document.createElement("li");
      const stationHeading = addText(entry, "h4", item.local_call || item.local_grid || "Станция без позывного");
      stationHeading.tabIndex = -1;
      addText(entry, "p", `Наблюдений: ${item.station_spots || 1}; последнее: ${formatObservationTime(item.observed_at)}`, "muted");
      addText(entry, "p", `${item.band} · ${item.mode}`);

      addText(entry, "h5", roles.localTitle);
      addObservationRows(entry, [
        ["Позывной", item.local_call || "Не указан"],
        ["Локатор", item.local_grid || "Не указан"],
        ["От твоего локатора", formatDistanceFromLocator(item.local_distance_km)],
      ]);

      addText(entry, "h5", roles.remoteTitle);
      addObservationRows(entry, [
        ["Позывной", item.remote_call || "Не указан"],
        ["Локатор", item.remote_grid || "Не указан"],
        ["От твоего локатора", formatDistanceFromLocator(item.distance_km)],
      ]);

      const pathRows = [
        ["Между станциями", item.station_distance_km === null || item.station_distance_km === undefined
          ? "Неизвестно: нет локатора одной из станций."
          : `${Number(item.station_distance_km).toLocaleString("ru-RU")} км`],
        ["Направление передачи", item.station_azimuth
          ? `${item.station_azimuth}, ${item.station_azimuth_degrees}°`
          : "Неизвестно: нет локатора одной из станций."],
      ];
      if (item.bearing) {
        pathRows.push([
          "Направление от твоего локатора до удалённой станции",
          `${item.bearing}, ${item.bearing_degrees}°`,
        ]);
      }
      if (item.snr_db !== null && item.snr_db !== undefined) {
        pathRows.push(["Уровень сигнала", `${item.snr_db} дБ`]);
      }
      pathRows.push(["Время приёма", formatObservationTime(item.observed_at)]);
      addObservationRows(entry, pathRows);
      list.append(entry);
    }
    section.append(list);
  } else if (!data.stations_total) {
    addText(section, "p", "За выбранный период приёмов в указанном районе нет.");
  }

  if ((data.stations?.length || 0) < (data.stations_total || 0)) {
    const more = document.createElement("button");
    more.type = "button";
    more.textContent = "Загрузить ещё 10";
    more.addEventListener("click", async () => {
      more.disabled = true;
      try {
        const nextOffset = data.stations?.length || 0;
        const params = new URLSearchParams({ direction, limit: "10", offset: String(nextOffset) });
        const response = await fetch(`${API}/psk-reporter/regional/sessions/${encodeURIComponent(sessionId)}/stations?${params}`, { cache: "no-store" });
        const nextData = await readApiResponse(response, "Подгрузка станций");
        const temporary = document.createElement("div");
        renderRegionalDirection(temporary, title, description, nextData, roles, direction, sessionId);
        const nextList = temporary.querySelector(".observation-list");
        const previousCount = list.children.length;
        if (nextList) {
          for (const child of Array.from(nextList.children)) list.append(child);
        }
        data.stations = [...(data.stations || []), ...(nextData.stations || [])];
        data.stations_total = nextData.stations_total;
        regionalStatus.textContent = "Подгружено";
        const newEntries = Array.from(list.children).slice(previousCount);
        const firstNew = newEntries[0];
        if (firstNew) firstNew.querySelector("h4")?.focus();
        void window.locationTools?.enrichRegionalEntries(newEntries);
        if (data.stations.length >= data.stations_total) more.remove();
      } catch (error) {
        regionalStatus.textContent = error.message;
        more.disabled = false;
      }
    });
    section.append(more);
  }
  parent.append(section);
}

function renderRegionalReport(data) {
  regionalReport.replaceChildren();
  regionalDescription.textContent =
    `Последний сбор: локатор ${data.locator}, радиус ${data.radius_km} км, ${Math.round((data.period_seconds || 60) / 60)} мин.`;
  const info = document.createElement("p");
  info.className = "muted";
  info.textContent =
    `Твой локатор: ${data.locator}. Радиус поиска: ${data.radius_km} км. Продолжительность сбора: ${Math.round((data.period_seconds || 60) / 60)} мин. В отчёт вошли только свежие споты, полученные во время этого сбора.`;
  regionalReport.append(info);

  renderRegionalDirection(
    regionalReport,
    "Передачи станций рядом с тобой услышали в других местах",
    "Здесь перечислены передачи радиолюбителей из выбранного радиуса вокруг твоего локатора. Их сигналы приняли удалённые станции.",
    data.tx,
    {
      localTitle: "Передатчик рядом с тобой",
      remoteTitle: "Удалённый приёмник",
    },
    "tx",
    data.session_id
  );
  renderRegionalDirection(
    regionalReport,
    "Приёмники рядом с тобой услышали станции из других мест",
    "Здесь перечислены удалённые радиолюбители, чьи передачи приняли станции в выбранном радиусе вокруг твоего локатора.",
    data.rx,
    {
      localTitle: "Приёмник рядом с тобой",
      remoteTitle: "Удалённый передатчик",
    },
    "rx",
    data.session_id
  );
  void window.locationTools?.enrichRegionalReport(regionalReport, data);
}

function waitForRegionalPoll() {
  return new Promise((resolve) => window.setTimeout(resolve, 3000));
}

function setRegionalCollectionState(collecting) {
  regionalStartButton.disabled = collecting;
  regionalCancelButton.disabled = !collecting;
  regionalRadiusInput.disabled = collecting;
  regionalDurationInput.disabled = collecting;
}

async function startRegionalCollection() {
  const locator = locatorInput.value.trim().toUpperCase();
  const radiusKm = Number(regionalRadiusInput.value);
  const durationSeconds = Number(regionalDurationInput.value);
  if (!locator) {
    locatorError.textContent = "Сначала укажи QTH-локатор.";
    locatorInput.focus();
    return;
  }
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 1000) {
    regionalStatus.textContent = "Радиус должен быть от 1 до 1000 км.";
    regionalRadiusInput.focus();
    return;
  }
  if (![60, 120, 180, 300].includes(durationSeconds)) {
    regionalStatus.textContent = "Выбери продолжительность от 1 до 5 минут.";
    regionalDurationInput.focus();
    return;
  }
  regionalStartButton.disabled = true;
  regionalStatus.textContent = "Проверяем локатор и подключение PSK Reporter…";
  try {
    const validated = await readApiResponse(await fetch(`${API}/locator/validate`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locator }), cache: "no-store",
    }), "Проверка локатора");
    userSettings = { ...userSettings, locator: validated.locator, radiusKm, durationSeconds };
    applySettings(userSettings);
    try { localStorage.setItem("blindHamPropagationSettings", JSON.stringify(userSettings)); } catch {}
    const session = await readApiResponse(await fetch(`${API}/psk-reporter/regional/sessions`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locator: validated.locator, radius_km: radiusKm, duration_seconds: durationSeconds }),
      cache: "no-store",
    }), "Запуск сбора");
    activeRegionalSessionId = session.session_id;
    regionalPollRun += 1;
    const runId = regionalPollRun;
    try { localStorage.setItem("blindHamPropagationSessionId", activeRegionalSessionId); } catch {}
    setRegionalCollectionState(true);
    latestRegionalReport = null;
    regionalReport.replaceChildren();
    regionalReport.setAttribute("aria-busy", "true");
    if (!document.getElementById("panel-local").hidden) {
      void loadLocalDashboard(locator);
    }
    regionalStatus.textContent = session.reused
      ? `Этот сбор уже выполняется. Осталось около ${session.remaining_seconds} секунд.`
      : `Сбор начат на ${durationSeconds / 60} мин. Получаем свежие наблюдения…`;
    await pollRegionalSession(activeRegionalSessionId, runId);
  } catch (error) {
    regionalStatus.textContent = error.message || "Не удалось запустить сбор.";
    setRegionalCollectionState(false);
  }
}

async function pollRegionalSession(sessionId, runId) {
  while (runId === regionalPollRun) {
    const progress = await readApiResponse(await fetch(
      `${API}/psk-reporter/regional/sessions/${encodeURIComponent(sessionId)}`,
      { cache: "no-store" },
    ), "Получение состояния сбора");
    if (progress.state === "cancelled") {
      regionalStatus.textContent = "Сбор остановлен. Незавершённый результат не сохранён.";
      setRegionalCollectionState(false);
      regionalReport.setAttribute("aria-busy", "false");
      return;
    }
    if (progress.state === "completed") {
      latestRegionalReport = progress.report;
      renderRegionalReport(latestRegionalReport);
      regionalStatus.textContent = `Сбор завершён. Получено ${progress.accepted_spots} подходящих спотов.`;
      setRegionalCollectionState(false);
      regionalReport.setAttribute("aria-busy", "false");
      if (!document.getElementById("panel-local").hidden) {
        await loadLocalDashboard(locatorInput.value.trim().toUpperCase());
      }
      return;
    }
    regionalStatus.textContent =
      `Сбор продолжается. Осталось примерно ${progress.remaining_seconds} сек. Подходящих спотов: ${progress.accepted_spots}.`;
    await waitForRegionalPoll();
  }
}

async function cancelRegionalCollection() {
  if (!activeRegionalSessionId) return;
  regionalCancelButton.disabled = true;
  regionalStatus.textContent = "Останавливаем сбор…";
  try {
    await readApiResponse(await fetch(
      `${API}/psk-reporter/regional/sessions/${encodeURIComponent(activeRegionalSessionId)}`,
      { method: "DELETE", cache: "no-store" },
    ), "Остановка сбора");
    regionalPollRun += 1;
    setRegionalCollectionState(false);
    regionalReport.setAttribute("aria-busy", "false");
    regionalStatus.textContent = "Сбор остановлен. Незавершённые результаты не будут показаны.";
    activeRegionalSessionId = null;
    try { localStorage.removeItem("blindHamPropagationSessionId"); } catch {}
  } catch (error) {
    regionalStatus.textContent = error.message || "Не удалось остановить сбор.";
    regionalCancelButton.disabled = false;
  }
}


async function restoreLastRegionalSession() {
  let sessionId = null;
  try { sessionId = localStorage.getItem("blindHamPropagationSessionId"); } catch {}
  if (!sessionId) return;
  try {
    const progress = await readApiResponse(await fetch(
      `${API}/psk-reporter/regional/sessions/${encodeURIComponent(sessionId)}`,
      { cache: "no-store" },
    ), "Восстановление последнего сбора");
    activeRegionalSessionId = sessionId;
    if (progress.state === "completed") {
      latestRegionalReport = progress.report;
      renderRegionalReport(latestRegionalReport);
      regionalStatus.textContent = "Показан результат последнего сбора.";
      return;
    }
    if (progress.state === "collecting") {
      regionalPollRun += 1;
      setRegionalCollectionState(true);
      regionalStatus.textContent = `Восстановлен выполняющийся сбор. Осталось около ${progress.remaining_seconds} секунд.`;
      void pollRegionalSession(sessionId, regionalPollRun).catch((error) => {
        setRegionalCollectionState(false);
        regionalStatus.textContent = error.message || "Не удалось продолжить сбор.";
      });
      return;
    }
    activeRegionalSessionId = null;
    localStorage.removeItem("blindHamPropagationSessionId");
  } catch {
    activeRegionalSessionId = null;
    try { localStorage.removeItem("blindHamPropagationSessionId"); } catch {}
  }
}

function renderLocal(data, regional, errors = {}) {
  localReport.replaceChildren();
  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", `Солнечные условия в районе ${data.locator}`);
  const list = document.createElement("dl");
  list.className = "measurements";
  for (const [label, value] of [
    ["Что сейчас с освещением", data.solar.illumination],
    ["Насколько высоко Солнце над горизонтом", `${data.solar.solar_elevation_degrees}°`],
    ["Расчётное солнечное время в этом районе", data.solar.local_mean_solar_time],
    ["Широта центра квадрата локатора", `${data.latitude}°`],
    ["Долгота центра квадрата локатора", `${data.longitude}°`],
  ]) {
    addText(list, "dt", label);
    addText(list, "dd", value);
  }
  section.append(list);
  addText(section, "p", "Это расчёт положения Солнца по координатам локатора и времени UTC. Он показывает освещение твоего района, но сам по себе не измеряет состояние ионосферы.");
  addText(section, "p", "Днём солнечное излучение поддерживает нижнюю часть ионосферы. Она может сильнее поглощать некоторые КВ-сигналы. Ночью это поглощение обычно ослабевает. Для оценки конкретной радиотрассы нужны координаты обеих станций и отдельная модель прохождения.");
  addText(section, "p", `Время расчёта: ${formatObservationTime(data.generated_at)}`, "muted");
  localReport.append(section);
  if (data.drap?.nearest_cell) {
    const drap = document.createElement("section");
    drap.className = "result-card";
    addText(drap, "h3", "Оценка поглощения радиосигналов в твоём районе");
    const cell = data.drap.nearest_cell;
    addText(drap, "p", cell.frequency_mhz === null
      ? "Модель не вернула числовую оценку. Это не означает нулевое поглощение."
      : `По оценке модели пороговая частота составляет ${cell.frequency_mhz} МГц.`);
    addText(drap, "p", `Расчёт относится к ближайшему участку сетки модели: широта ${cell.latitude}°, долгота ${cell.longitude}°.`);
    addText(drap, "p", "Это модельная оценка поглощения в нижней части ионосферы. Она не показывает максимальную рабочую частоту КВ и не является прогнозом MUF.");
    addText(drap, "p", `Время обновления модели: ${formatObservationTime(data.drap.valid_at)}. Сетка модели довольно крупная, поэтому оценка приблизительная.`, "muted");
    addText(drap, "p", data.drap.description, "muted");
    localReport.append(drap);
  } else if (data.drap?.status === "unavailable") {
    addText(localReport, "p", data.drap.error, "muted");
  }

  const activity = document.createElement("section");
  activity.className = "result-card";
  addText(activity, "h3", "Какие диапазоны сейчас наиболее активны рядом с тобой");
  addText(activity, "p",
    `Учитываются свежие радионаблюдения, собранные вручную в течение ${Math.round((regional?.period_seconds || userSettings.durationSeconds) / 60)} мин в радиусе ${regional?.radius_km ?? userSettings.radiusKm} км от локатора ${data.locator}. Считаются реальные записи PSK Reporter, а не расчётная вероятность связи.`);
  if (regional) {
    renderLocalBandActivity(activity, regional);
  } else {
    addText(activity, "p", errors.regional || "Пока не удалось получить радионаблюдения.", "muted");
  }
  localReport.append(activity);
  void window.locationTools?.enrichLocalReport(localReport, data);

}

function renderLocalBandActivity(parent, regional) {
  const totals = new Map();
  for (const [direction, label] of [["tx", "Передачи рядом услышали удалённые станции"], ["rx", "Приёмники рядом услышали удалённые станции"]]) {
    for (const row of regional[direction]?.by_band || []) {
      const band = String(row.band || "Неизвестно");
      if (!totals.has(band)) {
        totals.set(band, { band, tx: 0, rx: 0, lastSeen: null });
      }
      const item = totals.get(band);
      item[direction] += Number(row.spots) || 0;
      if (row.last_seen && (!item.lastSeen || Date.parse(row.last_seen) > Date.parse(item.lastSeen))) {
        item.lastSeen = row.last_seen;
      }
    }
  }
  const rows = [...totals.values()].sort((a, b) =>
    (b.tx + b.rx) - (a.tx + a.rx)
    || (Date.parse(b.lastSeen || 0) - Date.parse(a.lastSeen || 0))
    || a.band.localeCompare(b.band, "ru")
  );
  if (!rows.length) {
    addText(parent, "p",
      "Для этого локатора ещё нет результатов ручного сбора. Нажми «Начать сбор», чтобы получить свежие наблюдения.");
    return;
  }
  const top = rows[0];
  addText(parent, "p",
    `Чаще всего в наблюдениях встречается диапазон ${top.band}: ${top.tx + top.rx} записей. Из них ${top.tx} — передачи местных станций, услышанные в других местах; ${top.rx} — передачи удалённых станций, услышанные местными приёмниками.`);
  const table = document.createElement("table");
  table.className = "data-table";
  const caption = document.createElement("caption");
  caption.textContent = "Активность диапазонов по радионаблюдениям";
  table.append(caption);
  const thead = document.createElement("thead");
  const header = document.createElement("tr");
  for (const label of ["Диапазон", "Местные передачи услышали", "Местные приёмники услышали", "Всего записей", "Последний приём"]) {
    const th = addText(header, "th", label);
    th.scope = "col";
  }
  thead.append(header);
  table.append(thead);
  const tbody = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const value of [
      row.band,
      String(row.tx),
      String(row.rx),
      String(row.tx + row.rx),
      row.lastSeen ? formatObservationTime(row.lastSeen) : "Нет данных",
    ]) addText(tr, "td", value);
    tbody.append(tr);
  }
  table.append(tbody);
  parent.append(table);
  addText(parent, "p",
    "Важно: одна и та же передача может попасть в обе стороны, если обе станции находятся внутри выбранного радиуса. Поэтому сумма записей показывает активность наблюдений, а не число уникальных радиосвязей.", "muted");
}


async function loadLocalDashboard(locator) {
  if (!locator) return;
  localSubmit.disabled = true;
  localStatus.textContent = "Рассчитываем освещённость и загружаем результаты последнего сбора…";
  localReport.setAttribute("aria-busy", "true");
  localReport.replaceChildren();
  try {
    const data = await readApiResponse(
      await fetch(`${API}/local/report?locator=${encodeURIComponent(locator)}`, { cache: "no-store" }),
      "Расчёт условий в районе",
    );
    const regionalForLocator = latestRegionalReport?.locator === locator ? latestRegionalReport : null;
    renderLocal(data, regionalForLocator);
    localStatus.textContent = regionalForLocator
      ? "Условия и результаты последнего сбора отображены."
      : "Освещённость рассчитана. Радионаблюдения появятся после ручного сбора для этого локатора.";
  } catch (error) {
    localStatus.textContent = error.message || "Не удалось загрузить данные для локатора.";
  } finally {
    localSubmit.disabled = false;
    localReport.setAttribute("aria-busy", "false");
  }
}

localForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  locatorError.textContent = "";
  const locator = locatorInput.value.trim().toUpperCase();
  if (!locator) {
    locatorError.textContent = "Введи радиолюбительский локатор Maidenhead.";
    locatorInput.focus();
    return;
  }
  userSettings = { ...userSettings, locator };
  if (latestRegionalReport && latestRegionalReport.locator !== locator) {
    latestRegionalReport = null;
  }
  applySettings(userSettings);
  try { localStorage.setItem("blindHamPropagationSettings", JSON.stringify(userSettings)); } catch {}
  await loadLocalDashboard(locator);
});

solarButton.addEventListener("click", loadSolar);
void loadSolar();
regionalStartButton.addEventListener("click", startRegionalCollection);
regionalCancelButton.addEventListener("click", cancelRegionalCollection);
loadSettings();
void restoreLastRegionalSession();
collectionDescription.textContent =
  `Локатор ${userSettings.locator}; радиус ${userSettings.radiusKm} км; продолжительность ${userSettings.durationSeconds / 60} мин.`;
regionalDescription.textContent = "Результатов ещё нет. Запусти сбор на вкладке «Мой район».";
async function checkService() {
  try {
    const response = await fetch(`${API}/health`, { cache: "no-store" });
    if (!response.ok) throw new Error();
    serviceStatus.textContent = "Сервер приложения доступен.";
  } catch {
    serviceStatus.textContent = "Не удалось проверить сервер приложения.";
  }
}
checkService();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js", { scope: "./" }).catch(() => {});
  });
}

// Local mode advertises a WebSocket endpoint. A live WebSocket is not affected
// by background-tab timer throttling; closing the final local tab closes it.
let localSessionSocket = null;
let localSessionPageClosing = false;

async function startLocalBrowserSession() {
  try {
    const response = await fetch(`${API}/local-session`, { cache: "no-store" });
    if (!response.ok) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const apiPath = new URL(API, window.location.href).pathname;
    const socketUrl = `${protocol}//${window.location.host}${apiPath}/local-session`;

    const connect = () => {
      if (localSessionPageClosing) return;
      localSessionSocket = new WebSocket(socketUrl);
      localSessionSocket.addEventListener("close", () => {
        if (!localSessionPageClosing) window.setTimeout(connect, 2000);
      }, { once: true });
    };
    connect();
  } catch {
    // Production does not expose the local-only lifecycle endpoint.
  }
}

window.addEventListener("pagehide", () => {
  localSessionPageClosing = true;
  if (localSessionSocket) localSessionSocket.close();
}, { once: true });

void startLocalBrowserSession();
