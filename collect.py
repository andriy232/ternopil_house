import argparse,datetime,hashlib,json,re,time,urllib.parse
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

parser=argparse.ArgumentParser()
parser.add_argument('--out',required=True)
parser.add_argument('--smoke',action='store_true')
a=parser.parse_args()
ROOT=Path(__file__).resolve().parent
OUT=Path(a.out);OUT.mkdir(parents=True,exist_ok=True)
session=requests.Session()
session.headers.update({'User-Agent':'TernopilHouseSearch/1.0 (personal property monitoring)'})
CATALOGS=[
'https://flatfy.ua/uk/search?geo_id=10023304&has_eoselia=false&land_area_min=3&page=1&price_max=120000&section_id=3&sort=relevance',
'https://flatfy.ua/uk/search?geo_id=10023304&has_eoselia=false&land_area_min=3&page=2&price_max=120000&section_id=3&sort=relevance',
'https://dom.ria.com/uk/prodazha-domov/ternopol/',
'https://dom.ria.com/uk/prodazha-domov/velykye-gay/',
'https://dom.ria.com/uk/prodazha-domov/podgorodnoe-obl-ternopolskaya/',
'https://lun.ua/sale/ternopil/houses',
'https://lun.ua/sale/ternopil/houses-velyki-hai',
'https://lun.ua/sale/ternopil/houses-pidhorodnie',
'https://rieltor.ua/ternopol/houses-sale/',
'https://rieltor.ua/ternopol/areas-sale/',
'https://lun.ua/sale/ternopil/land',
'https://vison.te.ua/zem_uchastki_prodaga/',
'https://dom.ria.com/uk/prodazha-uchastkov/ternopol-pod-zastroyku/',
'https://www.olx.ua/uk/nedvizhimost/zemlya/prodazha-zemli/ternopol/',
'https://vison.te.ua/doma_dachi_prodaga/',
'https://www.olx.ua/uk/nedvizhimost/doma/prodazha-domov/ternopol/',
'https://mls.te.ua/Listing.aspx?aptype=1',
'https://lider.org.ua/base.aspx?t=bud']
records=[]; discovered=[]; visited=set()
def fetch(url):
 if url in visited:return None
 visited.add(url); ident=hashlib.sha256(url.encode()).hexdigest()[:16]
 rec={'url':url,'checkedAt':datetime.datetime.now().astimezone().isoformat(),'id':ident}
 try:
  r=session.get(url,timeout=35);rec.update(status=r.status_code,finalUrl=r.url)
  if r.status_code==200:
   charset=re.search(br'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)',r.content[:12000],re.I)
   r.encoding=charset.group(1).decode('ascii') if charset else ('windows-1251' if 'vison.te.ua' in url and r.apparent_encoding=='windows-1251' else 'utf-8')
   soup=BeautifulSoup(r.text,'html.parser');rec['title']=soup.title.get_text(' ',strip=True) if soup.title else ''
   rec['structured']=[]
   for s in soup.select('script[type="application/ld+json"]'):
    try:rec['structured'].append(json.loads(s.string or s.get_text()))
    except Exception:pass
   m=re.search(r'window\.INITIAL_STATE\s*=\s*',r.text)
   if m:
    try:
     st=json.JSONDecoder().raw_decode(re.sub(r'\bundefined\b','null',r.text[m.end():]))[0]
     items=st.get('search',{}).get('realties',{}).get('list',[])
     for item in items:
      discovered.append({k:item.get(k) for k in ['id','header','geo','geo_entities','price','price_converted','currency_name','area','area_total','land_area','url_raw','location','text','images','group_id','similar_page_ids']})
     rec['flatfyListingCount']=len(items)
     (OUT/(ident+'-state.json')).write_text(json.dumps(st,ensure_ascii=False),encoding='utf8')
    except Exception as e:rec['stateError']=str(e)
   imgs=[]
   for tag in soup.find_all('img'):
    src=tag.get('src') or tag.get('data-src')
    if src and src.startswith('https://') and any(t in src for t in ['riastatic.com/photos','lunstatic.net','olxcdn.com','ligapic.s3']):imgs.append(src)
   rec['images']=list(dict.fromkeys(imgs))
   for s in soup(['script','style','nav','footer']):s.decompose()
   rec['text']=soup.get_text('\n',strip=True)
   rec['availability']='readable page; inspect text for withdrawn listing'
   (OUT/(ident+'.txt')).write_text(rec['text'],encoding='utf8')
  else:rec['availability']='unverified: HTTP error does not mean sold'
 except Exception as e:rec.update(status=None,error=str(e),availability='unverified: connection failure')
 records.append(rec)
 print(json.dumps({'url':url,'status':rec.get('status'),'title':rec.get('title')},ensure_ascii=False),flush=True)
 time.sleep(0.6)
 return rec
if a.smoke:
 fetch('https://rieltor.ua/ternopol/houses-sale/view/12924108/')
else:
 for u in CATALOGS:fetch(u)
 # Continue a full filtered search until it returns no new listings.
 # Bounded batches leave any additional coverage to the research step.
 for page in range(3,11):
  prev=next((x for x in records if 'flatfy.ua/uk/search?' in x['url'] and 'page='+str(page-1)+'&' in x['url']),None)
  if not prev or prev.get('flatfyListingCount',0)<30:break
  before={x.get('id') for x in discovered}
  u=CATALOGS[0].replace('page=1&','page='+str(page)+'&');CATALOGS.append(u);fetch(u)
  if not ({x.get('id') for x in discovered}-before):break
 for item in discovered:
  u=item.get('url_raw')
  if isinstance(u,str) and u.startswith('https://'):fetch(u)
 if (ROOT/'baseline.json').exists():
  b=json.loads((ROOT/'baseline.json').read_text(encoding='utf-8-sig'))
  for item in b.get('listings',[]):
   if item.get('excludedByGeography'):continue
   for src in item.get('sources',[]):
    u=src if isinstance(src,str) else src.get('url')
    if u and urllib.parse.urlparse(u).scheme=='https':fetch(u)
photo_manifest=[]
if not a.smoke:
 media=OUT/'photos';media.mkdir(exist_ok=True)
 tasks=[]
 for rec in records:
  if rec['url'] in CATALOGS:continue
  for src in rec.get('images',[]):
   if any(t in src for t in ['avatar','logo','static-content']):continue
   tasks.append((rec['url'],src))
 tasks=list(dict.fromkeys(tasks))
 def get_photo(task):
  listing,src=task; ident=hashlib.sha256(src.encode()).hexdigest()[:20]
  result={'listing':listing,'url':src}
  try:
   r=requests.get(src,timeout=20,headers={'User-Agent':'TernopilHouseSearch/1.0'})
   if r.ok and r.headers.get('Content-Type','').startswith('image/'):
    ext='.png' if 'png' in r.headers.get('Content-Type','') else '.webp' if 'webp' in r.headers.get('Content-Type','') else '.jpg'
    target=media/(ident+ext);target.write_bytes(r.content);result['localPath']=str(target)
   else:result['error']='Photo unavailable: HTTP '+str(r.status_code)
  except Exception as e:result['error']=str(e)
  return result
 with ThreadPoolExecutor(max_workers=3) as pool:photo_manifest=list(pool.map(get_photo,tasks))
(OUT/'photos-manifest.json').write_text(json.dumps(photo_manifest,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'live-pages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'discovered.json').write_text(json.dumps(discovered,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'collection-status.json').write_text(json.dumps({'checkedAt':datetime.datetime.now().astimezone().isoformat(),'pages':len(records),'readable':sum(x.get('status')==200 for x in records),'unverified':sum(x.get('status')!=200 for x in records)},indent=2),encoding='utf8')
