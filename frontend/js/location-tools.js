(() => {
  "use strict";

  const API = "./api/v1";
  const geolocateButton = document.querySelector("#locator-geolocate");
  const addressOpenButton = document.querySelector("#locator-address-open");
  const toolsStatus = document.querySelector("#locator-tools-status");
  const dialog = document.querySelector("#locator-address-dialog");
  const addressForm = document.querySelector("#locator-address-form");
  const addressInput = document.querySelector("#locator-address-query");
  const addressStatus = document.querySelector("#locator-address-status");
  const addressResults = document.querySelector("#locator-address-results");
  const addressMapElement = document.querySelector("#locator-address-map");
  const addressSelected = document.querySelector("#locator-address-selected");
  const addressConfirm = document.querySelector("#locator-address-confirm");
  const addressCancel = document.querySelector("#locator-address-cancel");

  let apiKey = "";
  let ymapsReady = null;
  let addressMap = null;
  let addressMarker = null;
  let selectedAddress = null;
  const maps = new Map();
  const geocodeCache = new Map();
  let geocodeQueue = Promise.resolve();
  let lastGeocodeAt = 0;

  const configReady = fetch(`${API}/config/public`, { cache: "no-store" })
    .then((response) => response.ok ? response.json() : {})
    .then((config) => {
      apiKey = String(config.yandex_maps_api_key || "").trim();
    })
    .catch(() => {
      apiKey = "";
    });

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

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
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
    const city = find("locality") || find("province") || find("area");
    const district = find("district", "subLocality");
    const values = [country, city, district].filter((value, index, all) =>
      value && all.indexOf(value) === index
    );
    return {
      text: values.join(", ") || geoObject?.properties?.get("text") || "Местоположение не определено",
      fullAddress: geoObject?.properties?.get("text") || "",
      precision: metadata.precision || "other",
    };
  }

  function queuedGeocode(query, options = {}) {
    const key = typeof query === "string" ? `address:${query.toLowerCase()}` : `point:${query[0].toFixed(4)},${query[1].toFixed(4)}`;
    if (geocodeCache.has(key)) return geocodeCache.get(key);
    const request = geocodeQueue.then(async () => {
      const wait = Math.max(0, 1000 - (Date.now() - lastGeocodeAt));
      if (wait) await new Promise((resolve) => window.setTimeout(resolve, wait));
      const ymaps = await loadYandex();
      lastGeocodeAt = Date.now();
      const response = await ymaps.geocode(query, { results: options.results || 1 });
      const object = response.geoObjects.get(0);
      if (!object) return null;
      return object;
    });
    geocodeQueue = request.catch(() => null);
    geocodeCache.set(key, request);
    return request;
  }

  function createMap(element, center, zoom = 5) {
    if (!element || !window.ymaps) return null;
    const existing = maps.get(element.id);
    if (existing) {
      existing.destroy();
      maps.delete(element.id);
    }
    element.replaceChildren();
    const map = new window.ymaps.Map(element.id, {
      center,
      zoom,
      controls: ["zoomControl", "typeSelector"],
    }, { suppressMapOpenBlock: true });
    maps.set(element.id, map);
    return map;
  }

  async function addReverseGeocodedPoint(map, locator, label, target) {
    const coordinates = locatorCenter(locator);
    if (!coordinates) return;
    try {
      const geoObject = await queuedGeocode(coordinates);
      if (!geoObject) {
        if (target) target.textContent = "Географическое название не найдено.";
        return;
      }
      const location = extractLocation(geoObject);
      if (target) target.textContent = `Местоположение: ${location.text}.`;
      if (map) {
        const marker = new window.ymaps.Placemark(coordinates, {
          hintContent: `${label}: ${location.text}`,
          balloonContent: `<strong>${escapeHtml(label)}</strong><br>${escapeHtml(location.text)}<br><small>Локатор ${escapeHtml(locator)}</small>`,
        });
        map.geoObjects.add(marker);
      }
    } catch {
      if (target) target.textContent = "Не удалось определить страну, город и район.";
    }
  }

  async function enrichLocalReport(root, data) {
    if (!root || !data?.locator) return;
    try {
      const ymaps = await loadYandex();
      const section = document.createElement("section");
      section.className = "result-card location-result";
      const heading = document.createElement("h3");
      heading.textContent = "Где находится мой локатор";
      const summary = document.createElement("p");
      summary.textContent = "Определяем страну, город и район по центру ячейки локатора…";
      const mapElement = document.createElement("div");
      mapElement.id = "local-yandex-map";
      mapElement.className = "yandex-map";
      mapElement.setAttribute("role", "region");
      mapElement.setAttribute("aria-label", "Карта местоположения моего локатора");
      section.append(heading, summary, mapElement);
      root.prepend(section);
      const map = createMap(mapElement, [data.latitude, data.longitude], 9);
      await addReverseGeocodedPoint(map, data.locator, "Моя станция", summary);
    } catch (error) {
      const section = document.createElement("p");
      section.className = "muted";
      section.textContent = error.message || "Географические названия временно недоступны.";
      root.prepend(section);
    }
  }

  async function enrichRegionalReport(root, data) {
    if (!root || !data) return;
    const points = new Map();
    const qthCoordinates = locatorCenter(data.locator);
    if (qthCoordinates) points.set(data.locator, { locator: data.locator, label: "Твой QTH", coordinates: qthCoordinates });
    const entries = Array.from(root.querySelectorAll(".observation-list > li"));
    for (const entry of entries) {
      const headings = entry.querySelectorAll("h5");
      const lists = entry.querySelectorAll("dl");
      for (let index = 0; index < lists.length; index += 1) {
        const list = lists[index];
        const terms = Array.from(list.querySelectorAll("dt"));
        const locatorTerm = terms.find((term) => term.textContent.trim() === "Локатор");
        if (!locatorTerm) continue;
        const value = locatorTerm.nextElementSibling;
        const locator = value?.textContent.trim().toUpperCase();
        const coordinates = locatorCenter(locator);
        if (!coordinates) continue;
        const label = headings[index]?.textContent || "Станция";
        const locationLine = document.createElement("p");
        locationLine.className = "station-location muted";
        locationLine.textContent = "Определяем страну, город и район…";
        value.insertAdjacentElement("afterend", locationLine);
        if (!points.has(locator)) points.set(locator, { locator, label, coordinates, targets: [] });
        const point = points.get(locator);
        point.targets ||= [];
        point.targets.push(locationLine);
      }
    }
    if (!points.size) return;

    const section = document.createElement("section");
    section.className = "result-card location-result";
    const heading = document.createElement("h3");
    heading.textContent = "География радионаблюдений";
    const note = document.createElement("p");
    note.textContent = "Страна, город и район определяются по центру локатора. Это примерное положение станции, а не точные координаты антенны.";
    const mapElement = document.createElement("div");
    mapElement.id = "regional-yandex-map";
    mapElement.className = "yandex-map";
    mapElement.setAttribute("role", "region");
    mapElement.setAttribute("aria-label", "Карта мест расположения радиостанций");
    section.append(heading, note, mapElement);
    root.insertBefore(section, root.children[1] || null);

    try {
      await loadYandex();
      const map = createMap(mapElement, qthCoordinates || [...points.values()][0].coordinates, 5);
      for (const point of points.values()) {
        const target = point.targets?.[0] || null;
        await addReverseGeocodedPoint(map, point.locator, point.label, target);
        if (point.targets?.length > 1 && target) {
          for (const other of point.targets.slice(1)) other.textContent = target.textContent;
        }
      }
    } catch (error) {
      note.textContent = error.message || "Географические названия временно недоступны.";
      mapElement.remove();
      for (const line of root.querySelectorAll(".station-location")) {
        line.textContent = "Географическое название недоступно.";
      }
    }
  }

  function setLocator(locator, accuracyText) {
    if (typeof window.applyQthLocator === "function") {
      window.applyQthLocator(locator);
    } else {
      const input = document.querySelector("#locator");
      if (input) input.value = locator;
    }
    toolsStatus.textContent = `Определён локатор ${locator}. ${accuracyText}`;
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

  geolocateButton?.addEventListener("click", () => {
    toolsStatus.textContent = "";
    if (!navigator.geolocation) {
      toolsStatus.textContent = "Браузер не поддерживает определение местоположения.";
      return;
    }
    geolocateButton.disabled = true;
    toolsStatus.textContent = "Запрашиваем разрешение на определение местоположения…";
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const { latitude, longitude, accuracy } = position.coords;
        const result = await coordinatesToLocator(latitude, longitude, accuracy);
        const accuracyText = Number.isFinite(accuracy)
          ? `Точность геолокации около ${Math.round(accuracy)} м; выбрано ${result.precision} символов.`
          : `Выбрана точность ${result.precision} символов.`;
        setLocator(result.locator, accuracyText);
      } catch (error) {
        toolsStatus.textContent = error.message;
      } finally {
        geolocateButton.disabled = false;
      }
    }, (error) => {
      const messages = {
        1: "Браузер не получил разрешение на местоположение.",
        2: "Устройство не смогло определить координаты.",
        3: "Истекло время ожидания геолокации.",
      };
      toolsStatus.textContent = messages[error.code] || "Не удалось определить местоположение.";
      geolocateButton.disabled = false;
    }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
  });

  addressOpenButton?.addEventListener("click", async () => {
    try {
      await loadYandex();
      dialog.showModal();
      addressInput.focus();
      addressStatus.textContent = "Введи адрес и нажми «Найти адрес».";
      if (!addressMap) {
        addressMap = createMap(addressMapElement, [59.94, 30.31], 9);
      } else {
        addressMap.container.fitToViewport();
      }
    } catch (error) {
      toolsStatus.textContent = error.message;
    }
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
      const bounds = objects.getBounds();
      if (bounds && addressMap) addressMap.setBounds(bounds, { checkZoomRange: true, zoomMargin: 30 });
      const results = [];
      for (let index = 0; index < objects.getLength(); index += 1) {
        const object = objects.get(index);
        const coordinates = object.geometry.getCoordinates();
        const title = object.properties.get("text") || object.properties.get("name") || `Вариант ${index + 1}`;
        results.push({ object, coordinates, title, metadata: getMetadata(object) });
      }
      for (const [index, result] of results.entries()) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "address-result";
        button.textContent = `${index + 1}. ${result.title}`;
        button.addEventListener("click", () => {
          selectedAddress = result;
          if (addressMarker) addressMap.geoObjects.remove(addressMarker);
          addressMarker = new (window.ymaps.Placemark)(result.coordinates, {
            hintContent: result.title,
            balloonContent: escapeHtml(result.title),
          });
          addressMap.geoObjects.add(addressMarker);
          addressMap.setCenter(result.coordinates, 16);
          addressSelected.textContent = `Выбран адрес: ${result.title}`;
          addressStatus.textContent = "Адрес выбран. Проверь его и нажми «Подтвердить локатор».";
          addressConfirm.disabled = false;
        });
        addressResults.append(button);
      }
      addressStatus.textContent = `Найдено вариантов: ${results.length}. Выбери подходящий адрес.`;
      if (results.length) results[0] && addressResults.querySelector("button")?.focus();
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
      dialog.close();
    } catch (error) {
      addressStatus.textContent = error.message;
      addressConfirm.disabled = false;
    }
  });

  addressCancel?.addEventListener("click", () => dialog.close());
  dialog?.addEventListener("close", () => addressOpenButton?.focus());

  window.locationTools = {
    enrichLocalReport,
    enrichRegionalReport,
  };
})();
