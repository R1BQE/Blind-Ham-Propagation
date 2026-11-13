(() => {
  "use strict";
  const hints = document.querySelector("#solar-show-hints");
  const translations = {"Poor":"Плохо","Fair":"Средне","Good":"Хорошо","Excellent":"Отлично","Band Closed":"Закрыт","Band Open":"Открыт","VR QUIET":"Очень спокойно","QUIET":"Спокойно","UNSETTLED":"Неустойчиво","ACTIVE":"Активно","MINOR STORM":"Небольшая магнитная буря","MAJOR STORM":"Сильная магнитная буря","SEVERE STORM":"Очень сильная магнитная буря","NoRpt":"Нет отчёта","No Report":"Нет отчёта"};
  const definitions = [
    ["solarflux","Солнечный поток F10.7","Показывает, насколько активно Солнце излучает радиоволны. Чем выше значение, тем больше солнечная активность. Это полезный ориентир для КВ, но не гарантия хорошего прохождения."],
    ["sunspots","Солнечные пятна","Тёмные области на поверхности Солнца. Часто их становится больше при высокой солнечной активности. Но по одному числу пятен нельзя понять, будет ли проходить связь между двумя станциями."],
    ["aindex","Индекс A","Показывает, насколько сильно магнитное поле Земли возмущалось за последние сутки. Чем выше индекс, тем сильнее были изменения."],
    ["kindex","Индекс K HamQSL","Показывает возмущения магнитного поля Земли за последние три часа. Чем выше значение, тем неспокойнее магнитная обстановка. Индекс Kp NOAA показан отдельно — это другой источник данных."],
    ["xray","Рентгеновское излучение","Во время солнечной вспышки поток рентгеновского излучения резко растёт. На освещённой стороне Земли это может усилить поглощение КВ-сигналов: дальние станции становятся слышны хуже или пропадают."],
    ["magneticfield","Магнитное поле по данным HamQSL","Дополнительный показатель магнитного поля из HamQSL. Источник не уточняет, какую именно составляющую показывает это поле, поэтому нельзя считать его значением Bz или напрямую сравнивать с Bt/Bz NOAA."],
    ["solarwind","Скорость солнечного ветра","Солнечный ветер — поток частиц от Солнца. Он постоянно достигает Земли. Высокая скорость может влиять на магнитное поле, но сама по себе ещё не означает магнитную бурю."],
    ["protonflux","Поток солнечных протонов","Во время сильных солнечных событий к Земле приходит больше быстрых частиц — протонов. В полярных районах они могут сильно поглощать КВ-сигналы, и связь на некоторых трассах ухудшается."],
    ["electonflux","Поток электронов","Показывает поток электронов в околоземном космосе. Это показатель космической радиационной обстановки, а не уровень помех или шума у тебя на приёмнике."],
    ["heliumline","Линия гелия","Показатель излучения Солнца в определённой линии спектра. Он помогает оценивать солнечную активность, но сам по себе не говорит, открыт ли диапазон."],
    ["aurora","Индекс авроры","Оценка активности полярных сияний. При сильной авроральной активности радиосигналы на трассах через северные широты могут искажаться или проходить необычным способом."],
    ["latdegree","Широта границы аврорального овала","Показывает, где проходит граница области полярных сияний. Чем дальше она смещается к югу, тем больше вероятность влияния авроральных условий на радиосвязь в северных районах."],
    ["geomagfield","Состояние магнитного поля Земли","Краткая оценка того, насколько спокойно магнитное поле Земли. Во время сильных возмущений прохождение на КВ может стать нестабильным."],
    ["signalnoise","Оценка уровня радиошума","Расчётная оценка радиошума по данным источника. Это не измерение помех на твоём QTH и не показания твоего трансивера."],
    ["muf","MUF — максимально применимая частота","MUF — самая высокая частота, на которой радиоволна при данных условиях ещё может вернуться к Земле после отражения от ионосферы. Если рабочая частота выше MUF, связь по такой трассе может не пройти. Значение HamQSL получено из Lowell GIRO Data Center, но источник не указывает точку расчёта. Поэтому не считай его MUF именно для своего QTH или конкретной трассы."]
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
    el(card,"p","HamQSL оценивает, насколько благоприятны условия на разных КВ-диапазонах днём и ночью. Это общая подсказка: на конкретной трассе результат может отличаться.","muted");
    if(!source.length){el(card,"p","HamQSL не передал оценку по диапазонам.");return;}
    const map=new Map();
    for(const r of source){if(!r||typeof r!=="object")continue;const name=r["@name"]||"Без названия";const period=String(r["@time"]||"").toLowerCase();if(!map.has(name))map.set(name,{day:"Нет данных",night:"Нет данных"});if(period==="day")map.get(name).day=val(r);if(period==="night")map.get(name).night=val(r);}
    const table=el(card,"table",undefined,"data-table");el(table,"caption","Оценка HamQSL по диапазонам");const head=el(table,"thead");const tr=el(head,"tr");for(const t of ["Диапазон","Днём","Ночью"])el(tr,"th",t).scope="col";const body=el(table,"tbody");
    for(const [name,v] of map){const row=el(body,"tr");el(row,"th",name.toUpperCase()).scope="row";el(row,"td",v.day);el(row,"td",v.night);}
  }
  function renderVhf(parent,solar){
    const phenomena=rows(solar?.calculatedvhfconditions?.phenomenon);const card=el(parent,"section",undefined,"result-card");el(card,"h3","Условия для УКВ");el(card,"p","Здесь показаны условия, при которых УКВ-сигнал иногда проходит намного дальше обычного. Это возможность, а не обещание связи.","muted");
    if(!phenomena.length){el(card,"p","HamQSL не передал данные об УКВ-условиях.");return;}
    const list=el(card,"ul",undefined,"solar-vhf-list");
    for(const r of phenomena){if(!r||typeof r!=="object")continue;const name=vhfNames[r["@name"]]||r["@name"]||"Явление";const loc=vhfNames[r["@location"]]||r["@location"]||"Регион не указан";const li=el(list,"li");el(li,"strong",`${name}. Регион: ${loc}. Статус: ${val(r)}.`);help(li,"Спорадический слой E и авроральное прохождение могут неожиданно открыть дальнюю УКВ-связь. Такие условия бывают не всегда и иногда исчезают очень быстро.");}
  }
  function overview(payload,noaa){
    const fragment=document.createDocumentFragment();const solar=payload?.data?.solardata||{};
    const activity=el(fragment,"section",undefined,"result-card");el(activity,"h3","Солнечная активность");const dl=el(activity,"dl",undefined,"measurements");
    const hamqslFlux=val(solar.solarflux)==="Нет данных"?null:raw(solar.solarflux);const flux=noaa?.solar_flux?.value??hamqslFlux;measurement(dl,"Поток F10.7",flux,"sfu");measurement(dl,"Солнечные пятна",solar.sunspots===undefined?"Нет данных":val(solar.sunspots));el(activity,"p",`F10.7: ${noaa?.solar_flux?.value!==null&&noaa?.solar_flux?.value!==undefined?"NOAA":"HamQSL"}. Время измерения смотри в подробных данных.`,"muted");
    const geo=el(fragment,"section",undefined,"result-card");el(geo,"h3","Геомагнитная обстановка");const gd=el(geo,"dl",undefined,"measurements");measurement(gd,"Индекс Kp NOAA",noaa?.kp?.value);measurement(gd,"Оценка HamQSL",solar.geomagfield===undefined?"Нет данных":val(solar.geomagfield));measurement(gd,"Индекс K HamQSL",solar.kindex===undefined?"Нет данных":val(solar.kindex));el(geo,"p","Эти индексы описывают общую обстановку на Земле. Они помогают понять фоновые условия, но не предсказывают напрямую связь между двумя конкретными QTH.","muted");
    if(payload?.data?.solardata)bandsTable(fragment,solar);else{const missing=el(fragment,"section",undefined,"result-card");el(missing,"h3","Общие условия на КВ");el(missing,"p","HamQSL сейчас не передал данные об условиях по диапазонам.");}
    if(payload.drap){const d=el(fragment,"section",undefined,"result-card");el(d,"h3","Поглощение КВ-сигналов");el(d,"p","NOAA D-RAP — модель поглощения радиоволн в нижней части ионосферы, которую называют D-областью. Проще говоря, она показывает, где солнечное излучение и частицы могут ослаблять КВ-сигналы. Это расчёт модели, а не измерение на твоей антенне и не MUF.");el(d,"p",`Рентгеновское излучение: ${payload.drap.xray_message||"Нет данных"}`);el(d,"p",`Солнечные протоны: ${payload.drap.proton_message||"Нет данных"}`);el(d,"p",`Модель актуальна на: ${time(payload.drap.valid_at)}`,"muted");}
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
      for(const [tag,title,explanation] of definitions){let value=val(solar[tag]);if(tag==="latdegree"&&value!=="Нет данных")value+="°";if(tag==="solarwind"&&value!=="Нет данных")value+=" км/с";if(tag==="muf"&&value!=="Нет данных")value+=" MHz";const dd=measurement(list,title,value);help(dd,explanation);}
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
