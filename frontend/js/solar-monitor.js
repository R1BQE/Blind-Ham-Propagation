(() => {
  "use strict";
  const hints = document.querySelector("#solar-show-hints");
  const translations = {"Poor":"Плохо","Fair":"Средне","Good":"Хорошо","Excellent":"Отлично","Band Closed":"Закрыт","Band Open":"Открыт","VR QUIET":"Очень спокойно","QUIET":"Спокойно","UNSETTLED":"Неустойчиво","ACTIVE":"Активно","MINOR STORM":"Небольшая магнитная буря","MAJOR STORM":"Сильная магнитная буря","SEVERE STORM":"Очень сильная магнитная буря","NoRpt":"Нет отчёта","No Report":"Нет отчёта"};
  const definitions = [
    ["solarflux","Солнечный поток F10.7","Радиоизлучение Солнца на длине волны 10,7 см. Один из показателей солнечной активности."],
    ["sunspots","Солнечные пятна","Количество видимых групп и пятен на Солнце. Само по себе число не показывает, открыта ли конкретная трасса."],
    ["aindex","Индекс A","Средняя геомагнитная активность за сутки."],
    ["kindex","Индекс K HamQSL","Оценка возмущения магнитного поля за трёхчасовой интервал. NOAA Kp приводится отдельно."],
    ["xray","Рентгеновское излучение","Сильные вспышки могут усиливать поглощение КВ-сигналов на освещённой стороне Земли."],
    ["magneticfield","Межпланетное магнитное поле Bz","Отрицательное Bz при определённых условиях может усиливать передачу энергии магнитосфере Земли."],
    ["solarwind","Скорость солнечного ветра","Высокая скорость сама по себе не означает магнитную бурю."],
    ["protonflux","Поток солнечных протонов","Во время сильных событий протоны могут вызывать поглощение радиоволн в полярных областях."],
    ["electonflux","Поток электронов","Дополнительный показатель радиационной обстановки, а не измерение шума на приёмнике."],
    ["heliumline","Линия гелия","Дополнительный индикатор солнечного ультрафиолетового излучения."],
    ["aurora","Индекс авроры","Оценка активности полярных сияний, влияющей на трассы через полярные широты."],
    ["latdegree","Широта границы аврорального овала","Положение границы области полярных сияний в геомагнитных широтах."],
    ["geomagfield","Состояние магнитного поля Земли","Сводная текстовая оценка геомагнитной обстановки от HamQSL."],
    ["signalnoise","Оценка уровня радиошума","Оценка источника, а не измерение шума непосредственно на твоей антенне."],
    ["muf","MUF — максимально применимая частота","HamQSL не указывает однозначно точку расчёта. Это нельзя считать MUF именно для KP50DB."]
  ];
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
    const card=el(parent,"section",undefined,"result-card");el(card,"h3","Общие условия на КВ");
    el(card,"p","Оценка HamQSL отдельно для дневного и ночного времени. Это не прогноз для конкретной пары станций.","muted");
    if(!source.length){el(card,"p","HamQSL не передал оценку по диапазонам.");return;}
    const map=new Map();
    for(const r of source){if(!r||typeof r!=="object")continue;const name=r["@name"]||"Без названия";const period=String(r["@time"]||"").toLowerCase();if(!map.has(name))map.set(name,{day:"Нет данных",night:"Нет данных"});if(period==="day")map.get(name).day=val(r);if(period==="night")map.get(name).night=val(r);}
    const table=el(card,"table",undefined,"data-table");el(table,"caption","Оценка HamQSL по диапазонам");const head=el(table,"thead");const tr=el(head,"tr");for(const t of ["Диапазон","Днём","Ночью"])el(tr,"th",t).scope="col";const body=el(table,"tbody");
    for(const [name,v] of map){const row=el(body,"tr");el(row,"th",name.toUpperCase()).scope="row";el(row,"td",v.day);el(row,"td",v.night);}
  }
  function renderVhf(parent,solar){
    const phenomena=rows(solar?.calculatedvhfconditions?.phenomenon);const card=el(parent,"section",undefined,"result-card");el(card,"h3","Условия для УКВ");el(card,"p","Оценки отдельных механизмов дальнего УКВ-прохождения. Они не гарантируют проведение связи.","muted");
    if(!phenomena.length){el(card,"p","HamQSL не передал данные об УКВ-условиях.");return;}
    const list=el(card,"ul",undefined,"solar-vhf-list");
    for(const r of phenomena){if(!r||typeof r!=="object")continue;const name=vhfNames[r["@name"]]||r["@name"]||"Явление";const loc=vhfNames[r["@location"]]||r["@location"]||"Регион не указан";const li=el(list,"li");el(li,"strong",`${name}. Регион: ${loc}. Статус: ${val(r)}.`);help(li,"Спорадический слой E и авроральное прохождение иногда позволяют проводить УКВ-связи дальше обычной прямой видимости. Условия быстро меняются.");}
  }
  function overview(payload,noaa){
    const fragment=document.createDocumentFragment();const solar=payload?.data?.solardata||{};
    const activity=el(fragment,"section",undefined,"result-card");el(activity,"h3","Солнечная активность");const dl=el(activity,"dl",undefined,"measurements");
    const flux=noaa?.solar_flux?.value??(raw(solar.solarflux)||null);measurement(dl,"Поток F10.7",flux,noaa?.solar_flux?.value!==null&&noaa?.solar_flux?.value!==undefined?"sfu":"");measurement(dl,"Солнечные пятна",solar.sunspots===undefined?"Нет данных":val(solar.sunspots));el(activity,"p",`F10.7: ${noaa?.solar_flux?.value!==null&&noaa?.solar_flux?.value!==undefined?"NOAA":"HamQSL"}. Время измерения смотри в подробных данных.`,"muted");
    const geo=el(fragment,"section",undefined,"result-card");el(geo,"h3","Геомагнитная обстановка");const gd=el(geo,"dl",undefined,"measurements");measurement(gd,"Индекс Kp NOAA",noaa?.kp?.value);measurement(gd,"Оценка HamQSL",solar.geomagfield===undefined?"Нет данных":val(solar.geomagfield));measurement(gd,"Индекс K HamQSL",solar.kindex===undefined?"Нет данных":val(solar.kindex));el(geo,"p","Глобальные показатели общей обстановки, а не прогноз прохождения на конкретной трассе.","muted");
    if(payload?.data?.solardata)bandsTable(fragment,solar);else{const missing=el(fragment,"section",undefined,"result-card");el(missing,"h3","Общие условия на КВ");el(missing,"p","HamQSL сейчас не передал данные об условиях по диапазонам.");}
    if(payload.drap){const d=el(fragment,"section",undefined,"result-card");el(d,"h3","Поглощение КВ-сигналов");el(d,"p","NOAA D-RAP моделирует поглощение в нижней части ионосферы. Это не измерение на антенне и не MUF.");el(d,"p",`Рентгеновское излучение: ${payload.drap.xray_message||"Нет данных"}`);el(d,"p",`Солнечные протоны: ${payload.drap.proton_message||"Нет данных"}`);el(d,"p",`Модель актуальна на: ${time(payload.drap.valid_at)}`,"muted");}
    el(fragment,"p",`HamQSL обновил данные: ${time(solar.updated)}. Ответ получен сервером: ${payload.retrieved_at||"время не указано"}.`,"muted");
    if(payload.cache?.hit)el(fragment,"p","Используется кэш сервера; запрос к HamQSL выполняется не чаще одного раза в 60 минут.","muted");
    return fragment;
  }
  function details(payload,noaa){
    const fragment=document.createDocumentFragment();const card=el(fragment,"section",undefined,"result-card");el(card,"h3","Измерения NOAA SWPC");el(card,"p","Данные NOAA показаны отдельно от HamQSL. Значения не усредняются: время и методы обработки могут различаться.","muted");const dl=el(card,"dl",undefined,"measurements observation-details");
    const labels=[["solar_flux","Солнечный поток F10.7"],["kp","Планетарный индекс Kp"],["solar_wind_speed","Скорость солнечного ветра"],["magnetic_field_bt","Полная сила магнитного поля Bt"],["magnetic_field_bz","Составляющая магнитного поля Bz"],["xray_flux","Поток рентгеновского излучения"]];
    for(const [key,label] of labels){const m=noaa?.[key];const dd=measurement(dl,label,m?.value,m?.unit||"");if(m?.observed_at)dd.textContent+=`; время измерения: ${m.observed_at}`; }
    const solar=payload?.data?.solardata;
    if(solar&&typeof solar==="object"){
      const h=el(fragment,"section",undefined,"result-card");el(h,"h3","Показатели HamQSL");el(h,"p",`Время обновления по HamQSL: ${time(solar.updated)}`,"muted");const list=el(h,"dl",undefined,"measurements solar-measurements observation-details");
      for(const [tag,title,explanation] of definitions){let value=val(solar[tag]);if(tag==="latdegree"&&value!=="Нет данных")value+="°";if(tag==="solarwind"&&value!=="Нет данных")value+=" км/с";const dd=measurement(list,title,value);help(dd,explanation);}
      const c=el(fragment,"section",undefined,"result-card");el(c,"h3","Сопоставление источников");el(c,"p","Показатели NOAA и HamQSL приведены раздельно. Автоматическое сравнение отключено: даже похожие названия не гарантируют одинаковые методику, период усреднения и географическую область. Индекс K HamQSL не подменяет планетарный Kp NOAA, а магнитное поле Bz нельзя сравнивать с полной силой поля или неопределённым полем magneticfield. Время и единицы каждого источника указаны отдельно.","muted");
      renderVhf(fragment,solar);
    }else el(fragment,"section","HamQSL не передал данные. Остальные источники могут быть доступны независимо.","result-card");
    if(payload?.drap){const d=el(fragment,"section",undefined,"result-card");el(d,"h3","NOAA D-RAP — модель поглощения");el(d,"p",payload.drap.description||"Модельная оценка поглощения в D-области. Это не MUF.");el(d,"p",`Рентгеновское излучение: ${payload.drap.xray_message||"Нет данных"}`);el(d,"p",`Солнечные протоны: ${payload.drap.proton_message||"Нет данных"}`);el(d,"p",`Время актуальности: ${payload.drap.valid_at||"не указано"}; получено сервером: ${payload.drap.retrieved_at||"не указано"}`,"muted");}
    if(payload?.errors&&Object.keys(payload.errors).length){const e=el(fragment,"section",undefined,"result-card");el(e,"h3","Недоступные источники");const ul=el(e,"ul");for(const [name,msg] of Object.entries(payload.errors))el(ul,"li",`${name}: ${msg}`);}
    return fragment;
  }
  if(hints)hints.addEventListener("change",()=>document.querySelectorAll(".solar-help").forEach(n=>n.hidden=!hints.checked));
  window.renderSolarOverview=overview;window.renderSolarDetails=details;
})();
