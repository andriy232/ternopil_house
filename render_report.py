import json,html,re,math,datetime,argparse,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
O=Path(a.out);O.mkdir(parents=True,exist_ok=True);root=Path(__file__).parent
D=json.loads(Path(a.input).read_text(encoding='utf-8-sig'));rows=D['listings'];E=lambda x:html.escape(str(x),quote=True)
now=datetime.datetime.fromisoformat(D['checkedAt']) if D.get('checkedAt') else datetime.datetime.now().astimezone();stamp=now.strftime('%d.%m.%Y %H:%M')
rank={'Центр':0,'Східний':1,'Новий світ':2,'БАМ':3,'Канада':4,'Дружба':5,'Кутківці':7,'Пронятин':8,'Великі Гаї':9,'Підгороднє':10}
for r in rows:
 r['rank']=next((v for k,v in list(rank.items())[:6] if r['district'].startswith(k)),6 if any(k in r['district'] for k in ['Кутківці','Пронятин','Великі Гаї','Підгороднє','Передмістя']) else 7)
 r['centerKm']=r.get('centerKm') if r.get('coords') else None
def fmt(v):return '—' if v is None else format(v,',').replace(',',' ') if isinstance(v,(int,float)) else str(v)
def links(r):
 out=[]
 for s in r.get('sources',[]):
  if not s.get('url'):continue
  label=s.get('label','Оголошення')
  if s.get('verified') and not s.get('removed'):out.append('<a target="_blank" rel="noopener" href="'+E(s['url'])+'">'+E(label)+'</a>')
  else:
   ident=re.search(r'(?:view/|estate/)(\d+)|-(ID[^./]+)\.html|-(\d+)\.html|ann-([\d-]+)\.html',s['url'])
   code=next((x for x in ident.groups() if x),'') if ident else ''
   out.append('<span class="muted">'+E(label+' '+code+' — '+('сторінку видалено' if s.get('removed') else 'не перевірено'))+'</span>')
 return ' · '.join(out)
def cadastrelinks(r):
 out=[]
 for x in r.get('cadastreLinks',[]):
  if not x.get('url'):continue
  label=E(x.get('label') or x.get('number') or 'Кадастрова сторінка')
  if x.get('verified'):out.append('<a target="_blank" rel="noopener" href="'+E(x['url'])+'">'+label+'</a>')
  else:out.append('<span class="muted">'+label+' — '+('потрібен вхід' if x.get('requiresAuthentication') else 'не перевірено')+'</span>')
 return ' · '.join(out)
def measurement(r,key,label):
 x=r.get('measurements',{}).get(key)
 if not x or not r.get('coords'):return label+': не встановлено'
 prefix='від '+x.get('basis','адресної точки' if r.get('numberKnown') else 'маркера')
 return label+': ≈'+fmt(x['meters'])+' м '+E(prefix)+' · по прямій; не від межі ділянки · <a target="_blank" rel="noopener" href="'+E(x['url'])+'">'+E(x['name'])+'</a> · дата '+E(x.get('checkedAt','не встановлена'))
def rowhtml(r):
 num=r['number'];i=r['id'];known=r.get('numberKnown');dist='—' if r.get('centerKm') is None else '≈'+str(r['centerKm']).replace('.',',')+' км'
 price=r.get('priceLabel') or '$'+fmt(r['price'])
 thumbnail='<a href="'+E(r.get('thumbnail',''))+'" target="_blank" rel="noopener"><img loading="lazy" width="138" height="104" src="'+E(r.get('thumbnail',''))+'" alt="Фото: '+E(r['address'])+'"></a>'
 d=[('Місце',r.get('location','Номер будинку не підтверджений.')),('Заїзд',r.get('driveway','Не підтверджено за доступними ракурсами.')),('Сусіди й приватність',r.get('privacy','Повної перевірки сусідніх ділянок немає.')),('Однотипна забудова',r.get('rowHousing','Доказів відсутності щільного ряду недостатньо.')),('Стан / витрати',r.get('condition','Дивіться опис і фото; технічного огляду не було.')),('Рельєф / перехрестя',r.get('terrain','Низину та положення відносно роздоріжжя не підтверджено.'))]
 d.append(('Відступ від тротуару',r.get('setback','Наявність відступу стіни від тротуару на 1–2 м не підтверджена.')))
 d.extend([('Комісія',r.get('commission','Не встановлено.')),('Комунікації',r.get('utilities','Не встановлено.')),('Актуальність',r.get('availabilityNote','Не встановлено.')),('Супутник / дата',r.get('satelliteReview','Не перевірено.')),('Фото / дата',r.get('photoReview','Не перевірено.'))])
 for k,label in [('currencyNote','Валюта'),('priceConflict','Обсяг продажу й ціна'),('areaConflict','Площа: конфлікт'),('landConflict','Земля: конфлікт')]:
  if r.get(k):d.append((label,r[k]))
 if r.get('questions'):d.append(('Питання продавцю',r['questions']))
 if r.get('kind')=='land':d.append(('Призначення землі',r.get('zoning','Не підтверджено документально.')))
 details='<div class="facts">'+''.join('<div><b>'+E(k)+'</b><p>'+E(v)+'</p></div>' for k,v in d)+'</div>'
 details+='<p>'+measurement(r,'rail','Колія')+'<br>'+measurement(r,'cemetery','Цвинтар')+'</p>'
 details+='<p><b>Зупинка та садочок.</b> '+E(r.get('infrastructure',''))+'</p>'
 if not r.get('infrastructure'):details+='<p>'+measurement(r,'stop','Найближча знайдена зупинка')+'<br>'+measurement(r,'kindergarten','Найближчий знайдений садочок')+'. Відстані по прямій; повнота POI та реальний пішохідний маршрут не гарантовані.</p>'
 if r.get('route'):details+='<p><a target="_blank" rel="noopener" href="'+E(r['route'])+'">Google Maps: маршрут до садочка (потребує перевірки)</a></p>'
 if r.get('duplicates'):details+='<p><b>Зіставлення дублікатів.</b> '+E(r['duplicates'])+'</p>'
 if r.get('cadastreLinks'):details+='<p><b>Кадастрові сторінки.</b> '+cadastrelinks(r)+'<br><span class="small">'+E(r.get('cadastreNote','Сторінка довідкова. Перед угодою потрібні актуальні офіційні витяги та перевірка всіх ділянок, що входять у продаж.'))+'</span></p>'
 elif r.get('cadastreNote'):details+='<p><b>Кадастрова прив’язка.</b> '+E(r['cadastreNote'])+'</p>'
 details+='<div class="gallery">'+''.join('<a href="'+E(u)+'" target="_blank" rel="noopener"><img loading="lazy" src="'+E(u)+'" alt="'+E(r['address'])+' · фото '+str(j+1)+'"><span>'+str(j+1)+'</span></a>' for j,u in enumerate(r.get('photos',[])))+'</div>'
 details+='<p class="small">Дата перевірки сторінки: '+E(r.get('checkedAt',D.get('checkedAt','')))+' · Наявність оголошення не підтверджує, що будинок ще не проданий.</p>'
 maps='<a target="_blank" rel="noopener" href="'+E(r['map'])+'">Google Maps</a>'
 if r.get('coords'):maps+='<br><a target="_blank" rel="noopener" href="'+E(r['satellite'])+'">Супутник</a><br><button type="button" class="mapjump" data-id="'+E(i)+'">Мітка '+str(num)+'</button>'
 else:maps+='<br><span class="warn">Адреса не встановлена</span>'
 toggle='<button type="button" class="detailtoggle" data-id="'+E(i)+'" aria-expanded="false">Деталі перевірки та фото ('+str(len(r.get('photos',[])))+')</button>'
 return '<tbody id="row-'+E(i)+'" class="property" data-kind="'+E(r.get('kind','house'))+'" data-id="'+E(i)+'" data-price="'+str(r['price'])+'" data-rank="'+str(r['rank'])+'" data-distance="'+str(r.get('centerKm') if r.get('centerKm') is not None else 9999)+'"><tr><td class="photo">'+thumbnail+'</td><td><span class="number">'+str(num)+'</span><b>'+E(r['address'])+'</b><div class="muted">'+E(r['district'])+'</div><span class="precision">'+E(r.get('mapPrecision','приблизно'))+'</span>'+toggle+'</td><td class="price">'+E(price)+'<small>'+E(fmt(r['area']))+' м²<br>'+E(fmt(r['land']))+' сот.</small></td><td class="distance">'+dist+'<small>по прямій</small></td><td class="assessment">'+E(r['reason'])+'</td><td class="source">'+links(r)+'<div class="maplinks">'+maps+'</div></td></tr><tr class="detailrow" data-detail="'+E(i)+'" hidden><td colspan="6" class="more"><div class="detailpanel">'+details+'</div></td></tr></tbody>'
active=[r for r in rows if r['section']=='active'];excluded=[r for r in rows if r['section']!='active']
sort_key=lambda r:(r['rank'],r['price'])
active.sort(key=sort_key);excluded.sort(key=sort_key)
for n,r in enumerate(active+excluded,1):r['number']=n
rows=active+excluded;D['listings']=rows
cadastre_rows=[r for r in active+excluded if r.get('cadastreLinks')]
def table(items):
 return '<div class="tablewrap"><table class="houses"><thead><tr><th>Фото</th><th>Об’єкт / район</th><th>Ціна / площа</th><th>До центру</th><th>Висновок</th><th>Посилання</th></tr></thead>'+''.join(rowhtml(r) for r in items)+'</table></div>'
sources=D.get('sources',[])
def sourcerow(s):
 title=E(s['name']);url=s.get('url','')
 if not s.get('removed') and (s.get('verified') or s.get('sourceType')=='catalog'):title='<a target="_blank" rel="noopener" href="'+E(url)+'">'+title+'</a>'
 else:title+='<br><span class="small">'+E(url)+'</span>'
 proof='<br><a href="'+E(s['evidence'])+'">Збережений доказ</a>' if s.get('evidence') else ''
 return '<tr><td>'+title+'</td><td>'+E(s['coverage'])+proof+'</td><td>'+E(s['limitations'])+'<br><span class="small">'+E(s.get('checkedAt',''))+' · HTTP '+E(s.get('status','—'))+' · '+E(s.get('method',''))+'</span></td></tr>'
sourcehtml='<p>'+E(D.get('summary',''))+'</p><ul>'+''.join('<li>'+E(x)+'</li>' for x in D.get('coverageLimitations',[]))+'</ul><div class="tablewrap"><table class="sources"><thead><tr><th>Сайт</th><th>Що перевірено</th><th>Доступ / обмеження</th></tr></thead><tbody>'+''.join(sourcerow(s) for s in sources)+'</tbody></table></div>'
cadastrehtml='<div class="tablewrap"><table class="sources"><thead><tr><th>№</th><th>Об’єкт</th><th>Кадастровий номер</th><th>Пряма сторінка</th></tr></thead><tbody>'+''.join('<tr><td>'+str(r['number'])+'</td><td><a href="#row-'+E(r['id'])+'">'+E(r['address'])+'</a><br><span class="muted">'+E('актуальний кандидат' if r['section']=='active' else 'відсіяно / не включено')+'</span></td><td>'+('<br>'.join(E(x.get('number','—')) for x in r['cadastreLinks']))+'</td><td>'+cadastrelinks(r)+'</td></tr>' for r in cadastre_rows)+'</tbody></table></div>'
kindergarten_scan=D.get('kindergartenScan',{})
confirmed_kindergartens=kindergarten_scan.get('confirmed',[])
reviewed_kindergartens=kindergarten_scan.get('reviewedWithoutCurrentConfirmation',[])
def kindergartenrow(x):
 official='<a target="_blank" rel="noopener" href="'+E(x['officialUrl'])+'">ІСУО</a>' if x.get('officialUrl') else '—'
 maps='<a target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&amp;query='+E(str(x.get('lat',''))+','+str(x.get('lon','')))+'">Google Maps</a>' if x.get('lat') is not None else '—'
 distance='≈'+str(x.get('centerKm')).replace('.',',')+' км' if x.get('centerKm') is not None else '—'
 dates='<br><span class="small">Перевірено: '+E(x.get('checkedAt','не встановлено'))+'<br>Оновлення запису: '+E(x.get('recordUpdatedAt','не встановлено'))+'</span>'
 return '<tr><td><b>'+E(x.get('settlement',''))+'</b></td><td>'+E(x.get('name',''))+'<br><span class="small">'+E(x.get('address',''))+'</span></td><td>'+official+dates+'</td><td>'+distance+'<br><span class="small">'+E(x.get('precision',''))+'</span></td><td>'+maps+'</td></tr>'
kindergartenhtml='<p>'+E(kindergarten_scan.get('scope',''))+'</p><div class="notice"><b>Що означає підтвердження.</b> '+E(kindergarten_scan.get('method',''))+'</div>'
kindergartenhtml+='<div class="tablewrap"><table class="sources"><thead><tr><th>Населений пункт</th><th>Заклад / адреса</th><th>Офіційний запис</th><th>До центру / точність мітки</th><th>Карта</th></tr></thead><tbody>'+''.join(kindergartenrow(x) for x in confirmed_kindergartens)+'</tbody></table></div>'
if reviewed_kindergartens:kindergartenhtml+='<div class="card"><b>Перевірено, але чинний окремий запис не підтверджено</b><ul>'+''.join('<li><b>'+E(x.get('settlement',''))+':</b> '+E(x.get('result',''))+(' <a target="_blank" rel="noopener" href="'+E(x['officialUrl'])+'">Перевірений запис</a>' if x.get('officialUrl') else '')+'</li>' for x in reviewed_kindergartens)+'</ul><p class="small">Відсутність запису у перевіреній видачі не доводить, що садочка або дошкільної групи немає. Для конкретного будинку все одно потрібні точна адреса, перевірка фактичної роботи закладу та пішохідний маршрут до 500 м від виходу з двору.</p></div>'
css=r'''
:root{--ink:#162c35;--muted:#617179;--paper:#f4f3ed;--blue:#196a82;--amber:#b86d1e;--red:#a5483e}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#126078;text-decoration:none}a:hover{text-decoration:underline}header{background:#183842;color:#fff;padding:34px max(24px,calc((100vw - 1390px)/2)) 28px}h1{font:600 35px/1.15 Georgia,serif;margin:8px 0 16px}h2{font:600 25px/1.2 Georgia,serif;margin:36px 0 14px}header p{max-width:960px;color:#d8e6e7}nav{display:flex;gap:22px;flex-wrap:wrap;font-size:14px}nav a{color:#fff}.eyebrow{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#a8c4c7}.wrap{max-width:1440px;margin:auto;padding:24px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.stat{border:1px solid #d9dfdb;border-radius:8px;padding:18px;background:#fff}.stat b{font-size:28px;display:block}.stat span{color:var(--muted)}.notice{border-left:4px solid var(--amber);padding:14px 18px;margin:20px 0;background:#fff7e8}.small,.muted{font-size:13px;color:var(--muted)}.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:18px 0}input,select,button{font:inherit;padding:8px 12px;border:1px solid #bac9cc;border-radius:5px;background:white;color:var(--ink)}button{cursor:pointer}input{min-width:260px}.maplayout{display:grid;grid-template-columns:1fr 280px;gap:15px}#map{height:590px;border:1px solid #bbc8c9;border-radius:8px;z-index:1}.mapaside{background:#fff;border:1px solid #d7dfdc;border-radius:8px;padding:16px;max-height:590px;overflow:auto}.mapaside ul{padding-left:18px}.mapaside li{margin:10px 0;font-size:13px}.legend{display:flex;gap:18px;flex-wrap:wrap;margin:10px 0}.legend span:before{content:"";display:inline-block;width:10px;height:10px;background:var(--blue);margin-right:7px;border-radius:50%}.legend .excluded:before{background:var(--red)}.legend .cem:before{background:#795687}.legend .rail:before{background:#444}.legend .kindergarten:before{background:#178a59}.legend .stop:before{background:#20769b}.tablewrap{overflow:auto;border:1px solid #d7dfdc;border-radius:8px;background:#fff}table{width:100%;border-collapse:collapse;text-align:left}th{padding:12px;font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:#546a71;background:#e9eeeb}td{padding:15px 12px;vertical-align:top}.property>tr:first-child{border-top:1px solid #dce4df}.property:first-of-type>tr:first-child{border:0}.photo{width:170px}.photo img{display:block;width:138px;height:104px;object-fit:cover;border-radius:5px}.detailtoggle{display:block;width:max-content;white-space:nowrap;margin-top:7px;padding:4px 7px;text-align:left;font-size:12px;line-height:1.2;color:var(--blue);background:#f6faf9}.detailtoggle[aria-expanded="true"]{background:#e8f2f1;font-weight:600}.detailrow[hidden]{display:none}.more{padding:0 12px 14px}.detailpanel{padding:14px;background:#f4f6f3;border-radius:7px}.price{min-width:130px;font-weight:700}.price small,.distance small{display:block;font-weight:400;color:var(--muted);margin-top:7px;font-size:13px}.distance{min-width:85px}.assessment{min-width:270px;max-width:420px;font-size:14px}.source{min-width:148px;font-size:13px}.maplinks{margin-top:12px}.mapjump{font-size:12px;padding:3px 7px;margin-top:6px}.number{display:inline-flex;justify-content:center;align-items:center;background:#edf1ed;color:#4a656c;border-radius:3px;min-width:25px;height:24px;font-size:12px;margin-right:8px}.precision{display:inline-block;font-size:11px;border:1px solid #d9dfd7;border-radius:12px;padding:2px 7px;margin-top:8px;color:#647168}.warn{color:#9b5728;font-size:12px}.facts{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;font-size:13px;margin:4px 0 18px}.facts b{display:block;color:#4b646a}.facts p{margin:5px 0}.gallery{display:grid;grid-template-columns:repeat(5,1fr);gap:9px}.gallery a{position:relative}.gallery img{width:100%;height:145px;object-fit:contain;background:#e4e7e0}.gallery span{position:absolute;bottom:7px;left:5px;background:#fff;padding:1px 4px;font-size:11px}.sources td{border-top:1px solid #e2e7e3;font-size:14px}.sources td:first-child{min-width:140px}.pin{border-radius:50%;background:var(--blue);border:2px solid white;color:white;text-align:center;line-height:26px;font-size:12px;font-weight:700;box-shadow:0 1px 5px #4446}.pin.reject{background:var(--red)}.pin.approx{border-style:dashed}.popup{width:230px;line-height:1.4}.popup img{width:100%;height:125px;object-fit:cover}.popup p{margin:8px 0}.sectionnote{max-width:1000px;color:#617179}.foot{padding:25px 0 10px;color:#617179;font-size:13px}.hidden{display:none!important}.highlight{background:#fff3ca}.card{background:#fff;border:1px solid #d9dfdb;border-radius:8px;padding:18px;margin-top:16px}@media(max-width:950px){.maplayout{grid-template-columns:1fr}.mapaside{max-height:220px}.facts{grid-template-columns:1fr 1fr}.gallery{grid-template-columns:repeat(3,1fr)}.assessment{min-width:230px}}@media(max-width:600px){.wrap{padding:14px}.stats{gap:7px}.stat{padding:10px}.stat b{font-size:23px}header{padding:22px 16px}h1{font-size:28px}#map{height:430px}.facts{grid-template-columns:1fr}.gallery{grid-template-columns:repeat(2,1fr)}}@media print{header{background:#fff;color:#183842}header p,header a{color:#183842}.toolbar,button{display:none}#map{height:400px}.mapaside{max-height:none}.maplayout{grid-template-columns:1fr}.tablewrap{overflow:visible}.property{break-inside:avoid}.detailrow{display:none!important}}
'''
header='<header><div class="eyebrow">Тернопіль · приватний будинок · оновлений відбір</div><h1>Власний двір ближче до центру</h1><p>До $120 000 · від 3 соток · окремий будинок · пріоритет від 80 м². Колія та цвинтар — від 100 м; заміські варіанти — зі зупинкою і садочком до 500 м.</p><nav><a href="#map-section">Карта</a><a href="#kindergartens">Садочки</a><a href="#active">Актуальні сторінки</a><a href="#excluded">Що відсіяно</a><a href="#cadastre">Кадастр</a><a href="#sources">Джерела</a><a href="#automation">Щоденний пошук</a></nav><p class="small" style="color:#bbd2d6">Перевірено '+E(stamp)+' · Київ</p></header>'
leafcss=(root/'assets/leaflet.css').read_text(encoding='utf8');leafjs=(root/'assets/leaflet.js').read_text(encoding='utf8')
maplibrecss=(root/'assets/maplibre-gl.css').read_text(encoding='utf8');maplibrejs=(root/'assets/maplibre-gl.js').read_text(encoding='utf8');maplibreleaflet=(root/'assets/leaflet-maplibre-gl.js').read_text(encoding='utf8')
head='<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Будинки Тернополя — '+stamp+'</title><style>'+leafcss+'\n'+maplibrecss+'\n'+css+'</style></head><body>'
unknown=[r for r in rows if not r.get('coords')]
summary_block='<div class="stats"><div class="stat"><b>'+str(len(active))+'</b><span>актуальні кандидати з невизначеностями</span></div><div class="stat"><b>'+str(len(excluded))+'</b><span>відсіяно або поки не включено</span></div><div class="stat"><b>0</b><span>повністю підтверджених відповідностей</span></div></div>'
summary_block+='<div class="notice"><b>«Актуальна сторінка» не означає «підходить за всіма вимогами».</b> Основні перешкоди — невідомі адреси, суміжні висотки, близькість колії, площа та доступність садочка. Прямі виключення: Білогірська, 34; Глибока Долина, 29; Мостова без номера; Вільхова зі спільною стіною; Татарська–Дівоча; низ Коновальця.</div>'
if D.get('landSummary'):summary_block+='<div class="card"><b>Ділянка під будинок: від 6 соток, до $50 000, житлове призначення та комунікації.</b><p>'+E(D['landSummary'])+'</p></div>'
if D.get('decisionSummary'):summary_block+='<div class="card"><b>Пріоритет уточнень і запас коштів</b><p>'+E(D['decisionSummary'])+'</p></div>'
parts=[head,header,'<main class="wrap">',
'<section id="map-section"><h2>Карта Тернополя та передмістя</h2><p class="sectionnote">Номери міток відповідають таблицям. Пунктирна обводка означає приблизний маркер. '+str(len(unknown))+' позицій без надійної прив’язки наведено в панелі поруч: адресну точку для них не встановлено. Садочки й зупинки вмикаються окремими шарами у правому верхньому куті карти.</p><div class="toolbar"><label>На карті <select id="mapfilter"><option value="all">Усі відомі локації</option><option value="active">Актуальні кандидати</option><option value="excluded">Відсіяні / не включені</option></select></label><button id="fitmap">Показати всі мітки</button></div><div class="maplayout"><div id="map"></div><aside class="mapaside"><b>Адреса не встановлена</b><ul>'+''.join('<li><a href="#row-'+E(r['id'])+'">'+str(r['number'])+'. '+E(r['address'])+'</a><br><span class="muted">'+E(r['district'])+'</span><br><a target="_blank" rel="noopener" href="'+E(r['map'])+'">Google Maps: пошук місця</a></li>' for r in unknown)+'</ul><p class="small">Google Maps у рядку відкриє пошук вулиці або населеного пункту. Загальна точка міста не використовується для розрахунку відстані.</p></aside></div><div class="legend"><span>актуальний кандидат</span><span class="excluded">відсіяно / не включено</span><span class="kindergarten">садочки</span><span class="stop">зупинки</span><span class="cem">цвинтарі</span><span class="rail">колії</span></div></section>',
'<section id="kindergartens"><h2>Підтверджені садочки в околицях Тернополя</h2><p class="sectionnote">Офіційний запис закладу й точність його мітки перевіряються окремо.</p>'+kindergartenhtml+'</section>',
'<div class="toolbar"><label>Сортування <select id="sort"><option value="district-price">Мікрорайон → ціна</option><option value="distance">Ближче до центру</option><option value="price">За ціною</option></select></label><input id="search" type="search" placeholder="Вулиця, район, причина…" aria-label="Пошук у таблицях"><button onclick="window.print()">Друк / PDF</button><span id="visiblecount" class="small"></span></div>',
'<noscript><p>JavaScript вимкнено: таблиці нижче доступні; інтерактивна карта та перемикачі потребують JS. Фото й деталі показано під кожним рядком.</p><style>.detailrow[hidden]{display:table-row}.detailtoggle{display:none}</style></noscript><section id="active"><h2>Актуальні сторінки</h2><p class="sectionnote">Сторінки прочитані. Прогалини перевірки залишені явними. Невідомі заїзд або номер не приховують варіант; жоден рядок не позначений як повністю придатний.</p>',table(active),'</section>',
'<section id="excluded"><h2>Що відсіяно або не включено</h2><p class="sectionnote">Червоні мітки охоплюють і явні порушення, і варіанти з непідтвердженими обов’язковими умовами. Непідтверджене не прирівнюється до доведеного недоліку. Ці оголошення також мають фото й робочі джерела.</p>',table(excluded),'</section>',
'<section id="cadastre"><h2>Кадастрові сторінки</h2><p class="sectionnote">Наведено лише номери, які прямо вказані в оголошенні або прив’язані до точної адреси. Сторонні кадастрові сторінки мають довідковий характер і можуть містити застарілі дані; перед завдатком потрібні актуальні офіційні витяги щодо кожної ділянки у складі продажу.</p>',cadastrehtml,'</section>',
'<section id="method"><h2>Як читати відстані та висновки</h2><div class="card"><p>'+E(D.get('methodologySummary','Методологія та дати перевірки наведені в картках.'))+'</p><p>Центр — Театральний майдан (49.5537, 25.5948). Відстані по прямій від адресної точки або позначеного приблизного маркера; це не час і не маршрут ходьби.</p><p>'+E(D.get('photoReviewNote',''))+'</p></div></section>',
'<section id="sources"><h2>Проаналізовані сайти</h2><p class="sectionnote">Для прочитаних сторінок вхід не потрібний. 403 / 429 / таймаут означають технічне обмеження, а не продаж. Контактні форми, реєстрація і листування не використовувалися.</p>',sourcehtml,'<p><a href="sources.html">Окремий HTML-список джерел</a></p></section>',
'<section id="automation"><h2>Щоденний пошук Windows</h2><div class="card"><p><b>TernopilHouseSearchDaily · щодня о 09:00 за Києвом.</b> Після успішної перевірки сценарій оновлює latest_report, створює Git-коміт за наявності змін і публікує його через GitHub Pages.</p><p>Потрібні ввімкнений комп’ютер, вхід у Windows, інтернет та чинна авторизація Codex. У разі помилки попередній звіт зберігається. Поштове сповіщення створюється лише для рядка з qualified_all_criteria=true.</p></div></section>',
'<section id="summary-end"><h2>Підсумок перевірки</h2>'+summary_block+'</section>',
'<footer class="foot">Робочі посилання означають, що сторінку вдалося прочитати під час перевірки. Продаж, ціна, адреса та права на землю остаточно підтверджуються продавцем і документами. Підкладка: OpenFreeMap © OpenMapTiles, дані © OpenStreetMap contributors; Leaflet / MapLibre. Фото належать авторам оголошень. Зображення й підкладка карти потребують інтернету; текст, таблиці, мітки та геометрія вбудовані в HTML.</footer></main>']
payload=json.dumps(rows,ensure_ascii=False).replace('</','<\\/')
features=json.dumps(D.get('mapFeatures',[]),ensure_ascii=False).replace('</','<\\/')
js=r'''
const rows=JSON.parse(document.getElementById('records').textContent),features=JSON.parse(document.getElementById('geodata').textContent),byId=Object.fromEntries(rows.map(r=>[r.id,r]));
function esc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const map=L.map('map',{scrollWheelZoom:false}).setView([49.5537,25.5948],12);
const basemap=L.maplibreGL({style:'https://tiles.openfreemap.org/styles/liberty',attributionControl:true}).addTo(map);
const houses=L.layerGroup().addTo(map),rail=L.layerGroup().addTo(map),cem=L.layerGroup().addTo(map),kindergartens=L.layerGroup(),stops=L.layerGroup(),markers={};
const colocated={};for(const r of rows){if(r.coords){const k=r.coords.join(',');(colocated[k]??=[]).push(r.id)}}
for(const f of features){
 const title=esc(f.tags?.name||f.kind);
 if(f.kind==='rail')L.polyline(f.coords,{color:'#465359',weight:2,opacity:.75}).bindPopup(title).addTo(rail);
 if(f.kind==='cemetery')L.polygon(f.coords,{color:'#765587',fillOpacity:.27,weight:1}).bindPopup('Цвинтар · <a target="_blank" href="'+esc(f.url)+'">OSM</a>').addTo(cem);
 if(f.kind==='kindergarten'||f.kind==='stop'){
 const c=f.coords[0],layer=f.kind==='kindergarten'?kindergartens:stops;
 const official=f.officialUrl?'<br><a target="_blank" rel="noopener" href="'+esc(f.officialUrl)+'">Офіційне підтвердження</a>':'';
 const precision=f.precision?'<br><span class="small">'+esc(f.precision)+'</span>':'';
 L.circleMarker(c,{radius:f.kind==='kindergarten'?5:3,color:f.kind==='kindergarten'?'#178a59':'#20769b',fillOpacity:.75}).bindPopup(title+precision+'<br><a target="_blank" rel="noopener" href="'+esc(f.url)+'">Координати / джерело</a>'+official).addTo(layer);
 }
}
for(const r of rows){
 const body=document.querySelector('.property[data-id="'+r.id+'"]');body.id='row-'+r.id;
 if(!r.coords)continue;
 const group=colocated[r.coords.join(',')],offset=(group.indexOf(r.id)-(group.length-1)/2)*32;
 const icon=L.divIcon({className:'pin '+(r.section==='active'?'':'reject ')+(!r.numberKnown?'approx':''),html:String(r.number),iconSize:[30,30],iconAnchor:[15-offset,15]});
 const p='<div class="popup"><img src="'+esc(r.thumbnail)+'"><p><b>'+esc(r.address)+'</b><br>'+esc(r.district)+' · $'+Number(r.price).toLocaleString('uk-UA')+'</p><p>'+esc(r.mapPrecision)+'</p><p>'+esc(r.reason)+'</p><a href="#row-'+r.id+'">До таблиці</a> · <a href="'+esc(r.map)+'" target="_blank">Google Maps</a></div>';
 markers[r.id]=L.marker(r.coords,{icon,title:r.number+'. '+r.address}).bindPopup(p).addTo(houses);
}
L.control.layers({}, {'Будинки й ділянки':houses,'Колії':rail,'Цвинтарі':cem,'Садочки':kindergartens,'Зупинки':stops},{collapsed:true}).addTo(map);
L.control.scale({imperial:false}).addTo(map);
L.circleMarker([49.5537,25.5948],{radius:6,color:'#bd9c45',fillColor:'#fff1a6',fillOpacity:1}).bindPopup('Театральний майдан · орієнтир центру').addTo(map);
function fit(){const visible=rows.filter(r=>r.coords&&(document.getElementById('mapfilter').value==='all'||r.section===document.getElementById('mapfilter').value));if(visible.length)map.fitBounds(visible.map(r=>r.coords),{padding:[35,35],maxZoom:14});}
function mapfilter(){const v=document.getElementById('mapfilter').value;for(const r of rows){const m=markers[r.id];if(m){if(v==='all'||r.section===v)houses.addLayer(m);else houses.removeLayer(m);}}fit();}
document.getElementById('mapfilter').addEventListener('change',mapfilter);document.getElementById('fitmap').addEventListener('click',fit);fit();
document.querySelectorAll('.mapjump').forEach(b=>b.addEventListener('click',()=>{const r=byId[b.dataset.id],m=markers[r.id];if(!houses.hasLayer(m)){document.getElementById('mapfilter').value='all';mapfilter()}document.getElementById('map-section').scrollIntoView();map.setView(r.coords,17);m.openPopup()}));
document.querySelectorAll('.detailtoggle').forEach(b=>b.addEventListener('click',()=>{const row=document.querySelector('.detailrow[data-detail="'+b.dataset.id+'"]'),open=b.getAttribute('aria-expanded')==='true';b.setAttribute('aria-expanded',String(!open));b.textContent=open?'Деталі перевірки та фото ('+row.querySelectorAll('.gallery img').length+')':'Закрити деталі та фото';row.hidden=open;if(!open)row.scrollIntoView({block:'nearest'})}));
function apply(){
 const mode=document.getElementById('sort').value,q=document.getElementById('search').value.toLowerCase().trim();let n=0;
 document.querySelectorAll('.houses').forEach(t=>{
  const items=[...t.querySelectorAll('tbody.property')];items.sort((a,b)=>mode==='price'?+a.dataset.price-+b.dataset.price:mode==='district-price'?(+a.dataset.rank-+b.dataset.rank||+a.dataset.price-+b.dataset.price):(+a.dataset.distance-+b.dataset.distance||+a.dataset.price-+b.dataset.price));
  items.forEach(x=>{t.append(x);const k=document.getElementById('kind').value;const hide=(q&&!x.innerText.toLowerCase().includes(q))||(k!=='all'&&x.dataset.kind!==k);x.classList.toggle('hidden',!!hide);if(!hide)n++});
 });document.getElementById('visiblecount').textContent='Показано '+n+' із '+rows.length+' позицій';
}
document.getElementById('sort').addEventListener('change',apply);document.getElementById('search').addEventListener('input',apply);document.getElementById('kind').addEventListener('change',apply);apply();
'''
parts+=['<script type="application/json" id="records">'+payload+'</script><script type="application/json" id="geodata">'+features+'</script><script>'+leafjs.replace('</script','<\\/script')+'</script><script>'+maplibrejs.replace('</script','<\\/script')+'</script><script>'+maplibreleaflet.replace('</script','<\\/script')+'</script><script>'+js+'</script></body></html>']
report=''.join(parts)
report=report.replace('Зображення й підкладка карти потребують інтернету; текст, таблиці, мітки та геометрія вбудовані в HTML.','Локальні фото, текст і таблиці доступні без інтернету; підкладка карти та зовнішні джерела потребують мережі. Мітки та геометрія вбудовані в HTML.')
report=report.replace('</style></head>','.leaflet-control-layers-toggle{background-image:none!important;display:grid;place-items:center}.leaflet-control-layers-toggle:after{content:"☷";font-size:28px;color:#183842}</style></head>')
report=report.replace('<b>0</b><span>повністю підтверджених відповідностей','<b>'+str(sum(bool(r.get('qualified_all_criteria')) for r in rows))+'</b><span>повністю підтверджених відповідностей')
report=report.replace('<input id="search"','<label>Тип <select id="kind"><option value="all">Будинки й ділянки</option><option value="house">Будинки</option><option value="land">Ділянки</option></select></label><input id="search"')
for r in rows:report=report.replace('<tbody class="property" data-id="'+r['id']+'"','<tbody class="property" data-kind="'+r.get('kind','house')+'" data-id="'+r['id']+'"')
report=report.replace('Карта Тернополя та передмістя','Карта будинків і ділянок Тернополя та передмістя')
report=report.replace('Авторинок і Старий парк збережені в розділі відсіву.','Авторинок і Старий парк збережені в розділі відсіву. Сади Ветеранів АТО, Петриків і Байківці прямо виключені за останнім уточненням користувача.')
report=report.replace('До $120 000 · від 3 соток · окремий будинок · пріоритет від 80 м².', 'До $120 000 · від 3 соток · окремий будинок · пріоритет від 80 м² · відступ стіни від тротуару 1–2 м.')
report=report.replace('повторно використано перевірки попереднього пошуку цього ж дня та переглянуто нові галереї.',E(D.get('photoReviewNote','Дати й обсяг перевірки наведено в картках та джерелах.')))
report=report.replace(' Супутникові знімки можуть бути старішими за оголошення. Рівний двір',' Рівний двір')
report=report.replace('Пунктирна обводка означає приблизний маркер.','Пунктирна обводка означає приблизний маркер. Якщо оголошення мають однакові координати, значки розсунуті на екрані; координати не змінені.')
(O/'report.html').write_text(report,encoding='utf8')
(O/'sources.html').write_text(head+header.replace('href="#','href="report.html#')+'<main class="wrap"><h2>Проаналізовані сайти</h2>'+sourcehtml+'</main></body></html>',encoding='utf8')
(O/'listings.json').write_text(json.dumps(D,ensure_ascii=False,indent=2),encoding='utf8')
geo={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':r['coords'][::-1]},'properties':{k:r.get(k) for k in ['number','id','kind','address','district','price','section','mapPrecision','reason','map']}} for r in rows if r.get('coords')]}
(O/'houses.geojson').write_text(json.dumps(geo,ensure_ascii=False,indent=2),encoding='utf8')
md=['# Будинки й ділянки Тернополя — '+stamp,'',D.get('summary',''),'','## Зміни й обмеження','',D.get('decisionSummary',''),'',D.get('landSummary',''),'']
md+=['- '+x for x in D.get('coverageLimitations',[])]+['']
for title,items in [('Актуальні сторінки',active),('Що відсіяно або не включено',excluded)]:
 md+=['## '+title,'','| № / Об’єкт | Ціна | м² / сотки | Висновок і setback |','|---|---:|---|---|']
 for r in items:
  good=next((s for s in r['sources'] if s.get('verified') and not s.get('removed') and s.get('sourceType')!='cadastre'),None)
  title='['+r['address']+']('+good['url']+')' if good else r['address']+' (сторінка не перевірена / видалена)'
  md+=['| '+str(r['number'])+'. '+title+' | '+str(r.get('priceLabel') or '$'+fmt(r['price']))+' | '+fmt(r['area'])+' / '+fmt(r['land'])+' | '+r['reason']+' Відступ: '+r.get('setback','Не встановлено.')+' |']
 md+=['']
md+=['[Джерела та дати](sources.html) · [Зміни](changes.md) · [Повний звіт із фото](report.html)']
(O/'report.md').write_text('\n'.join(md),encoding='utf8')
print(json.dumps({'report':str(O/'report.html'),'active':len(active),'excluded':len(excluded),'mapMarkers':len(geo['features']),'unknownLocations':len(unknown),'photos':sum(len(r.get('photos',[])) for r in rows)},ensure_ascii=False))
