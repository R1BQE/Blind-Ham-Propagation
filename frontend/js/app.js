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
const regionalPeriodSelect = document.querySelector("#regional-period");
const settingsForm = document.querySelector("#settings-form");
const settingsLocator = document.querySelector("#settings-locator");
const settingsRadius = document.querySelector("#settings-radius");
const settingsError = document.querySelector("#settings-error");
const settingsStatus = document.querySelector("#settings-status");

const DEFAULT_SETTINGS = { locator: "KP50DB", radiusKm: 100, periodHours: 6 };
let userSettings = { ...DEFAULT_SETTINGS };
const ALL_BANDS = ["160m", "80m", "60m", "40m", "30m", "20m", "17m", "15m", "12m", "10m", "6m", "2m", "70cm"];
const ALL_MODES = ["FT8", "FT4", "JS8", "JT65", "JT9", "MSK144", "PSK31", "PSK63", "RTTY", "OLIVIA", "MFSK", "WSPR"];
let bandSelection = "all";
let modeSelection = "all";
let selectedBands = [...ALL_BANDS];
let selectedModes = [...ALL_MODES];

function updateFilterVisibility() {
  bandSelection = document.querySelector('input[name="regional-band-selection"]:checked')?.value || "all";
  modeSelection = document.querySelector('input[name="regional-mode-selection"]:checked')?.value || "all";
  document.querySelector("#regional-band-options").hidden = bandSelection !== "custom";
  document.querySelector("#regional-mode-options").hidden = modeSelection !== "custom";
}

function getSelectedFilters() {
  const bands = bandSelection === "all"
    ? [...ALL_BANDS]
    : Array.from(document.querySelectorAll('input[name="regional-band"]:checked')).map((input) => input.value);
  const modes = modeSelection === "all"
    ? [...ALL_MODES]
    : Array.from(document.querySelectorAll('input[name="regional-mode"]:checked')).map((input) => input.value);
  return { bands, modes };
}

function filterDescription() {
  return `диапазоны: ${bandSelection === "all" ? "все" : selectedBands.join(", ")}; режимы: ${modeSelection === "all" ? "все" : selectedModes.join(", ")}`;
}

function applySettings(settings) {
  userSettings = settings;
  settingsLocator.value = settings.locator;
  settingsRadius.value = String(settings.radiusKm);
  locatorInput.value = settings.locator;
  regionalLocatorInput.value = settings.locator;
  regionalRadiusInput.value = String(settings.radiusKm);
  regionalPeriodSelect.value = String(settings.periodHours || 6);
  regionalDescription.textContent =
    `Область поиска: локатор ${settings.locator}, радиус ${settings.radiusKm} км. Период — последние ${settings.periodHours || 6} часов.`;
}

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem("blindHamPropagationSettings") || "null");
    if (saved && typeof saved.locator === "string"
        && Number.isFinite(Number(saved.radiusKm))) {
      applySettings({
        locator: saved.locator.trim().toUpperCase(),
        radiusKm: Number(saved.radiusKm),
        periodHours: Number(saved.periodHours) || 6,
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
  updateFilterVisibility();
  const locator = regionalLocatorInput.value.trim().toUpperCase();
  const radiusKm = Number(regionalRadiusInput.value);
  const periodHours = Number(regionalPeriodSelect.value);
  const filters = getSelectedFilters();
  const { bands, modes } = filters;
  if (!locator) {
    regionalLocatorError.textContent = "Введи локатор Maidenhead.";
    regionalLocatorInput.focus();
    return;
  }
  if (!Number.isFinite(radiusKm) || radiusKm < 1 || radiusKm > 1000) {
    regionalLocatorError.textContent = "Радиус должен быть положительным числом от 1 до 1000 км.";
    regionalRadiusInput.focus();
    return;
  }
  if (![3, 6, 9, 12, 15, 18, 21, 24].includes(periodHours)) {
    regionalLocatorError.textContent = "Выбери период наблюдений от 3 до 24 часов.";
    regionalPeriodSelect.focus();
    return;
  }
  if (!bands.length) {
    regionalLocatorError.textContent = "Выбери хотя бы один диапазон или переключи выбор на «Все».";
    document.querySelector('input[name="regional-band-selection"][value="custom"]').focus();
    return;
  }
  if (!modes.length) {
    regionalLocatorError.textContent = "Выбери хотя бы один режим или переключи выбор на «Все».";
    document.querySelector('input[name="regional-mode-selection"][value="custom"]').focus();
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
    const settings = { locator: locatorData.locator, radiusKm, periodHours };
    applySettings(settings);
    regionalDescription.textContent =
      `Локатор ${settings.locator}; радиус ${radiusKm} км; ${filterDescription()}; период: ${periodHours} часов.`;
    try {
      localStorage.setItem("blindHamPropagationSettings", JSON.stringify(settings));
      localStorage.setItem("blindHamPropagationPSKFilters", JSON.stringify({
        bandSelection, modeSelection, bands, modes,
      }));
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
    const settings = { ...userSettings, locator: data.locator, radiusKm };
    localStorage.setItem("blindHamPropagationSettings", JSON.stringify(settings));
    applySettings(settings);
    settingsStatus.textContent =
      `Настройки сохранены: ${settings.locator}, радиус ${settings.radiusKm} км, период ${settings.periodHours || 6} часов.`;
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
  const sessionTabs = ["tab-local", "tab-spots"];
  if (sessionTabs.includes(tab.id)) {
    startPskReporterSession();
    if (tab.id === "tab-local" && pskReporterSocket?.readyState === WebSocket.OPEN) {
      void loadLocalDashboard(locatorInput.value.trim().toUpperCase());
    }
  } else if (sessionTabs.includes(previousTab?.id)) {
    stopPskReporterSession();
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

  if (data.hamqsl && typeof window.renderHamqslMonitor === "function") {
    window.renderHamqslMonitor(data.hamqsl, data.measurements || {}, solarReport);
  }

  const section = document.createElement("section");
  section.className = "result-card";
  addText(section, "h3", "Измерения NOAA для сравнения");
  addText(section, "p",
    "NOAA и HamQSL — независимые источники. Значения могут отличаться из-за разного времени измерения и способов усреднения. Мы показываем их отдельно и не усредняем.",
    "muted");
  const list = document.createElement("dl");
  list.className = "measurements";
  const labels = [
    ["solar_flux", "Солнечный поток F10.7"],
    ["kp", "Индекс геомагнитной активности Kp"],
    ["solar_wind_speed", "Скорость солнечного ветра"],
    ["magnetic_field_bt", "Полная сила межпланетного магнитного поля Bt"],
    ["magnetic_field_bz", "Составляющая магнитного поля Bz"],
    ["xray_flux", "Рентгеновское излучение"],
  ];
  for (const [key, label] of labels) {
    const measurement = data.measurements?.[key];
    addText(list, "dt", label);
    const value = document.createElement("dd");
    value.textContent = formatValue(measurement);
    if (measurement?.observed_at) {
      value.append(document.createTextNode(
        `; время измерения: ${formatObservationTime(measurement.observed_at)}`
      ));
    }
    list.append(value);
  }
  section.append(list);
  addText(section, "p",
    `Источник: ${data.source || "NOAA SWPC"}. Получено сервером: ${formatObservationTime(data.retrieved_at)}`,
    "muted");
  solarReport.append(section);

  if (data.drap) {
    const drap = document.createElement("section");
    drap.className = "result-card";
    addText(drap, "h3", "Поглощение коротких волн в нижней части ионосферы");
    addText(drap, "p", "Модель оценивает, насколько сильно нижние слои ионосферы могут ослаблять КВ-сигналы. Это оценка модели, а не измерение сигнала на твоей антенне.");
    addText(drap, "p", `Влияние солнечного рентгеновского излучения: ${data.drap.xray_message || "Нет данных"}`);
    addText(drap, "p", `Влияние солнечных протонов: ${data.drap.proton_message || "Нет данных"}`);
    addText(drap, "p", `Данные модели обновлены: ${formatObservationTime(data.drap.valid_at)}`);
    addText(drap, "p", `Источник данных: ${data.drap.source}`, "muted");
    solarReport.append(drap);
  }

  if (data.errors && Object.keys(data.errors).length) {
    const errors = document.createElement("section");
    errors.className = "result-card";
    addText(errors, "h3", "Какие источники сейчас недоступны");
    const errorList = document.createElement("ul");
    for (const [name, message] of Object.entries(data.errors)) {
      addText(errorList, "li", `${name}: ${message}`);
    }
    errors.append(errorList);
    solarReport.append(errors);
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
      : "Данные солнечной активности обновлены. Время измерения указано рядом с показателями.";
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
    disabled: "Приём наблюдений отключён",
    idle: "Ожидает открытия раздела радионаблюдений",
    connecting: "Подключается к службе приёма наблюдений",
    connected: "Связь установлена, поступают новые наблюдения",
    reconnecting: "Связь прервалась. Сервис пытается подключиться снова",
    error: "Не удалось получать наблюдения",
    stopped: "Приём наблюдений остановлен",
    not_started: "Приём наблюдений ещё не запускался",
  };
  addText(section, "h3", stateLabels[data.state] || data.state || "Состояние неизвестно");
  const list = document.createElement("dl");
  list.className = "measurements";
  const rows = [
    ["Сервер, откуда поступают наблюдения", data.broker ? `${data.broker}:${data.port}` : "Не указан"],
    ["Тип защищённого соединения", data.transport || "Неизвестно"],
    ["Какие диапазоны и режимы отслеживаются", (data.topic_filters || []).length ? String(data.topic_filters.length) : "Пока ничего не отслеживается"],
    ["Получено сообщений от службы наблюдений", String(data.messages_received ?? 0)],
    ["Найдено новых записей о приёме сигналов", String(data.spots_saved ?? 0)],
    ["Записей сейчас хранится на сервере", String(data.stored_spots ?? 0)],
    ["Повторно получено уже известных записей", String(data.duplicates ?? 0)],
    ["Сообщений, которые не удалось разобрать", String(data.invalid_messages ?? 0)],
    ["Количество ошибок приёма", String(data.errors ?? 0)],
    ["Последнее сообщение от службы наблюдений", data.last_message_at ? formatObservationTime(data.last_message_at) : "Пока не поступало"],
    ["Последняя запись о принятом сигнале", data.last_spot_at ? formatObservationTime(data.last_spot_at) : "Пока не поступала"],
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
      ? "Связь со службой наблюдений установлена. Новые записи могут поступать."
      : data.state === "disabled"
        ? "Приём наблюдений отключён в настройках сервера."
        : "Состояние приёма наблюдений обновлено.";
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

function renderRegionalDirection(parent, title, description, data, roles) {
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

  if (data.latest?.length) {
    addText(section, "h4", "Последние принятые передачи");
    const list = document.createElement("ol");
    list.className = "observation-list";

    for (const item of data.latest) {
      const entry = document.createElement("li");
      addText(entry, "h4", `${item.band} · ${item.mode}`);

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
          ? `${item.station_azimuth} (${item.station_azimuth_degrees}°)`
          : "Неизвестно: нет локатора одной из станций."],
      ];
      if (item.bearing) {
        pathRows.push([
          "Направление от твоего локатора до удалённой станции",
          `${item.bearing} (${item.bearing_degrees}°)`,
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
  } else {
    addText(section, "p", "За выбранный период приёмов в указанном районе нет.");
  }
  parent.append(section);
}

function renderRegionalReport(data) {
  regionalReport.replaceChildren();
  const info = document.createElement("p");
  info.className = "muted";
  info.textContent =
    `Твой локатор: ${data.locator}. Радиус поиска: ${data.radius_km} км. Период: последние ${data.period_hours} ч. Диапазоны: ${(data.bands || []).length ? (data.bands || []).join(", ") : "все"}; режимы: ${(data.modes || []).length ? (data.modes || []).join(", ") : "все"}. В отчёт вошли записи о приёме сигналов, сохранённые к моменту обновления.`;
  regionalReport.append(info);

  renderRegionalDirection(
    regionalReport,
    "Передачи станций рядом с тобой услышали в других местах",
    "Здесь перечислены передачи радиолюбителей из выбранного радиуса вокруг твоего локатора. Их сигналы приняли удалённые станции.",
    data.tx,
    {
      localTitle: "Передатчик рядом с тобой",
      remoteTitle: "Удалённый приёмник",
    }
  );
  renderRegionalDirection(
    regionalReport,
    "Приёмники рядом с тобой услышали станции из других мест",
    "Здесь перечислены удалённые радиолюбители, чьи передачи приняли станции в выбранном радиусе вокруг твоего локатора.",
    data.rx,
    {
      localTitle: "Приёмник рядом с тобой",
      remoteTitle: "Удалённый передатчик",
    }
  );
}
async function loadRegionalReport() {
  regionalRefresh.disabled = true;
  regionalReport.setAttribute("aria-busy", "true");
  regionalStatus.textContent = "Загружаем региональные наблюдения…";
  regionalReport.replaceChildren();
  const params = new URLSearchParams({
    locator: userSettings.locator,
    radius_km: String(userSettings.radiusKm),
    hours: String(userSettings.periodHours || 6),
    limit: "30",
    bands: bandSelection === "all" ? "" : selectedBands.join(","),
    modes: modeSelection === "all" ? "" : selectedModes.join(","),
  });
  try {
    const response = await fetch(`${API}/psk-reporter/regional?${params}`, {
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось получить региональные данные.");
    renderRegionalReport(data);
    regionalStatus.textContent =
      `Отчёт готов. Передачи станций рядом с тобой услышали ${data.tx.spots} раз; приёмники рядом с тобой услышали удалённые станции ${data.rx.spots} раз.`;
  } catch (error) {
    regionalStatus.textContent = error.message;
  } finally {
    regionalRefresh.disabled = false;
    regionalReport.setAttribute("aria-busy", "false");
  }
}

function renderLocal(data, weather, regional, errors = {}) {
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
    `Учитываются радионаблюдения за последние ${regional?.period_hours ?? userSettings.periodHours ?? 6} ч в радиусе ${regional?.radius_km ?? userSettings.radiusKm} км от локатора ${data.locator}. Считаются реальные записи PSK Reporter, а не расчётная вероятность связи.`);
  if (regional) {
    renderLocalBandActivity(activity, regional);
  } else {
    addText(activity, "p", errors.regional || "Пока не удалось получить радионаблюдения.", "muted");
  }
  localReport.append(activity);

  const comparison = document.createElement("section");
  comparison.className = "result-card";
  addText(comparison, "h3", "Солнечная активность и условия прохождения");
  if (weather) {
    const measurements = weather.measurements || {};
    const solarRows = [
      ["Солнечный поток F10.7", formatValue(measurements.solar_flux)],
      ["Геомагнитный индекс Kp", formatValue(measurements.kp)],
      ["Скорость солнечного ветра", formatValue(measurements.solar_wind_speed)],
      ["Межпланетное магнитное поле Bz", formatValue(measurements.magnetic_field_bz)],
      ["Рентгеновское излучение Солнца", formatValue(measurements.xray_flux)],
    ];
    addObservationRows(comparison, solarRows);
    addText(comparison, "p",
      "Эти показатели описывают общие условия в околоземном пространстве. Вместе с освещённостью и оценкой поглощения они помогают понять фоновые условия, но сами по себе не определяют, какой диапазон откроется именно между двумя станциями.");
    addText(comparison, "p", `Солнечные данные получены: ${formatObservationTime(weather.retrieved_at)}`, "muted");
  } else {
    addText(comparison, "p", errors.weather || "Не удалось получить свежие данные солнечной активности.", "muted");
  }
  if (regional) {
    addText(comparison, "p",
      "Сопоставление с радионаблюдениями: диапазоны выше отсортированы по числу зарегистрированных приёмов рядом с твоим локатором. Это фактические подтверждения отдельных приёмов, а не гарантия устойчивой связи.");
  }
  localReport.append(comparison);
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
      "За выбранный период пока нет записей о приёме сигналов рядом с твоим локатором. Если сбор наблюдений только что включился, подожди несколько минут и обнови данные.");
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
  localStatus.textContent = "Собираем данные о Солнце, освещённости и радионаблюдениях…";
  localReport.setAttribute("aria-busy", "true");
  localReport.replaceChildren();
  try {
    const params = new URLSearchParams({
      locator,
      radius_km: String(userSettings.radiusKm),
      hours: String(userSettings.periodHours || 6),
      limit: "100",
      bands: bandSelection === "all" ? "" : selectedBands.join(","),
      modes: modeSelection === "all" ? "" : selectedModes.join(","),
    });
    const requests = await Promise.allSettled([
      fetch(`${API}/local/report?locator=${encodeURIComponent(locator)}`, { cache: "no-store" }).then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Не удалось рассчитать условия для локатора.");
        return data;
      }),
      fetch(`${API}/solar/activity`, { cache: "no-store" }).then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error("Не удалось получить данные солнечной активности.");
        return data;
      }),
      fetch(`${API}/psk-reporter/regional?${params}`, { cache: "no-store" }).then(async response => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Не удалось получить радионаблюдения.");
        return data;
      }),
    ]);
    if (requests[0].status !== "fulfilled") throw requests[0].reason;
    const weather = requests[1].status === "fulfilled" ? requests[1].value : null;
    const regional = requests[2].status === "fulfilled" ? requests[2].value : null;
    renderLocal(requests[0].value, weather, regional, {
      weather: requests[1].status === "rejected" ? requests[1].reason.message : "",
      regional: requests[2].status === "rejected" ? requests[2].reason.message : "",
    });
    const observationCount = regional ? (regional.tx.spots + regional.rx.spots) : null;
    localStatus.textContent = regional
      ? `Отчёт готов. Найдено ${observationCount} записей о приёме за выбранный период. Солнечные данные ${weather ? "получены" : "временно недоступны"}.`
      : "Условия для локатора рассчитаны. Радионаблюдения временно недоступны.";
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
  await loadLocalDashboard(locator);
});

solarButton.addEventListener("click", loadSolar);
void loadSolar();
regionalRefresh.addEventListener("click", loadRegionalReport);
loadSettings();
try {
  const savedFilters = JSON.parse(localStorage.getItem("blindHamPropagationPSKFilters") || "null");
  if (savedFilters && Array.isArray(savedFilters.bands) && Array.isArray(savedFilters.modes)) {
    // New settings preserve independent "all/custom" choices.
    // Older saved settings are restored as custom filters for compatibility.
    bandSelection = savedFilters.bandSelection || "custom";
    modeSelection = savedFilters.modeSelection || "custom";
    selectedBands = bandSelection === "all" ? [...ALL_BANDS] : savedFilters.bands;
    selectedModes = modeSelection === "all" ? [...ALL_MODES] : savedFilters.modes;
    document.querySelector(`input[name="regional-band-selection"][value="${bandSelection}"]`).checked = true;
    document.querySelector(`input[name="regional-mode-selection"][value="${modeSelection}"]`).checked = true;
    for (const input of document.querySelectorAll('input[name="regional-band"]')) input.checked = selectedBands.includes(input.value);
    for (const input of document.querySelectorAll('input[name="regional-mode"]')) input.checked = selectedModes.includes(input.value);
  }
} catch {
  // Use all supported bands and modes by default.
}
updateFilterVisibility();
regionalDescription.textContent =
  `Локатор ${userSettings.locator}; радиус ${userSettings.radiusKm} км; ${filterDescription()}; период: ${userSettings.periodHours || 6} часов.`;
document.querySelectorAll('input[name="regional-band-selection"], input[name="regional-mode-selection"]')
  .forEach((input) => input.addEventListener("change", updateFilterVisibility));
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
      if (document.querySelector("#tab-local").getAttribute("aria-selected") === "true") {
        await loadLocalDashboard(locatorInput.value.trim().toUpperCase());
      } else {
        await loadRegionalReport();
      }
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
