(() => {
  "use strict";
  const hints = document.querySelector("#solar-show-hints");
  const translations = {"Poor":"Плохо","Fair":"Средне","Good":"Хорошо","Excellent":"Отлично","Band Closed":"Закрыт","Band Open":"Открыт","VR QUIET":"Очень спокойно","QUIET":"Спокойно","UNSETTLED":"Неустойчиво","UNSETTLD":"Неустойчиво","ACTIVE":"Активно","MINOR STORM":"Небольшая магнитная буря","MAJOR STORM":"Сильная магнитная буря","SEVERE STORM":"Очень сильная магнитная буря","NoRpt":"Нет отчёта","No Report":"Нет отчёта"};
  const definitions = [
    ["solarflux","SFI — солнечный поток F10.7","Индекс солнечного потока на длине волны 10,7 см. Отражает общую активность Солнца и степень ионизации ионосферы. До 70: минимум цикла, высокие диапазоны закрыты. 70–100: низкая активность, в основном работают 40 и 80 метров. 100–150: умеренная активность, открываются 20 и 15 метров. 150–200: высокая активность, 10 метров работает хорошо. Выше 200: пик цикла, возможно прохождение через слой F2 на 6 метрах."],
    ["sunspots","Число Вольфа (солнечные пятна)","Количество солнечных пятен на диске Солнца. 0–10: минимум цикла, высокие диапазоны почти закрыты. 10–50: низкая активность. 50–100: умеренная активность, открываются 20 и 17 метров. 100–150: хорошая активность, работают 15 и 10 метров. Выше 150: высокая активность, пик цикла."],
    ["aindex","A-индекс","Планетарный индекс геомагнитной активности за последние 24 часа. 0–7: спокойно, прохождение обычно не страдает. 8–15: слабые возмущения, возможно небольшое ухудшение на полярных трассах. 16–29: умеренная буря, заметное ухудшение на 80 и 160 метрах. 30–49: сильная буря, прохождение на КВ серьёзно нарушено. 50 и выше: экстремальная буря, связь на многих диапазонах может быть невозможна."],
    ["kindex","K-индекс","Текущий индекс геомагнитной активности по шкале от 0 до 9, обновляется раз в три часа. 0–1: спокойно, отличные условия. 2–3: небольшие возмущения, обычно без заметного влияния на прохождение. 4: неустойчиво, возможно лёгкое ухудшение. 5: малая магнитная буря, ухудшение на высоких широтах. 6–7: умеренная буря, серьёзные нарушения на 80 и 160 метрах и полярных трассах. 8–9: сильная буря, КВ-связь может быть почти невозможна."],
    ["xray","Рентгеновское излучение Солнца","Класс A: фоновый уровень, влияния на радиосвязь практически нет. Класс B: низкая активность, заметного влияния нет. Класс C: слабая вспышка, небольшое поглощение на дневной стороне Земли. Класс M: умеренная вспышка, заметное поглощение КВ-сигналов на дневной стороне примерно на 1–2 часа. Класс X: мощная вспышка, возможен полный радиоблэкаут на дневной стороне на несколько часов. X5 и выше: экстремальная вспышка, блэкаут может продолжаться весь световой день."],
    ["bz","Межпланетное магнитное поле Bz (NOAA)","Z-компонента межпланетного магнитного поля в нанотеслах. Положительные значения (северное направление): магнитный щит Земли держится, вероятность бури ниже. От 0 до −5: слабое южное поле. От −5 до −10: возможна слабая буря. От −10 до −20: вероятна буря уровня K5–K6. Ниже −20: высокая вероятность сильной бури. Чем дольше сохраняется отрицательный Bz, тем сильнее может быть воздействие."],
    ["solarwind","Солнечный ветер","Скорость потока частиц от Солнца. 300–400 км/с: фоновый уровень, спокойно. 400–500: обычная скорость. 500–600: повышенная скорость, при отрицательном Bz возможны возмущения. 600–800: высокая скорость, при отрицательном Bz риск магнитной бури заметно растёт. Выше 800: очень высокая скорость; при отрицательном Bz вероятность бури особенно велика."],
    ["protonflux","Поток протонов","Поток протонов высоких энергий от Солнца. Ниже 1 pfu: фоновый уровень. 1–10: немного повышен, обычно без угрозы. Выше 10: NOAA объявляет протонное событие. Выше 100: сильное событие, возможно поглощение КВ-сигналов в полярных областях. Выше 1000: экстремальное событие, поглощение на трансполярных трассах может сохраняться несколько дней."],
    ["electonflux","Поток электронов","Поток релятивистских электронов в магнитосфере Земли. Ниже 100 pfu: обычный уровень. 100–1000: повышенный уровень, часто сопровождает геомагнитную активность. 1000–10000: высокий уровень, характерный для периода после бурь. Выше 10000: экстремальный уровень, опасный для электроники спутников. Для КВ напрямую не критичен, но может указывать на усиление авроральной активности и ухудшение прохождения на полярных трассах."],
    ["heliumline","Линия гелия 304 Å","Интенсивность ультрафиолетового излучения Солнца в линии ионизованного гелия, в условных единицах. Ниже 80: низкая активность и слабая ионизация ионосферы. 80–120: умеренная активность. 120–160: высокая активность, хорошая ионизация и плотный слой F2. Выше 160: очень высокая активность. Показатель используют вместе с SFI для оценки условий прохождения и MUF."],
    ["aurora","Индекс авроральной активности","1–3: слабая активность, сияния в основном у полюсов. 4–5: умеренная активность, аврора достигает широт выше 65°. 6–7: сильная активность, аврора может достигать 60–62°; Санкт-Петербург оказывается в зоне влияния. 8–9: очень сильная активность, зона может смещаться до 55–57°. 10: экстремальная активность. При значениях от 6 возможно авроральное рассеяние на УКВ, но КВ-прохождение на полярных трассах серьёзно ухудшается."],
    ["latdegree","Геомагнитная широта авроральной зоны","Показывает, до какой геомагнитной широты доходят авроральные возмущения. Выше 70°: аврора только у полюсов. 65–70°: влияние на субполярные трассы. 60–65°: в зону влияния могут попадать Санкт-Петербург и Скандинавия. Ниже 60°: возмущения достигают средних широт. Ниже 50°: экстремальная ситуация, аврора может наблюдаться в значительной части Европы."],
    ["geomagfield","Геомагнитное поле","Словесная оценка состояния магнитного поля Земли на основе K-индекса. QUIET: K 0–1, отличные условия. UNSETTLD: K 2–3, небольшие возмущения. ACTIVE: K 4, возможно лёгкое ухудшение. MINOR STORM: K 5, заметное ухудшение на высоких широтах. MAJOR STORM: K 6–7, серьёзные нарушения КВ-связи. SEVERE STORM: K 8–9, связь на многих диапазонах может быть невозможна."],
    ["signalnoise","Уровень радиошума","Оценка атмосферных и ионосферных шумов на КВ по шкале S. S0: шума почти нет, удобно принимать слабые сигналы. S1–S2: низкий шум, хорошие условия. S3–S4: умеренный шум, слабые станции различать труднее. S5–S6: высокий шум, работа со слабыми корреспондентами затруднена. S7 и выше: сильный шум, уверенно слышны в основном мощные станции."],
    ["muf","MUF — максимально используемая частота","Наибольшая частота, на которой радиоволна ещё может вернуться к Земле после отражения от ионосферы на данной трассе. Ниже 7 МГц: обычно доступны 40 и 80 метров. 7–14 МГц: ориентир для 40 метров. 14–21 МГц: ориентир для 20 метров. 21–28 МГц: ориентир для 15 метров. Выше 28 МГц: возможно прохождение на 10 метрах. No Report означает, что ионозонд не передал значение."]
  ];
  const hfDescriptions = {
    "80m-40m":"Это низкочастотные КВ-диапазоны. Днём слой D сильнее поглощает их сигналы, поэтому ночью они обычно работают лучше. Хорошее ночное прохождение возможно даже при низкой солнечной активности. Геомагнитные бури особенно сильно влияют на эти диапазоны.",
    "30m-20m":"20 метров — один из самых надёжных диапазонов для DX и при умеренной солнечной активности часто открыт почти круглосуточно. 30 метров — диапазон WARC, который особенно полезен для дальних трасс вечером.",
    "17m-15m":"Дневные диапазоны. Хорошо открываются при умеренной и высокой солнечной активности. В максимуме солнечного цикла 15 метров может обеспечивать дальние связи по всему миру в течение дня.",
    "12m-10m":"Это высокочастотные КВ-диапазоны. Для их открытия обычно нужен SFI примерно выше 120–150. При высокой солнечной активности они могут быть открыты много часов и позволять дальние связи небольшой мощностью. В минимуме цикла часто закрыты."
  };
  const vhfDescriptions = {
    "vhf-aurora|northern_hemi":"Авроральное рассеяние на УКВ. Сигналы рассеиваются на ионизованной области полярного сияния. Чаще проявляется при K-индексе 5 и выше. Трассы обычно направлены на север, к авроральной зоне. Сигнал звучит искажённо, с характерным шипением и быстрыми замираниями. Чаще используется на 144 МГц и выше; дальность трасс обычно составляет 500–2000 км. При сильной авроре одновременно ухудшается КВ-прохождение на полярных трассах.",
    "E-Skip|europe":"Спорадик E над Европой на 144 МГц (2 метра). Плотные участки ионизации внезапно возникают в слое E на высоте примерно 90–120 км. Диапазон может открываться на несколько минут или часов, иногда с очень сильными сигналами S9 и выше. Дальность трасс обычно 1000–2500 км. Чаще встречается в Европе с мая по август, а также в декабре и январе.",
    "E-Skip|europe_6m":"Спорадик E над Европой на 50 МГц (6 метров). Это УКВ-диапазон, который через спорадик открывается чаще остальных. Возможны трассы до 3000 км. Если открыт диапазон 6 метров, иногда стоит проверить и 2 метра. Чаще встречается с мая по август.",
    "E-Skip|europe_4m":"Спорадик E над Европой на 70 МГц (4 метра). По частоте открытия находится между 6 и 2 метрами. Диапазон используется не во всех странах Европы и в России практически не применяется. Его открытие говорит о достаточно плотном слое Es, поэтому могут быть доступны 50 МГц и иногда 144 МГц.",
    "E-Skip|north_america":"Спорадик E над Северной Америкой. Для европейского радиолюбителя это не прямое указание на открытие диапазона в Европе. Но одновременная активность в Европе и Северной Америке может говорить о широком распространении слоя Es."
  };
  const vhfNames={"vhf-aurora":"Авроральное прохождение","E-Skip":"Спорадический слой E","northern_hemi":"Северное полушарие","europe":"Европа","north_america":"Северная Америка","europe_6m":"Европа, диапазон 50 МГц","europe_4m":"Европа, диапазон 70 МГц"};
  function el(parent,tag,text,cls){const n=document.createElement(tag);if(text!==undefined&&text!==null)n.textContent=String(text);if(cls)n.className=cls;parent.append(n);return n;}
  function raw(v){if(v===undefined||v===null)return "";if(Array.isArray(v))return raw(v[0]);if(typeof v==="object")return raw(v["#text"]);return String(v).trim();}
  function rows(v){return v==null?[]:Array.isArray(v)?v:[v];}
  function val(v){const s=raw(v);return !s||s==="NoRpt"||s==="No Report"?"Нет данных":(translations[s]||s);}
  function time(v){return raw(v)||"время не указано";}
  function measurement(dl,label,value,unit=""){el(dl,"dt",label);return el(dl,"dd",value===null||value===undefined||value===""?"Нет данных":`${value}${unit?" "+unit:""}`);}
  function help(parent,text){const p=el(parent,"p",text,"solar-help muted");p.hidden=!hints?.checked;}
  function bandsTable(parent,solar){
    const source=rows(solar?.calculatedconditions?.band);
    const card=el(parent,"section",undefined,"result-card");
    el(card,"h3","Прохождение по диапазонам (КВ)");
    if(!source.length){el(card,"p","HamQSL не передал оценку прохождения по КВ-диапазонам.");return;}
    const map=new Map();
    for(const r of source){if(!r||typeof r!=="object")continue;const name=r["@name"]||"Без названия";const period=String(r["@time"]||"").toLowerCase();if(!map.has(name))map.set(name,{day:"Нет данных",night:"Нет данных"});if(period==="day")map.get(name).day=val(r);if(period==="night")map.get(name).night=val(r);}
    const table=el(card,"table",undefined,"data-table");
    el(table,"caption","Оценка HamQSL: день и ночь");
    const head=el(table,"thead");const tr=el(head,"tr");
    for(const t of ["Диапазон","День","Ночь"])el(tr,"th",t).scope="col";
    const body=el(table,"tbody");
    for(const [name,v] of map){const row=el(body,"tr");el(row,"th",name.toUpperCase()).scope="row";el(row,"td",v.day);el(row,"td",v.night);}
    const helpList=el(card,"ul",undefined,"solar-band-help");
    for(const [name] of map){const li=el(helpList,"li");el(li,"strong",name.toUpperCase());help(li,hfDescriptions[name]||"Подробное описание для этого диапазона пока отсутствует.");}
  }
  function renderVhf(parent,solar){
    const phenomena=rows(solar?.calculatedvhfconditions?.phenomenon);
    const card=el(parent,"section",undefined,"result-card");
    el(card,"h3","УКВ условия");
    if(!phenomena.length){el(card,"p","HamQSL не передал данные об УКВ-прохождении.");return;}
    const list=el(card,"ul",undefined,"solar-vhf-list");
    for(const r of phenomena){
      if(!r||typeof r!=="object")continue;
      const key=`${r["@name"]||""}|${r["@location"]||""}`;
      const name=vhfNames[r["@name"]]||r["@name"]||"Явление";
      const loc=vhfNames[r["@location"]]||r["@location"]||"Регион не указан";
      const li=el(list,"li");
      el(li,"strong",`${name} (${loc}): ${val(r)}`);
      help(li,vhfDescriptions[key]||"Описание этого вида прохождения пока отсутствует.");
    }
  }
  function overview(payload,noaa){
    const fragment=document.createDocumentFragment();
    const solar=payload?.data?.solardata||{};
    const card=el(fragment,"section",undefined,"result-card");
    el(card,"h3","Солнечные индексы");
    const list=el(card,"ul",undefined,"solar-index-list");
    const values={
      solarflux:noaa?.solar_flux?.value??raw(solar.solarflux),
      sunspots:raw(solar.sunspots),
      aindex:raw(solar.aindex),
      kindex:raw(solar.kindex),
      xray:raw(solar.xray),
      bz:noaa?.magnetic_field_bz?.value,
      solarwind:noaa?.solar_wind_speed?.value??raw(solar.solarwind),
      protonflux:raw(solar.protonflux),
      electonflux:raw(solar.electonflux),
      heliumline:raw(solar.heliumline),
      aurora:raw(solar.aurora),
      latdegree:raw(solar.latdegree),
      geomagfield:raw(solar.geomagfield),
      signalnoise:raw(solar.signalnoise),
      muf:raw(solar.muf)
    };
    const units={solarflux:"sfu",bz:noaa?.magnetic_field_bz?.unit||"nT",solarwind:"км/с",protonflux:"pfu",electonflux:"pfu",latdegree:"°",muf:"МГц"};
    for(const [tag,title,description] of definitions){
      let value=values[tag]||"Нет данных";
      if(tag==="kindex"&&value!=="Нет данных"){
        const k=Number.parseInt(value,10);
        const state=Number.isFinite(k)?(k<=1?"Очень спокойно":k<=3?"Спокойно":k===4?"Неустойчиво":k===5?"Малая магнитная буря":k<=7?"Умеренная магнитная буря":"Сильная магнитная буря"):"";
        if(state)value+=` (${state})`;
      }
      if(tag==="geomagfield")value=val(value);
      else if(tag==="xray")value=val(value);
      if(units[tag]&&value!=="Нет данных")value+=` ${units[tag]}`;
      const li=el(list,"li");
      el(li,"strong",`${title}: ${value}`);
      help(li,description);
    }
    if(solar.magneticfield!==undefined){
      const item=el(list,"li");
      el(item,"strong",`Магнитное поле HamQSL: ${val(solar.magneticfield)}`);
      help(item,"HamQSL не уточняет, какую именно составляющую магнитного поля показывает это поле. Поэтому его нельзя считать значением Bz или напрямую сравнивать с NOAA Bt/Bz.");
    }
    if(solar.updated)el(card,"p",`Обновлено HamQSL: ${time(solar.updated)}.`,"muted");
    bandsTable(fragment,solar);
    renderVhf(fragment,solar);
    if(payload?.drap){
      const d=el(fragment,"section",undefined,"result-card");
      el(d,"h3","Поглощение КВ-сигналов — NOAA D-RAP");
      el(d,"p","Модель оценивает, насколько солнечное излучение и частицы могут ослаблять КВ-сигналы в нижней части ионосферы (D-области). Это не измерение на антенне и не MUF.");
      el(d,"p",`Рентгеновское излучение: ${payload.drap.xray_message||"Нет данных"}`);
      el(d,"p",`Солнечные протоны: ${payload.drap.proton_message||"Нет данных"}`);
      el(d,"p",`Модель актуальна на: ${time(payload.drap.valid_at)}`,"muted");
    }
    return fragment;
  }
  function details(payload,noaa){
    const fragment=document.createDocumentFragment();const card=el(fragment,"section",undefined,"result-card");el(card,"h3","Измерения NOAA SWPC");el(card,"p","Данные NOAA показаны отдельно от HamQSL. Значения не усредняются: время и методы обработки могут различаться.","muted");const dl=el(card,"dl",undefined,"measurements observation-details");
    const labels=[["solar_flux","Солнечный поток F10.7"],["kp","Планетарный индекс Kp"],["solar_wind_speed","Скорость солнечного ветра"],["magnetic_field_bt","Полная сила магнитного поля Bt"],["magnetic_field_bz","Составляющая магнитного поля Bz"],["xray_flux","Поток рентгеновского излучения"]];
    for(const [key,label] of labels){const m=noaa?.[key];const dd=measurement(dl,label,m?.value,m?.unit||"");if(m?.observed_at)dd.textContent+=`; время измерения: ${m.observed_at}`; }
    const solar=payload?.data?.solardata;
    if(solar&&typeof solar==="object"){
      const h=el(fragment,"section",undefined,"result-card");el(h,"h3","Показатели HamQSL");el(h,"p",`Время обновления по HamQSL: ${time(solar.updated)}`,"muted");const list=el(h,"dl",undefined,"measurements solar-measurements observation-details");
      for(const [tag,title,explanation] of definitions){if(tag==="bz")continue;let value=val(solar[tag]);if(tag==="latdegree"&&value!=="Нет данных")value+="°";if(tag==="solarwind"&&value!=="Нет данных")value+=" км/с";if(tag==="muf"&&value!=="Нет данных")value+=" MHz";const dd=measurement(list,title,value);help(dd,explanation);}
      const c=el(fragment,"section",undefined,"result-card");el(c,"h3","Сопоставление источников");el(c,"p","Показатели NOAA и HamQSL приведены раздельно. Автоматическое сравнение отключено: даже похожие названия не гарантируют одинаковые методику, период усреднения и географическую область. Индекс K HamQSL не подменяет планетарный Kp NOAA, а магнитное поле Bz нельзя сравнивать с полной силой поля или неопределённым полем magneticfield. Время и единицы каждого источника указаны отдельно.","muted");
      renderVhf(fragment,solar);
    }else el(fragment,"section","HamQSL не передал данные. Остальные источники могут быть доступны независимо.","result-card");
    if(payload?.drap){const d=el(fragment,"section",undefined,"result-card");el(d,"h3","NOAA D-RAP — модель поглощения");el(d,"p",payload.drap.description||"D-RAP рассчитывает, насколько сильно D-область ионосферы может поглощать радиосигналы. Это не измерение на приёмнике и не MUF.");el(d,"p",`Рентгеновское излучение: ${payload.drap.xray_message||"Нет данных"}`);el(d,"p",`Солнечные протоны: ${payload.drap.proton_message||"Нет данных"}`);el(d,"p",`Время актуальности: ${payload.drap.valid_at||"не указано"}; получено сервером: ${payload.drap.retrieved_at||"не указано"}`,"muted");}
    if(payload?.errors&&Object.keys(payload.errors).length){const e=el(fragment,"section",undefined,"result-card");el(e,"h3","Недоступные источники");const ul=el(e,"ul");for(const [name,msg] of Object.entries(payload.errors))el(ul,"li",`${name}: ${msg}`);}
    return fragment;
  }
  if(hints)hints.addEventListener("change",()=>document.querySelectorAll(".solar-help").forEach(n=>n.hidden=!hints.checked));
  window.renderSolarOverview=overview;window.renderSolarDetails=details;
})();
