const API = "./api/v1";
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
const pskStatusButton = document.querySelector("#psk-status-refresh");
const pskStatus = document.querySelector("#psk-status");
const pskReport = document.querySelector("#psk-report");
const regionalRefresh = document.querySelector("#regional-refresh");
const regionalStatus = document.querySelector("#regional-status");
const regionalDescription = document.querySelector("#regional-description");
const regionalReport = document.querySelector("#regional-report");
const regionalLocatorForm = document.querySelector("#regional-locator-form");
const regionalLocatorInput = document.querySelector("#regional-locator");
const regionalLocatorError = document.querySelector("#regional-locator-error");
const regionalLocatorSubmit = document.querySelector("#regional-locator-submit");
const regionalRadiusInput = document.querySelector("#regional-radius");
const settingsForm = document.querySelector("#settings-form");
const settingsLocator = document.querySelector("#settings-locator");
const settingsRadius = document.querySelector("#settings-radius");
const settingsError = document.querySelector("#settings-error");
const settingsStatus = document.querySelector("#settings-status");

const DEFAULT_SETTINGS = { locator: "KP50DB", radiusKm: 100 };
let userSettings = { ...DEFAULT_SETTINGS };
let selectedBands = ["20m"];
let selectedModes = ["FT8"];

function applySettings(settings) {
  userSettings = settings;
  settingsLocator.value = settings.locator;
  settingsRadius.value = String(settings.radiusKm);
  locatorInput.value = settings.locator;
  regionalLocatorInput.value = settings.locator;
  regionalRadiusInput.value = String(settings.radiusKm);
  regionalDescription.textContent =
    `Область поиска: локатор ${settings.locator}, радиус ${settings.radiusKm} км. Период — последние 6 часов.`;
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("blindHamPropagationSettings") || "null");
    if (saved && typeof saved.locator === "string"
        && Number.isFinite(Number(saved.radiusKm))) {
      applySettings({
        locator: saved.locator.trim().toUpperCase(),
        radiusKm: Number(saved.radiusKm),
      });
      settingsStatus.textContent = "Загружены сохранённые настройки этого браузера.";
      return;
    }
  } catch {
    // Invalid or unavailable browser storage falls back to defaults.
  }
  applySettings({ ...DEFAULT_SETTINGS });
}

regionalLocatorForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  regionalLocatorError.textContent = "";
  const locator = regionalLocatorInput.value.trim().toUpperCase();
  const radiusKm = Number(regionalRadiusInput.value);
  const bands = Array.from(document.querySelectorAll('input[name="regional-band"]:checked')).map((input) => input.value);
  const modes = Array.from(document.querySelectorAll('input[name="regional-mode"]:checked')).map((input) => input.value);
  if (!locator) {
    regionalLocatorError.textContent = "Введи локатор Maidenhead.";
    regionalLocatorInput.focus();
    return;
  }
  if (!Number.isFinite(radiusKm) || radiusKm <= 0 || radiusKm > 1000) {
    regionalLocatorError.textContent = "Радиус должен быть положительным числом от 1 до 1000 км.";
    regionalRadiusInput.focus();
    return;
  }
  if (!bands.length) {
    regionalLocatorError.textContent = "Выбери хотя бы один диапазон.";
    document.querySelector('input[name="regional-band"]').focus();
    return;
  }
  if (!modes.length) {
    regionalLocatorError.textContent = "Выбери хотя бы один режим.";
    document.querySelector('input[name="regional-mode"]').focus();
    return;
  }

  regionalLocatorSubmit.disabled = true;
  regionalStatus.textContent = "Проверяем локатор и применяем MQTT-подписки…";
  try {
    const validateResponse = await fetch(`${API}/locator/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locator }),
      cache: "no-store",
    });
    const locatorData = await validateResponse.json();
    if (!validateResponse.ok) throw new Error(locatorData.detail || "Некорректный локатор.");

    const subscriptionResponse = await fetch(`${API}/psk-reporter/subscriptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bands, modes }),
      cache: "no-store",
    });
    const subscriptionData = await subscriptionResponse.json();
    if (!subscriptionResponse.ok) throw new Error(subscriptionData.detail || "Не удалось изменить MQTT-подписки.");

    selectedBands = bands;
    selectedModes = modes;
    const settings = { locator: locatorData.locator, radiusKm };
    applySettings(settings);
    regionalDescription.textContent =
      `Локатор ${settings.locator}; радиус ${radiusKm} км; диапазоны: ${bands.join(", ")}; режимы: ${modes.join(", ")}; период: 6 часов.`;
    try {
      localStorage.setItem("blindHamPropagationSettings", JSON.stringify(settings));
      localStorage.setItem("blindHamPropagationPSKFilters", JSON.stringify({ bands, modes }));
    } catch {
      // Active settings remain in memory for this page.
    }
    regionalStatus.textContent =
      `Подписки обновлены: ${subscriptionData.topic_filters.length}. Ожидаем поток и загружаем накопленные наблюдения…`;
    await loadPskStatus();
    await loadRegionalReport();
  } catch (error) {
    regionalLocatorError.textContent = error.message;
    regionalStatus.textContent = "Не удалось применить параметры регионального поиска.";
  } finally {
    regionalLocatorSubmit.disabled = false;
  }
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  settingsError.textContent = "";
  const locator = settingsLocator.value.trim().toUpperCase();
  const radiusKm = Number(settingsRadius.value);
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 1000) {
    settingsError.textContent = "Радиус должен быть от 1 до 1000 км.";
    settingsRadius.focus();
    return;
  }
  const saveButton = document.querySelector("#settings-save");
  saveButton.disabled = true;
  settingsStatus.textContent = "Проверяем локатор…";
  try {
    const response = await fetch(`${API}/locator/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locator }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Некорректный локатор.");
    const settings = { locator: data.locator, radiusKm };
    localStorage.setItem("blindHamPropagationSettings", JSON.stringify(settings));
    applySettings(settings);
    settingsStatus.textContent =
      `Настройки сохранены: ${settings.locator}, радиус ${settings.radiusKm} км.`;
  } catch (error) {
    settingsError.textContent = error.message;
    settingsStatus.textContent = "Не удалось сохранить настройки.";
  } finally {
    saveButton.disabled = false;
  }
});

// Accessible tabs: arrow keys move between tabs and activate the selected panel.
const tabList = document.querySelector('[role="tablist"]');
const tabs = Array.from(tabList.querySelectorAll('[role="tab"]'));

function activateTab(tab, moveFocus = false) {
  const previousTab = tabs.find((item) => item.getAttribute("aria-selected") === "true");
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
    const panel = document.getElementById(item.getAttribute("aria-controls"));
    panel.hidden = !selected;
  }
  if (moveFocus) tab.focus();
  if (tab.id === "tab-spots") startPskReporterSession();
  else if (previousTab?.id === "tab-spots") stopPskReporterSession();
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
  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", "Текущие показатели");
  const list = document.createElement("dl");
  list.className = "measurements";
  const labels = [
    ["solar_flux", "Солнечный поток F10.7"],
    ["kp", "Планетарный индекс Kp"],
    ["solar_wind_speed", "Скорость солнечного ветра"],
    ["magnetic_field_bt", "Магнитное поле Bt"],
    ["magnetic_field_bz", "Компонента Bz GSM"],
    ["xray_flux", "Рентгеновский поток GOES"],
  ];
  for (const [key, label] of labels) {
    const measurement = data.measurements?.[key];
    addText(list, "dt", label);
    const value = document.createElement("dd");
    value.textContent = formatValue(measurement);
    if (measurement?.observed_at) value.append(document.createTextNode(`; наблюдение: ${measurement.observed_at}`));
    list.append(value);
  }
  section.append(list);
  addText(section, "p", `Источник: ${data.source}. Получено: ${data.retrieved_at}`, "muted");
  if (data.errors && Object.keys(data.errors).length) {
    const errors = document.createElement("ul");
    addText(section, "h3", "Предупреждения источников");
    for (const [name, message] of Object.entries(data.errors)) addText(errors, "li", `${name}: ${message}`);
    section.append(errors);
  }
  solarReport.append(section);
  if (data.drap) {
    const drap = document.createElement("section");
    drap.className = "result-card";
    addText(drap, "h3", "D-RAP: поглощение HF в D-области");
    addText(drap, "p", data.drap.description || "Модель NOAA для оценки поглощения радиоволн.");
    addText(drap, "p", `Состояние рентгеновского фона: ${data.drap.xray_message || "Нет данных"}`);
    addText(drap, "p", `Состояние протонного фона: ${data.drap.proton_message || "Нет данных"}`);
    addText(drap, "p", `Время актуальности модели: ${data.drap.valid_at || "Не указано"}`);
    addText(drap, "p", `Источник: ${data.drap.source}`, "muted");
    solarReport.append(drap);
  }
}

async function loadSolar() {
  solarButton.disabled = true;
  solarReport.setAttribute("aria-busy", "true");
  solarStatus.textContent = "Получаем данные NOAA…";
  try {
    const response = await fetch(`${API}/solar/activity`, { cache: "no-store" });
    if (!response.ok) throw new Error("Сервер вернул ошибку.");
    const data = await response.json();
    renderSolar(data);
    solarStatus.textContent = data.status === "partial"
      ? "Данные загружены частично. Список недоступных источников приведён ниже."
      : "Данные солнечной активности обновлены.";
  } catch (error) {
    solarStatus.textContent = `Не удалось получить данные: ${error.message}`;
  } finally {
    solarButton.disabled = false;
    solarReport.setAttribute("aria-busy", "false");
  }
}

function renderPskStatus(data) {
  pskReport.replaceChildren();
  const section = document.createElement("section");
  section.className = "result-card";
  const stateLabels = {
    disabled: "Сборщик выключен",
    idle: "Ожидает запуска",
    connecting: "Подключается к брокеру",
    connected: "Подключён, получает поток",
    reconnecting: "Потеряно соединение, выполняется переподключение",
    error: "Ошибка сборщика",
    stopped: "Сборщик остановлен",
    not_started: "Сборщик ещё не запущен",
  };
  addText(section, "h3", stateLabels[data.state] || data.state || "Состояние неизвестно");
  const list = document.createElement("dl");
  list.className = "measurements";
  const rows = [
    ["Брокер", data.broker ? `${data.broker}:${data.port}` : "Не задан"],
    ["Защищённое соединение", data.transport || "Неизвестно"],
    ["Подписки", (data.topic_filters || []).join(", ") || "Нет"],
    ["Получено MQTT-сообщений", String(data.messages_received ?? 0)],
    ["Сохранено новых спотов", String(data.spots_saved ?? 0)],
    ["Сейчас в хранилище", String(data.stored_spots ?? 0)],
    ["Повторных сообщений", String(data.duplicates ?? 0)],
    ["Некорректных сообщений", String(data.invalid_messages ?? 0)],
    ["Ошибок", String(data.errors ?? 0)],
    ["Последнее MQTT-сообщение", data.last_message_at || "Пока не поступало"],
    ["Время последнего спота", data.last_spot_at || "Пока не поступало"],
  ];
  for (const [label, value] of rows) {
    addText(list, "dt", label);
    addText(list, "dd", value);
  }
  section.append(list);
  if (data.last_error) addText(section, "p", `Последняя ошибка: ${data.last_error}`, "field-error");
  pskReport.append(section);
}

async function loadPskStatus() {
  pskStatusButton.disabled = true;
  pskReport.setAttribute("aria-busy", "true");
  pskStatus.textContent = "Проверяем состояние сборщика…";
  try {
    const response = await fetch(`${API}/psk-reporter/status`, { cache: "no-store" });
    if (!response.ok) throw new Error("Сервер вернул ошибку.");
    const data = await response.json();
    renderPskStatus(data);
    pskStatus.textContent = data.state === "connected"
      ? "Соединение с PSK Reporter установлено."
      : data.state === "disabled"
        ? "Сборщик выключен. Для теста его нужно включить переменной окружения."
        : "Состояние сборщика обновлено.";
  } catch (error) {
    pskStatus.textContent = `Не удалось получить состояние: ${error.message}`;
  } finally {
    pskStatusButton.disabled = false;
    pskReport.setAttribute("aria-busy", "false");
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
  for (const label of ["Диапазон", "Режим", "Спотов", "Станций", "Последнее наблюдение"]) {
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

function renderRegionalDirection(parent, title, description, data) {
  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", title);
  addText(section, "p", description);
  const summary = document.createElement("dl");
  summary.className = "measurements";
  for (const [label, value] of [
    ["Всего наблюдений", String(data.spots)],
    ["Уникальных местных станций", String(data.unique_local_stations)],
    ["Последнее наблюдение", formatObservationTime(data.last_seen)],
  ]) {
    addText(summary, "dt", label);
    addText(summary, "dd", value);
  }
  section.append(summary);
  renderBandSummary(section, data.by_band);
  if (data.latest?.length) {
    addText(section, "h4", "Последние наблюдения");
    const list = document.createElement("ol");
    list.className = "observation-list";
    for (const item of data.latest) {
      const local = `${item.local_call}${item.local_grid ? ` (${item.local_grid})` : ""}`;
      const remote = `${item.remote_call}${item.remote_grid ? ` (${item.remote_grid})` : ""}`;
      const distance = item.distance_km === null
        ? "расстояние до удалённой станции неизвестно"
        : `удалённая станция — ${item.distance_km} км от QTH`;
      const localDistance = item.local_distance_km === null
        ? ""
        : `; местная станция — ${item.local_distance_km} км от QTH`;
      const bearing = item.bearing
        ? `, направление на удалённую станцию ${item.bearing} (${item.bearing_degrees}°)`
        : "";
      const snr = item.snr_db === null || item.snr_db === undefined
        ? ""
        : `, сигнал ${item.snr_db} дБ`;
      addText(
        list,
        "li",
        `${formatObservationTime(item.observed_at)}; ${item.band} ${item.mode}; местная станция: ${local}; удалённая станция: ${remote}; ${distance}${bearing}${localDistance}${snr}.`
      );
    }
    section.append(list);
  } else {
    addText(section, "p", "За выбранный период наблюдений этого типа в указанной области нет.");
  }
  parent.append(section);
}

function renderRegionalReport(data) {
  regionalReport.replaceChildren();
  const info = document.createElement("p");
  info.className = "muted";
  info.textContent =
    `Локатор: ${data.locator}; радиус: ${data.radius_km} км; период: ${data.period_hours} ч. Диапазоны: ${(data.bands || []).join(", ") || "все"}; режимы: ${(data.modes || []).join(", ") || "все"}. Центр квадрата: ${data.latitude}, ${data.longitude}. Проверено записей в хранилище: ${data.stored_spots_scanned}. Сформировано: ${formatObservationTime(data.generated_at)}.`;
  regionalReport.append(info);
  renderRegionalDirection(
    regionalReport,
    "TX: местные передатчики услышаны снаружи",
    data.explanation.tx,
    data.tx
  );
  renderRegionalDirection(
    regionalReport,
    "RX: местные приёмники услышали удалённые станции",
    data.explanation.rx,
    data.rx
  );
  addText(regionalReport, "p", data.explanation.distance, "muted");
}

async function loadRegionalReport() {
  regionalRefresh.disabled = true;
  regionalReport.setAttribute("aria-busy", "true");
  regionalStatus.textContent = "Загружаем региональные наблюдения…";
  regionalReport.replaceChildren();
  const params = new URLSearchParams({
    locator: userSettings.locator,
    radius_km: String(userSettings.radiusKm),
    hours: "6",
    limit: "30",
    bands: selectedBands.join(","),
    modes: selectedModes.join(","),
  });
  try {
    const response = await fetch(`${API}/psk-reporter/regional?${params}`, {
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось получить региональные данные.");
    renderRegionalReport(data);
    regionalStatus.textContent =
      `Региональный отчёт готов. TX: ${data.tx.spots} наблюдений; RX: ${data.rx.spots} наблюдений.`;
  } catch (error) {
    regionalStatus.textContent = error.message;
  } finally {
    regionalRefresh.disabled = false;
    regionalReport.setAttribute("aria-busy", "false");
  }
}

function renderLocal(data) {
  localReport.replaceChildren();
  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", `Локальная информация для ${data.locator}`);
  const list = document.createElement("dl");
  list.className = "measurements";
  for (const [label, value] of [
    ["Широта центра квадрата", `${data.latitude}°`],
    ["Долгота центра квадрата", `${data.longitude}°`],
    ["Местное среднее солнечное время", data.solar.local_mean_solar_time],
    ["Положение Солнца", data.solar.illumination],
    ["Высота Солнца над горизонтом", `${data.solar.solar_elevation_degrees}°`],
  ]) {
    addText(list, "dt", label);
    addText(list, "dd", value);
  }
  section.append(list);
  addText(section, "p", data.solar.calculation, "muted");
  addText(section, "p", data.interpretation);
  addText(section, "p", `Рассчитано: ${data.generated_at}`, "muted");
  localReport.append(section);
  if (data.drap?.nearest_cell) {
    const drap = document.createElement("section");
    drap.className = "result-card";
    addText(drap, "h3", "D-RAP для района QTH");
    const cell = data.drap.nearest_cell;
    addText(drap, "p", cell.frequency_mhz === null
      ? "Для ближайшей ячейки нет числового значения."
      : `Частота: ${cell.frequency_mhz} МГц.`);
    addText(drap, "p", `Центр ближайшей ячейки модели: широта ${cell.latitude}°, долгота ${cell.longitude}°.`);
    addText(drap, "p", cell.meaning);
    addText(drap, "p", `Модель актуальна на: ${data.drap.valid_at || "не указано"}; разрешение сетки около 2° по широте и 4° по долготе.`, "muted");
    addText(drap, "p", data.drap.description, "muted");
    localReport.append(drap);
  } else if (data.drap?.status === "unavailable") {
    addText(localReport, "p", data.drap.error, "muted");
  }
}

localForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  locatorError.textContent = "";
  localReport.replaceChildren();
  const locator = locatorInput.value.trim().toUpperCase();
  if (!locator) {
    locatorError.textContent = "Введи QTH-локатор.";
    locatorInput.focus();
    return;
  }
  localSubmit.disabled = true;
  localStatus.textContent = "Рассчитываем локальные условия…";
  localReport.setAttribute("aria-busy", "true");
  try {
    const response = await fetch(`${API}/local/report?locator=${encodeURIComponent(locator)}`, { cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось обработать локатор.");
    renderLocal(data);
    localStatus.textContent = "Локальный отчёт готов.";
  } catch (error) {
    localStatus.textContent = error.message;
  } finally {
    localSubmit.disabled = false;
    localReport.setAttribute("aria-busy", "false");
  }
});

solarButton.addEventListener("click", loadSolar);
regionalRefresh.addEventListener("click", loadRegionalReport);
loadSettings();
try {
  const savedFilters = JSON.parse(localStorage.getItem("blindHamPropagationPSKFilters") || "null");
  if (savedFilters && Array.isArray(savedFilters.bands) && Array.isArray(savedFilters.modes)) {
    selectedBands = savedFilters.bands;
    selectedModes = savedFilters.modes;
    for (const input of document.querySelectorAll('input[name="regional-band"]')) input.checked = selectedBands.includes(input.value);
    for (const input of document.querySelectorAll('input[name="regional-mode"]')) input.checked = selectedModes.includes(input.value);
  }
} catch {
  // Keep the default 20m FT8 selection.
}
pskStatusButton.addEventListener("click", loadPskStatus);

let pskReporterSocket = null;
let pskReporterReconnectTimer = null;
let pskReporterTabActive = false;
let pskReporterPageClosing = false;

function stopPskReporterSession() {
  pskReporterTabActive = false;
  if (pskReporterReconnectTimer !== null) {
    window.clearTimeout(pskReporterReconnectTimer);
    pskReporterReconnectTimer = null;
  }
  if (pskReporterSocket) {
    const socket = pskReporterSocket;
    pskReporterSocket = null;
    socket.close();
  }
}

async function applyPskSubscriptions() {
  try {
    const response = await fetch(`${API}/psk-reporter/subscriptions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bands: selectedBands, modes: selectedModes }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось восстановить MQTT-подписки.");
    return data;
  } catch (error) {
    regionalStatus.textContent = error.message;
    return null;
  }
}

function startPskReporterSession() {
  pskReporterTabActive = true;
  if (pskReporterPageClosing || pskReporterSocket || pskReporterReconnectTimer !== null) return;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const apiPath = new URL(API, window.location.href).pathname;
  const socketUrl = `${protocol}//${window.location.host}${apiPath}/psk-reporter/session`;
  const socket = new WebSocket(socketUrl);
  pskReporterSocket = socket;
  socket.addEventListener("open", () => {
    if (!pskReporterTabActive || pskReporterPageClosing) {
      socket.close();
      return;
    }
    void (async () => {
      await applyPskSubscriptions();
      await loadPskStatus();
      await loadRegionalReport();
    })();
  });
  socket.addEventListener("close", () => {
    if (pskReporterSocket === socket) pskReporterSocket = null;
    if (pskReporterTabActive && !pskReporterPageClosing) {
      pskReporterReconnectTimer = window.setTimeout(() => {
        pskReporterReconnectTimer = null;
        startPskReporterSession();
      }, 2000);
    }
  });
  socket.addEventListener("error", () => {});
}

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
  pskReporterPageClosing = true;
  stopPskReporterSession();
  if (localSessionSocket) localSessionSocket.close();
}, { once: true });

void startLocalBrowserSession();
