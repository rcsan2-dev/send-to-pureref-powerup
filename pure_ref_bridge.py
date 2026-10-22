#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from pathlib import Path
import json, os, re, html, mimetypes, subprocess, threading, webbrowser, time

HOST="127.0.0.1"; PORT=18765
HERE=Path(__file__).resolve().parent
CONFIG_PATH=HERE/"bridge_config.json"
DEFAULT_CONFIG={"pureref_exe":r"C:\Program Files\PureRef\PureRef.exe","root_folder":str(Path.home()/"Documents"/"PureRef_Trello")}
IMAGE_EXTS={".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".svg",".avif",".heic",".heif",".exr",".ppm",".pgm",".pbm",".pnm",".tga",".ico",".jxl",".jp2",".qoi",".dds",".psd",".raw",".xbm",".xpm"}

def load_config():
    c=DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:c.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except:pass
    return c
def save_config(c): CONFIG_PATH.write_text(json.dumps(c,indent=2),encoding="utf-8")
def safe_name(v):
    v=re.sub(r'[\\/:*?"<>|]+',"_",(v or "").strip());v=re.sub(r"\s+"," ",v).strip(" .")
    return v[:140] or "Untitled Card"
def wrap_text(text,w=82):
    words=re.sub(r"\s+"," ",text or "").strip().split();lines=[];line=""
    for word in words:
        c=word if not line else line+" "+word
        if len(c)<=w:line=c
        else:
            if line:lines.append(line)
            line=word
    if line:lines.append(line)
    return lines[:28]
def make_header(card,path):
    lines=wrap_text(card.get("desc",""));h=max(300,150+max(1,len(lines))*30+90)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="{h}">','<rect width="100%" height="100%" fill="#202124"/>','<rect width="14" height="100%" fill="#579dff"/>',f'<text x="52" y="78" fill="#fff" font-family="Segoe UI,Arial" font-size="42" font-weight="700">{html.escape(card.get("name","Untitled Card"))}</text>']
    y=150
    if lines:
        for line in lines:p.append(f'<text x="52" y="{y}" fill="#d0d4db" font-family="Segoe UI,Arial" font-size="22">{html.escape(line)}</text>');y+=30
    else:p.append(f'<text x="52" y="{y}" fill="#7f8794" font-family="Segoe UI,Arial" font-size="22">No card description.</text>')
    if card.get("url"):p.append(f'<text x="52" y="{h-42}" fill="#85b8ff" font-family="Segoe UI,Arial" font-size="17">{html.escape(card["url"])}</text>')
    p.append("</svg>");path.write_text("\n".join(p),encoding="utf-8")
def image_links(text):
    out=[]
    for u in re.findall(r'https?://[^\s<>"\')\]]+',text or "",re.I):
        u=u.rstrip(".,;")
        if Path(urlparse(u).path.lower()).suffix in IMAGE_EXTS:out.append(u)
    return out
def ext_for(url,ct):
    e=Path(urlparse(url).path).suffix.lower()
    if e in IMAGE_EXTS:return e
    e=mimetypes.guess_extension((ct or "").split(";")[0].strip()) if ct else None
    return ".jpg" if e==".jpe" else (e or ".jpg")
def download(url,base):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 SendToPureRef/1.0"})
    with urlopen(req,timeout=35) as r:data=r.read();ct=r.headers.get("Content-Type","")
    p=base.with_suffix(ext_for(url,ct));p.write_bytes(data);return p
def find_pureref(c):
    cand=[c.get("pureref_exe",""),r"C:\Program Files\PureRef\PureRef.exe",r"C:\Program Files (x86)\PureRef\PureRef.exe"]
    la=os.environ.get("LOCALAPPDATA","")
    if la:cand += [str(Path(la)/"PureRef"/"PureRef.exe"),str(Path(la)/"Programs"/"PureRef"/"PureRef.exe")]
    for x in cand:
        if x and Path(x).is_file():return str(Path(x))
    return ""
def paths(payload,c):
    name=safe_name((payload.get("card")or{}).get("name","Untitled Card"))
    root=Path(os.path.expandvars(os.path.expanduser(c.get("root_folder",""))))
    folder=root/name
    return name,root,folder,folder/"references",folder/f"{name}.pur"
def run_pure(exe,commands):
    args=[exe]
    for cmd in commands:args.extend(["-c",cmd])
    subprocess.Popen(args,cwd=str(Path(exe).parent),close_fds=True)
def open_board(payload):
    c=load_config();exe=find_pureref(c)
    if not exe:raise RuntimeError("PureRef executable was not found. Configure the Bridge.")
    *_,pur=paths(payload,c)
    if not pur.exists():raise FileNotFoundError(f"No existing board was found for this card: {pur}")
    run_pure(exe,[f"load;{pur.as_posix()}"]);return str(pur)
def create_board(payload):
    c=load_config();exe=find_pureref(c)
    if not exe:raise RuntimeError("PureRef executable was not found. Configure the Bridge.")
    name,root,folder,refs,pur=paths(payload,c);root.mkdir(parents=True,exist_ok=True);folder.mkdir(parents=True,exist_ok=True);refs.mkdir(parents=True,exist_ok=True)
    if pur.exists():return {"status":"exists","path":str(pur)}
    card=payload.get("card")or{};opt=payload.get("options")or{};src=[]
    if opt.get("includeHeader",True):
        hp=folder/"card_info.svg";make_header(card,hp);src.append(("header",hp))
    urls=[]
    if opt.get("includeCover",True) and payload.get("coverUrl"):urls.append(("cover",payload["coverUrl"]))
    if opt.get("includeAttachments",True):
        for i,a in enumerate(payload.get("attachments")or[],1):
            if a.get("url"):urls.append((f"attachment_{i:02d}",a["url"]))
    if opt.get("includeDescLinks",True):
        for i,u in enumerate(image_links(card.get("desc","")),1):urls.append((f"desc_{i:02d}",u))
    seen=set();downloads=[];fail=[]
    for key,u in urls:
        if not u or u in seen:continue
        seen.add(u)
        try:downloads.append(download(u,refs/safe_name(key)))
        except Exception as e:fail.append({"url":u,"error":str(e)})
    src += [("image",p) for p in downloads]
    (folder/"trello_card.json").write_text(json.dumps({"card":card,"created_at":time.strftime("%Y-%m-%d %H:%M:%S"),"downloaded":[str(p) for p in downloads],"failures":fail},indent=2,ensure_ascii=False),encoding="utf-8")
    cmds=["clearScene"];i=0
    for kind,p in src:
        if kind=="header":cmds.append(f"load;{p.as_posix()};0;-750")
        else:
            col=i%4;row=i//4;cmds.append(f"load;{p.as_posix()};{int((col-1.5)*650)};{row*520}");i+=1
    cmds.append(f"save;{pur.as_posix()}");run_pure(exe,cmds)
    return {"status":"created","path":str(pur),"downloaded":len(downloads),"failed":len(fail),"failures":fail[:10]}

SETTINGS_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><title>Send to PureRef Bridge</title><style>body{font-family:Segoe UI,Arial;background:#191b1f;color:#e9e9ea;margin:0;padding:30px}.wrap{max-width:850px;margin:auto}.box{background:#24272c;border:1px solid #3b4048;border-radius:9px;padding:20px}label{display:block;margin:15px 0 6px;font-weight:600}input{width:100%;padding:10px;background:#15171a;color:#fff;border:1px solid #4b515a;border-radius:5px}button{margin-top:18px;padding:10px 16px;border:0;border-radius:5px;background:#579dff;font-weight:700}.small{color:#a5adba;font-size:13px}.status{margin-top:14px;white-space:pre-wrap}</style></head><body><div class="wrap"><div class="box"><h1>Send to PureRef — Local Bridge R01</h1><p class="small">These paths stay only on this computer.</p><label>PureRef.exe</label><input id="exe"><label>Root folder</label><input id="root"><button onclick="save()">SAVE LOCAL SETTINGS</button><div id="status" class="status"></div></div></div><script>async function load(){const r=await fetch('/config'),j=await r.json();exe.value=j.pureref_exe||'';root.value=j.root_folder||'';status.textContent=j.pureref_found?'PureRef detected.':'PureRef not detected.'}async function save(){const r=await fetch('/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pureref_exe:exe.value,root_folder:root.value})}),j=await r.json();status.textContent=j.ok?'Saved. PureRef detected: '+j.pureref_found:'Failed: '+j.error}load();</script></body></html>'''

class H(BaseHTTPRequestHandler):
    def log_message(self,f,*a):print("[Bridge]",f%a)
    def cors(self):
        self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Methods","GET, POST, OPTIONS");self.send_header("Access-Control-Allow-Headers","Content-Type");self.send_header("Access-Control-Allow-Private-Network","true")
    def js(self,code,obj):
        b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.cors();self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
    def do_OPTIONS(self):self.send_response(204);self.cors();self.send_header("Content-Length","0");self.end_headers()
    def do_GET(self):
        if self.path=="/" or self.path.startswith("/settings"):
            b=SETTINGS_PAGE.encode();self.send_response(200);self.cors();self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b);return
        if self.path.startswith("/health"):
            c=load_config();self.js(200,{"ok":True,"version":"R01","pureref_found":bool(find_pureref(c)),"root_folder":c.get("root_folder","")});return
        if self.path.startswith("/config"):
            c=load_config();c["pureref_found"]=bool(find_pureref(c));self.js(200,c);return
        self.js(404,{"error":"Not found"})
    def readj(self):
        n=int(self.headers.get("Content-Length","0")or 0);return json.loads(self.rfile.read(n).decode()or"{}")
    def do_POST(self):
        try:
            d=self.readj()
            if self.path=="/config":
                c=load_config()
                for k in ("pureref_exe","root_folder"):
                    if k in d:c[k]=d[k]
                save_config(c);self.js(200,{"ok":True,"pureref_found":bool(find_pureref(c))});return
            if self.path=="/create":self.js(200,create_board(d));return
            if self.path=="/open":self.js(200,{"status":"opened","path":open_board(d)});return
            self.js(404,{"error":"Not found"})
        except FileNotFoundError as e:self.js(404,{"error":str(e)})
        except Exception as e:self.js(500,{"error":str(e)})

def main():
    c=load_config()
    if not CONFIG_PATH.exists():save_config(c)
    print(f"Send to PureRef Bridge R01 - http://{HOST}:{PORT}")
    s=ThreadingHTTPServer((HOST,PORT),H);threading.Timer(.6,lambda:webbrowser.open(f"http://{HOST}:{PORT}/")).start()
    try:s.serve_forever()
    except KeyboardInterrupt:pass
if __name__=="__main__":main()
