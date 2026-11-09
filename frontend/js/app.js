const form = document.querySelector("#locator-form");
const input = document.querySelector("#locator");
const error = document.querySelector("#locator-error");
const result = document.querySelector("#locator-result");
const submitButton = document.querySelector("#submit-button");
const serviceStatus = document.querySelector("#service-status");

function showError(message) {
  error.textContent = message;
  result.replaceChildren();
}

function showLocator(data) {
  const card = document.createElement("div");
  card.className = "result-card";

  const heading = document.createElement("h3");
  heading.textContent = "Локатор распознан";

  const locator = document.createElement("p");
  locator.textContent = `QTH: ${data.locator}`;

  const coordinates = document.createElement("p");
  coordinates.textContent =
    `Центр квадрата: широта ${data.latitude.toFixed(4)}°, ` +
    `долгота ${data.longitude.toFixed(4)}°.`;

  card.append(heading, locator, coordinates);
  result.replaceChildren(card);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  error.textContent = "";
  result.replaceChildren();

  const locator = input.value.trim().toUpperCase();
  if (!locator) {
    showError("Введи QTH-локатор.");
    input.focus();
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Проверяем…";

  try {
    const response = await fetch("./api/v1/locator/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ locator }),
    });
    const data = await response.json();

    if (!response.ok) {
      const detail = typeof data.detail === "string"
        ? data.detail
        : "Не удалось проверить локатор.";
      showError(detail);
      return;
    }

    showLocator(data);
  } catch {
    showError("Не удалось связаться с сервером. Проверь подключение и повтори попытку.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Проверить локатор";
  }
});

async function checkService() {
  try {
    const response = await fetch("./api/v1/health", { cache: "no-store" });
    if (!response.ok) throw new Error("Service unavailable");
    serviceStatus.textContent = "Сервер приложения доступен.";
  } catch {
    serviceStatus.textContent = "Не удалось проверить сервер приложения.";
  }
}

checkService();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js", { scope: "./" }).catch(() => {
      // The service remains usable in the browser if PWA installation is unavailable.
    });
  });
}
