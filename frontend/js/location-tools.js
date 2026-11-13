(() => {
  "use strict";

  const API = "./api/v1";
  const dialog = document.querySelector("#locator-address-dialog");
  const addressForm = document.querySelector("#locator-address-form");
  const addressInput = document.querySelector("#locator-address-query");
  const addressStatus = document.querySelector("#locator-address-status");
  const addressResults = document.querySelector("#locator-address-results");
  const addressSelected = document.querySelector("#locator-address-selected");
  const addressConfirm = document.querySelector("#locator-address-confirm");
  const addressCancel = document.querySelector("#locator-address-cancel");

  let apiKey = "";
  let ymapsReady = null;
  let selectedAddress = null;
  let activeLocatorInput = null;
  let activeStatus = null;
  let activeTrigger = null;
  let confirmedAddress = false;
  const geocodeCache = new Map();
  let geocodeQueue = Promise.resolve();
  let lastGeocodeAt = 0;

  const configReady = fetch(`${API}/config/public`, { cache: "no-store" })
    .then((response) => response.ok ? response.json() : {})
    .then((config) => { apiKey = String(config.yandex_maps_api_key || "").trim(); })
    .catch(() => { apiKey = ""; });

  function loadYandex() {
    if (ymapsReady) return ymapsReady;
    ymapsReady = configReady.then(() => {
      if (!apiKey) throw new Error("Не задан ключ JavaScript API Яндекс Карт в settings.ini.");
      if (window.ymaps) {
        return new Promise((resolve) => window.ymaps.ready(() => resolve(window.ymaps)));
      }
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(apiKey)}&lang=ru_RU`;
        script.async = true;
        script.onload = () => window.ymaps.ready(() => resolve(window.ymaps));
        script.onerror = () => reject(new Error("Не удалось загрузить JavaScript API Яндекс Карт."));
        document.head.append(script);
      });
    });
    return ymapsReady;
  }

  function getMetadata(geoObject) {
    return geoObject?.properties?.get("metaDataProperty.GeocoderMetaData") || {};
  }

  function extractLocation(geoObject) {
    const metadata = getMetadata(geoObject);
    const components = metadata.Address?.Components || [];
    const find = (...kinds) => {
      const component = components.find((item) => kinds.includes(item.kind));
      return component?.name || "";
    };
    const country = find("country");
    // "province" and "area" are administrative regions, not cities.
    // Only Yandex's locality component is presented as a city/town.
    const city = find("locality");
    const region = find("province") || find("area");
    // subLocality is an urban district. Administrative regions are labelled separately.
    const cityDistrict = find("subLocality");
    const labels = [];
    if (country) labels.push(`Страна: ${country}`);
    if (region) labels.push(`Регион: ${region}`);
    if (city) labels.push(`Город/населённый пункт: ${city}`);
    if (cityDistrict) labels.push(`Район города: ${cityDistrict}`);
    if (!city) labels.push("Город или населённый пункт не определён");
    return {
      text: labels.join("; ") || "Географическое название не найдено",
      fullAddress: geoObject?.properties?.get("text") || "",
      precision: metadata.precision || "other",
    };
  }

  function queuedGeocode(query, options = {}) {
    const key = `point:${query[0].toFixed(4)},${query[1].toFixed(4)}`;
    if (geocodeCache.has(key)) return geocodeCache.get(key);
    const request = geocodeQueue.then(async () => {
      const wait = Math.max(0, 1000 - (Date.now() - lastGeocodeAt));
      if (wait) await new Promise((resolve) => window.setTimeout(resolve, wait));
      const ymaps = await loadYandex();
      lastGeocodeAt = Date.now();
      const response = await ymaps.geocode(query, { results: options.results || 1 });
      return response.geoObjects.get(0) || null;
    });
    geocodeQueue = request.catch(() => null);
    geocodeCache.set(key, request);
    return request;
  }

  function locatorCenter(locator) {
    const value = String(locator || "").trim().toUpperCase();
    if (![2, 4, 6, 8, 10, 12].includes(value.length)) return null;
    let lon = -180;
    let lat = -90;
    let lonSize = 360;
    let latSize = 180;
    for (let pair = 0; pair < value.length / 2; pair += 1) {
      const first = value[pair * 2];
      const second = value[pair * 2 + 1];
      const divisor = pair === 0 ? 18 : (pair % 2 ? 10 : 24);
      let lonIndex;
      let latIndex;
      if (pair % 2 === 0) {
        lonIndex = first.charCodeAt(0) - 65;
        latIndex = second.charCodeAt(0) - 65;
        if (lonIndex < 0 || latIndex < 0 || lonIndex >= divisor || latIndex >= divisor) return null;
      } else {
        if (!/^\d$/.test(first) || !/^\d$/.test(second)) return null;
        lonIndex = Number(first);
        latIndex = Number(second);
      }
      lonSize /= divisor;
      latSize /= divisor;
      lon += lonIndex * lonSize;
      lat += latIndex * latSize;
    }
    return [lat + latSize / 2, lon + lonSize / 2];
  }

  async function enrichPoint(locator, target) {
    const coordinates = locatorCenter(locator);
    if (!coordinates || !target) return;
    try {
      const geoObject = await queuedGeocode(coordinates);
      if (!geoObject) {
        target.textContent = "Географическое название не найдено.";
        return;
      }
      const location = extractLocation(geoObject);
      target.textContent = `Местоположение: ${location.text}. Это примерное положение центра ячейки локатора, а не точные координаты антенны.`;
    } catch {
      target.textContent = "Не удалось определить географическое название.";
    }
  }

  async function enrichLocalReport(root, data) {
    if (!root || !data?.locator) return;
    const section = document.createElement("section");
    section.className = "result-card location-result";
    const heading = document.createElement("h3");
    heading.textContent = "Где находится мой локатор";
    const summary = document.createElement("p");
    summary.textContent = "Определяем страну, город и район по центру ячейки локатора…";
    section.append(heading, summary);
    root.prepend(section);
    await enrichPoint(data.locator, summary);
  }

  async function enrichRegionalReport(root, data) {
    if (!root || !data) return;
    const points = new Map();
    const qthCoordinates = locatorCenter(data.locator);
    if (qthCoordinates) points.set(data.locator, { locator: data.locator, targets: [] });
    const entries = Array.from(root.querySelectorAll(".observation-list > li"));
    for (const entry of entries) {
      const lists = entry.querySelectorAll("dl");
      for (const list of lists) {
        const terms = Array.from(list.querySelectorAll("dt"));
        const locatorTerm = terms.find((term) => term.textContent.trim() === "Локатор");
        if (!locatorTerm) continue;
        const value = locatorTerm.nextElementSibling;
        const locator = value?.textContent.trim().toUpperCase();
        if (!locatorCenter(locator)) continue;
        const locationLine = document.createElement("p");
        locationLine.className = "station-location muted";
        locationLine.textContent = "Определяем страну, город и район…";
        value.insertAdjacentElement("afterend", locationLine);
        if (!points.has(locator)) points.set(locator, { locator, targets: [] });
        points.get(locator).targets.push(locationLine);
      }
    }
    if (!points.size) return;

    const section = document.createElement("section");
    section.className = "result-card location-result";
    const heading = document.createElement("h3");
    heading.textContent = "География радионаблюдений";
    const note = document.createElement("p");
    note.textContent = "Местоположение определяется по центру ячейки локатора. Это примерное положение станции, а не точные координаты антенны.";
    const qthLine = document.createElement("p");
    qthLine.className = "station-location muted";
    if (qthCoordinates) qthLine.textContent = "Определяем местоположение твоего QTH…";
    section.append(heading, note);
    if (qthCoordinates) section.append(qthLine);
    root.insertBefore(section, root.children[1] || null);

    try {
      await loadYandex();
      for (const point of points.values()) {
        const target = point.targets[0] || (point.locator === data.locator ? qthLine : null);
        await enrichPoint(point.locator, target);
        if (point.targets.length > 1 && target) {
          for (const other of point.targets.slice(1)) other.textContent = target.textContent;
        }
      }
    } catch {
      note.textContent = "Географические названия временно недоступны.";
      for (const line of root.querySelectorAll(".station-location")) {
        line.textContent = "Географическое название недоступно.";
      }
    }
  }

  async function coordinatesToLocator(latitude, longitude, accuracy) {
    const response = await fetch(`${API}/locator/from-coordinates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        latitude,
        longitude,
        accuracy_m: Number.isFinite(accuracy) && accuracy > 0 ? accuracy : null,
      }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось вычислить Maidenhead-локатор.");
    return data;
  }

  function setLocator(locator, accuracyText) {
    if (typeof window.applyQthLocator === "function") {
      window.applyQthLocator(locator);
    } else if (activeLocatorInput) {
      activeLocatorInput.value = locator;
    }
    if (activeStatus) activeStatus.textContent = `Определён локатор ${locator}. ${accuracyText}`;
    if (activeLocatorInput) {
      activeLocatorInput.value = locator;
      activeLocatorInput.focus();
    }
  }

  function getLocatorInput(button) {
    return document.querySelector(button.dataset.locatorTarget || "#locator");
  }

  function getStatus(button) {
    return document.querySelector(button.dataset.statusTarget || "#locator-tools-status");
  }

  document.querySelectorAll("[data-locator-geolocate]").forEach((button) => {
    button.addEventListener("click", () => {
      activeLocatorInput = getLocatorInput(button);
      activeStatus = getStatus(button);
      activeTrigger = button;
      if (activeStatus) activeStatus.textContent = "";
      if (!navigator.geolocation) {
        if (activeStatus) activeStatus.textContent = "Браузер не поддерживает определение местоположения.";
        return;
      }
      button.disabled = true;
      if (activeStatus) activeStatus.textContent = "Запрашиваем разрешение на определение местоположения…";
      navigator.geolocation.getCurrentPosition(async (position) => {
        try {
          const { latitude, longitude, accuracy } = position.coords;
          const result = await coordinatesToLocator(latitude, longitude, accuracy);
          const accuracyText = Number.isFinite(accuracy)
            ? `Точность геолокации около ${Math.round(accuracy)} м; выбрано ${result.precision} символов.`
            : `Выбрана точность ${result.precision} символов.`;
          setLocator(result.locator, accuracyText);
        } catch (error) {
          if (activeStatus) activeStatus.textContent = error.message;
        } finally {
          button.disabled = false;
        }
      }, (error) => {
        const messages = {
          1: "Браузер не получил разрешение на местоположение.",
          2: "Устройство не смогло определить координаты.",
          3: "Истекло время ожидания геолокации.",
        };
        if (activeStatus) activeStatus.textContent = messages[error.code] || "Не удалось определить местоположение.";
        button.disabled = false;
      }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
    });
  });

  document.querySelectorAll("[data-locator-address]").forEach((button) => {
    button.addEventListener("click", async () => {
      activeLocatorInput = getLocatorInput(button);
      activeStatus = getStatus(button);
      activeTrigger = button;
      confirmedAddress = false;
      selectedAddress = null;
      addressResults.replaceChildren();
      addressSelected.textContent = "";
      addressConfirm.disabled = true;
      try {
        if (activeStatus) activeStatus.textContent = "Подключаем поиск адресов…";
        await loadYandex();
        addressInput.value = "";
        addressStatus.textContent = "Введи адрес и нажми «Найти адрес».";
        if (activeStatus) activeStatus.textContent = "";
        dialog.showModal();
        addressInput.focus();
      } catch (error) {
        if (activeStatus) activeStatus.textContent = error.message;
      }
    });
  });

  addressForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = addressInput.value.trim();
    if (!query) {
      addressStatus.textContent = "Введи адрес или его часть.";
      addressInput.focus();
      return;
    }
    const searchButton = document.querySelector("#locator-address-search");
    searchButton.disabled = true;
    addressStatus.textContent = "Ищем адрес…";
    addressResults.replaceChildren();
    selectedAddress = null;
    addressConfirm.disabled = true;
    addressSelected.textContent = "";
    try {
      const response = await (await loadYandex()).geocode(query, { results: 5 });
      const objects = response.geoObjects;
      if (!objects.getLength()) {
        addressStatus.textContent = "По этому запросу ничего не найдено. Уточни адрес.";
        return;
      }
      for (let index = 0; index < objects.getLength(); index += 1) {
        const object = objects.get(index);
        const result = {
          coordinates: object.geometry.getCoordinates(),
          title: object.properties.get("text") || object.properties.get("name") || `Вариант ${index + 1}`,
          metadata: getMetadata(object),
        };
        const option = document.createElement("button");
        option.type = "button";
        option.className = "address-result";
        option.textContent = `${index + 1}. ${result.title}`;
        option.setAttribute("aria-pressed", "false");
        option.addEventListener("click", () => {
          selectedAddress = result;
          addressResults.querySelectorAll("button").forEach((item) => {
            item.setAttribute("aria-pressed", String(item === option));
          });
          addressSelected.textContent = `Выбран адрес: ${result.title}`;
          addressStatus.textContent = "Адрес выбран. Нажми «Подтвердить локатор».";
          addressConfirm.disabled = false;
        });
        addressResults.append(option);
      }
      addressStatus.textContent = `Найдено вариантов: ${objects.getLength()}. Выбери подходящий адрес.`;
      addressResults.querySelector("button")?.focus();
    } catch (error) {
      addressStatus.textContent = error.message || "Не удалось выполнить поиск адреса.";
    } finally {
      searchButton.disabled = false;
    }
  });

  addressConfirm?.addEventListener("click", async () => {
    if (!selectedAddress) return;
    addressConfirm.disabled = true;
    addressStatus.textContent = "Вычисляем локатор…";
    try {
      const precision = selectedAddress.metadata.precision || "other";
      const accuracy = ["exact", "number"].includes(precision) ? 10
        : precision === "street" ? 100
          : 5000;
      const [latitude, longitude] = selectedAddress.coordinates;
      const result = await coordinatesToLocator(latitude, longitude, accuracy);
      setLocator(result.locator, `Адресная точка: ${selectedAddress.title}. Расчётная точность координат — около ${accuracy} м; локатор содержит ${result.precision} символов.`);
      confirmedAddress = true;
      dialog.close();
    } catch (error) {
      addressStatus.textContent = error.message;
      addressConfirm.disabled = false;
    }
  });

  addressCancel?.addEventListener("click", () => dialog.close());
  dialog?.addEventListener("close", () => {
    if (confirmedAddress && activeLocatorInput) activeLocatorInput.focus();
    else activeTrigger?.focus();
  });

  window.locationTools = { enrichLocalReport, enrichRegionalReport };
})();
