(() => {
  "use strict";

  const hintsControl = document.querySelector("#solar-show-hints");

  const translations = {
    "Poor": "Плохо",
    "Fair": "Средне",
    "Good": "Хорошо",
    "Excellent": "Отлично",
    "Band Closed": "Закрыт",
    "Band Open": "Открыт",
    "VR QUIET": "Очень спокойно",
    "QUIET": "Спокойно",
    "UNSETTLED": "Неустойчиво",
    "ACTIVE": "Активно",
    "MINOR STORM": "Небольшая магнитная буря",
    "MAJOR STORM": "Сильная магнитная буря",
    "SEVERE STORM": "Очень сильная магнитная буря",
    "NoRpt": "Нет отчёта",
    "No Report": "Нет отчёта"
  };

  const indexDefinitions = [
    ["solarflux", "Солнечный поток F10.7", "Показывает радиоизлучение Солнца на длине волны 10,7 см. Это один из показателей, по которым оценивают состояние ионосферы. Более высокие значения часто помогают работе на верхних КВ-диапазонах, но сами по себе не гарантируют хорошего прохождения."],
    ["sunspots", "Солнечные пятна", "Количество видимых групп и пятен на Солнце. Это ещё один показатель солнечной активности. По одному этому числу нельзя точно определить, будет ли открыта конкретная трасса."],
    ["aindex", "Индекс A", "Показывает усреднённую геомагнитную активность за сутки. Чем меньше значение, тем спокойнее в среднем было магнитное поле Земли."],
    ["kindex", "Индекс K", "Оценивает возмущение магнитного поля за последние три часа. Низкие значения обычно соответствуют более спокойной геомагнитной обстановке."],
    ["xray", "Рентгеновское излучение", "Сильные вспышки увеличивают ионизацию нижней части ионосферы на освещённой стороне Земли. Это может усиливать поглощение КВ-сигналов, особенно на нижних диапазонах."],
    ["magneticfield", "Межпланетное магнитное поле Bz", "Показывает направление одной из составляющих магнитного поля солнечного ветра. Отрицательное Bz может облегчать передачу энергии от солнечного ветра магнитосфере Земли и усиливать возмущения. Важны также сила поля и длительность такого состояния."],
    ["solarwind", "Скорость солнечного ветра", "Скорость потока заряженных частиц от Солнца. Высокая скорость сама по себе ещё не означает магнитную бурю: важны также направление и сила межпланетного магнитного поля."],
    ["protonflux", "Поток солнечных протонов", "Показывает количество быстрых протонов. Во время сильных солнечных событий они могут вызывать поглощение радиоволн в полярных областях Земли."],
    ["electonflux", "Поток электронов", "Показатель потока электронов высокой энергии. Он помогает следить за радиационной обстановкой около Земли. Это не прямое измерение уровня шума на твоём приёмнике."],
    ["heliumline", "Линия гелия", "Показатель излучения Солнца в линии гелия. Он связан с ультрафиолетовой активностью Солнца и используется как дополнительный индикатор состояния ионосферы."],
    ["aurora", "Индекс авроры", "Оценка активности полярных сияний. Сильная авроральная активность может затруднять обычную КВ-связь на трассах через полярные широты, но иногда позволяет проводить специальные связи отражением от сияния."],
    ["latdegree", "Широта границы аврорального овала", "Показывает положение границы области полярных сияний в геомагнитных широтах. Если граница смещается к югу, авроральные явления могут затрагивать более низкие широты."],
    ["geomagfield", "Состояние магнитного поля Земли", "Сводная текстовая оценка геомагнитной обстановки от HamQSL."],
    ["signalnoise", "Оценка уровня радиошума", "Текстовая оценка фонового радиошума, переданная источником. Это не измерение шума непосредственно на твоей антенне."],
    ["muf", "MUF — максимально применимая частота", "Оценка самой высокой частоты, которая может вернуться к Земле при заданных условиях распространения. HamQSL передаёт это значение без однозначного указания точки расчёта в данном ответе, поэтому его нельзя считать MUF именно для локатора KP50DB."]
  ];

  const vhfNames = {
    "vhf-aurora": "Авроральное прохождение",
    "E-Skip": "Спорадический слой E",
    "northern_hemi": "Северное полушарие",
    "europe": "Европа",
    "north_america": "Северная Америка",
    "europe_6m": "Европа, диапазон 50 МГц (6 метров)",
    "europe_4m": "Европа, диапазон 70 МГц (4 метра)"
  };

  function element(parent, tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    parent.append(node);
    return node;
  }

  function xmlText(value) {
    if (value === undefined || value === null) return "";
    if (Array.isArray(value)) return xmlText(value[0]);
    if (typeof value === "object") return xmlText(value["#text"]);
    return String(value).trim();
  }

  function xmlRows(value) {
    if (value === undefined || value === null) return [];
    return Array.isArray(value) ? value : [value];
  }

  function displayValue(value, suffix = "") {
    const text = xmlText(value);
    if (!text || text === "NoRpt" || text === "No Report") return "Нет данных";
    return `${translations[text] || text}${suffix}`;
  }

  function help(parent, text) {
    const node = element(parent, "p", text, "solar-help muted");
    node.hidden = !hintsControl?.checked;
  }

  function formatUpdated(value) {
    const raw = xmlText(value);
    if (!raw) return "время обновления не указано";
    return raw.replace(/(\\d{2})(\\d{2}) GMT$/, "$1:$2 GMT");
  }

  function numeric(value) {
    const match = xmlText(value).replace(",", ".").match(/-?\\d+(?:\\.\\d+)?/);
    return match ? Number(match[0]) : null;
  }

  function renderIndexes(parent, solarData) {
    const section = element(parent, "section", undefined, "result-card");
    element(section, "h3", "Солнечные и геомагнитные показатели");
    element(section, "p",
      "Это данные HamQSL. Под каждым показателем есть короткое пояснение. Если пояснения мешают, их можно скрыть переключателем выше.",
      "muted");

    const list = element(section, "dl", undefined, "measurements solar-measurements");
    for (const [tag, title, explanation] of indexDefinitions) {
      element(list, "dt", title);
      const value = element(list, "dd");
      let shown = displayValue(solarData[tag]);
      if (tag === "latdegree" && shown !== "Нет данных") shown += "°";
      if (tag === "solarwind" && shown !== "Нет данных") shown += " км/с";
      if (tag === "xray" && shown !== "Нет данных") {
        // The source already supplies the flare class, for example C1.2.
      }
      if (tag === "kindex" && shown !== "Нет данных") {
        const k = numeric(solarData[tag]);
        const state = k === null ? "" : k <= 1 ? " — очень спокойно" : k <= 3 ? " — спокойно" : k === 4 ? " — неустойчиво" : " — магнитная буря";
        shown += state;
      }
      value.textContent = shown;
      help(value, explanation);
    }
    const updated = element(section, "p",
      `Время обновления по HamQSL: ${formatUpdated(solarData.updated)}. Время получения сервером показывается отдельно.`,
      "muted");
    updated.setAttribute("aria-label", updated.textContent);
    return section;
  }

  function renderBands(parent, solarData) {
    const rows = xmlRows(solarData.calculatedconditions?.band);
    const section = element(parent, "section", undefined, "result-card");
    element(section, "h3", "Оценка прохождения на КВ");
    element(section, "p",
      "HamQSL отдельно оценивает условия для дневного и ночного времени. Это общая оценка источника, а не гарантия связи между двумя конкретными станциями.",
      "muted");

    if (!rows.length) {
      element(section, "p", "Источник не передал таблицу условий по КВ.");
      return;
    }

    const bands = new Map();
    for (const row of rows) {
      if (!row || typeof row !== "object") continue;
      const name = row["@name"] || "Диапазон без названия";
      const time = String(row["@time"] || "").toLowerCase();
      if (!bands.has(name)) bands.set(name, { day: "Нет данных", night: "Нет данных" });
      if (time === "day") bands.get(name).day = displayValue(row);
      if (time === "night") bands.get(name).night = displayValue(row);
    }

    const table = element(section, "table", undefined, "data-table");
    element(table, "caption", "Условия прохождения по диапазонам, оценка HamQSL");
    const head = element(table, "thead");
    const header = element(head, "tr");
    for (const label of ["Диапазон", "Днём", "Ночью"]) {
      const th = element(header, "th", label);
      th.scope = "col";
    }
    const body = element(table, "tbody");
    for (const [name, values] of bands) {
      const tr = element(body, "tr");
      element(tr, "th", name.toUpperCase()).scope = "row";
      element(tr, "td", values.day);
      element(tr, "td", values.night);
    }
  }

  function renderVhf(parent, solarData) {
    const rows = xmlRows(solarData.calculatedvhfconditions?.phenomenon);
    const section = element(parent, "section", undefined, "result-card");
    element(section, "h3", "Условия для УКВ");
    element(section, "p",
      "Здесь показаны оценки отдельных механизмов дальнего УКВ-прохождения. Они не означают, что связь гарантированно состоится.",
      "muted");
    if (!rows.length) {
      element(section, "p", "Источник не передал данные об УКВ-условиях.");
      return;
    }

    const list = element(section, "ul", undefined, "solar-vhf-list");
    for (const row of rows) {
      if (!row || typeof row !== "object") continue;
      const name = vhfNames[row["@name"]] || row["@name"] || "Явление";
      const location = vhfNames[row["@location"]] || row["@location"] || "Регион не указан";
      const item = element(list, "li");
      element(item, "strong", `${name}. Регион: ${location}. Статус: ${displayValue(row)}.`);
      help(item, "Спорадический слой E и авроральное прохождение могут позволять проводить УКВ-связи дальше обычной прямой видимости. Условия быстро меняются.");
    }
  }

  function renderComparison(parent, solarData, noaa) {
    const pairs = [
      ["Солнечный поток F10.7", solarData.solarflux, noaa.solar_flux],
      ["Индекс K", solarData.kindex, noaa.kp],
      ["Скорость солнечного ветра", solarData.solarwind, noaa.solar_wind_speed],
      ["Магнитное поле Bz", solarData.magneticfield, noaa.magnetic_field_bz]
    ].filter(([, ham, other]) => xmlText(ham) && other && other.value !== null && other.value !== undefined);

    if (!pairs.length) return;
    const section = element(parent, "section", undefined, "result-card");
    element(section, "h3", "Сверка HamQSL и NOAA");
    element(section, "p",
      "Здесь рядом показаны совпадающие показатели двух источников. Разница не означает автоматически, что один источник ошибается: время измерения и усреднение могут отличаться.",
      "muted");
    const table = element(section, "table", undefined, "data-table");
    element(table, "caption", "Сравнение значений без усреднения");
    const head = element(table, "thead");
    const trHead = element(head, "tr");
    for (const label of ["Показатель", "HamQSL", "NOAA"]) {
      element(trHead, "th", label).scope = "col";
    }
    const body = element(table, "tbody");
    for (const [label, ham, noaaValue] of pairs) {
      const tr = element(body, "tr");
      element(tr, "th", label).scope = "row";
      element(tr, "td", xmlText(ham));
      element(tr, "td", `${noaaValue.value} ${noaaValue.unit || ""}`.trim());
    }
  }

  function renderMonitor(payload, noaaMeasurements, target) {
    const solarData = payload?.data?.solardata;
    if (!solarData || typeof solarData !== "object") {
      const error = element(target, "section", undefined, "result-card");
      element(error, "h3", "HamQSL не передал данные");
      element(error, "p", "Ответ источника получен, но в нём не найдена секция solardata.");
      return;
    }

    const intro = element(target, "section", undefined, "result-card");
    element(intro, "h3", "Монитор радиопрохождения HamQSL");
    element(intro, "p",
      "Ниже перенесены показатели и таблицы из прежнего монитора. Значения передаются источником HamQSL; сервис не подменяет их собственными догадками.",
      "muted");
    element(intro, "p",
      `Данные источника обновлены: ${formatUpdated(solarData.updated)}. Получены сервером: ${payload.retrieved_at || "время не указано"}.`);
    if (payload.cache?.hit) {
      element(intro, "p", "Ответ взят из серверного кэша. Обновление источника запрашивается не чаще одного раза в 15 минут.", "muted");
    }

    renderIndexes(target, solarData);
    renderComparison(target, solarData, noaaMeasurements || {});
    renderBands(target, solarData);
    renderVhf(target, solarData);
  }

  if (hintsControl) {
    hintsControl.addEventListener("change", () => {
      document.querySelectorAll(".solar-help").forEach((node) => {
        node.hidden = !hintsControl.checked;
      });
    });
  }

  window.renderHamqslMonitor = renderMonitor;
})();
