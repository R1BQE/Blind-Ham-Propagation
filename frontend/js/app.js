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
