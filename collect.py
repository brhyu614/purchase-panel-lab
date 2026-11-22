"""Decrypt the researcher's inbox and summarize matched before/after judgments.

    python3 collect.py --owner "/path/to/private/config" --output review.html
    python3 collect.py --owner "/path/to/private/config" --output review.html --files *.json

Network access uses the Firebase CLI login of the researcher. No service secret
is installed in a public website. For offline-only input add --offline.
"""
import argparse
import base64
import collections
import datetime
import html
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def decode(s):
    return base64.urlsafe_b64decode(s+"="*(-len(s)%4))
def decrypt(sealed,key):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    version,iv,wrapped,cipher=sealed.split(".")
    if version!="v1":raise ValueError("알 수 없는 봉투 형식")
    raw=key.decrypt(decode(wrapped),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return json.loads(AESGCM(raw).decrypt(decode(iv),decode(cipher),None))
def fraction(total,den):return "—" if not den else f"{total/den:.1f}명"
def clean(t):return html.escape(str(t or ""),quote=True)
def load_records(args):
    files=list(args.files)
    cfg=json.loads((args.owner/"receiving.json").read_text())
    out=[]; invalid=0
    if not args.offline:
        from cryptography.hazmat.primitives import serialization
        key=serialization.load_pem_private_key((args.owner/"inbox.pem").read_bytes(),password=None)
        f=shutil.which("firebase")
        if not f:raise RuntimeError("Firebase CLI를 찾을 수 없습니다. 원래 연구용 Mac에서 실행하거나 --offline --files로 회신 파일을 불러오세요.")
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"inbox.json"
            route=cfg["path"] if not args.qa else cfg["path"].replace("/r/","/qa/",1)
            subprocess.run([f,"database:get",route,"--project",cfg["project"],"--instance",cfg["instance"],"--output",str(path)],check=True)
            for _,envelope in (json.loads(path.read_text()) or {}).items():
                try:out.append(decrypt(envelope,key))
                except (ValueError,TypeError,KeyError):invalid+=1
    for p in files:
        try:out.append(json.loads(p.read_text()))
        except (OSError,ValueError):invalid+=1
    return out,invalid
def metric(v,m):return '<div><strong>'+clean(v)+'</strong><span>'+clean(m)+'</span></div>'
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--owner",type=Path,required=True);ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--files",nargs="*",type=Path,default=[]);ap.add_argument("--offline",action="store_true");ap.add_argument("--qa",action="store_true")
    args=ap.parse_args()
    records,errors=load_records(args)
    truth=json.loads((args.owner/"outcomes.json").read_text())
    eligible={}
    for row in records:
        if not isinstance(row,dict) or row.get("schema")!="purchase-review-1" or row.get("dataset")!="study" or row.get("release") not in truth:continue
        id_=row.get("session","")
        if not isinstance(id_,str) or not id_:continue
        key=(row["release"],id_)
        previous=eligible.get(key)
        rank=(row.get("updated",""),len(row.get("trials",[])),sum(len(t.get("questions",[])) for t in row.get("trials",[])))
        if previous is None or rank>previous[0]:eligible[key]=(rank,row)
    baseline=after=n_pairs=correct=answered=switched=rank_diff=rank_pairs=0
    items=[];issues=collections.Counter();times=[];arms=collections.defaultdict(list)
    translations={"denominator":"분모·영수증 누락","comparison":"비교 방법","selection":"고객 선정 근거","generalization":"다른 제품 적용","ux":"화면·질문 이해","other":"기타","easy":"쉬웠다","partial":"일부 어려웠다","hard":"어려웠다","panel":"패널의 기록 구매","national":"전국 구매","campaign":"안내의 인과효과","unclear":"분명하지 않음"}
    for i,((release,_),(_,r)) in enumerate(sorted(eligible.items()),1):
        fb=r.get("feedback") or {}; mention=fb.get("issue")
        if mention:issues[translations.get(mention,mention)]+=1
        if fb.get("interpretation"):answered+=1;correct+=fb["interpretation"]=="panel"
        snippets=[]
        for tr in r.get("trials",[]):
            product=truth[release].get(tr.get("case"))
            if not product:continue
            before=tr.get("before") or {};aft=tr.get("after") or {}
            if tr.get("blind") and all(isinstance(x, (int,float)) and not isinstance(x,bool) and 0<=x<=product["eligible"] for x in (before.get("value"),aft.get("value"))):
                baseline+=abs(before["value"]-product["actual"]);after+=abs(aft["value"]-product["actual"]);n_pairs+=1
                switched+=before.get("strategy")!=aft.get("strategy")
                lookup=product.get("ranks",{})
                sk1=before.get("strategy");sk2=aft.get("method") if aft.get("strategy")=="consult" else aft.get("strategy")
                if sk1 in lookup and sk2 in lookup:
                    rank_pairs+=1;rank_diff+=lookup[sk2]-lookup[sk1]
                arms[tr.get("arm","demonstration")].append(abs(before["value"]-product["actual"])-abs(aft["value"]-product["actual"]))
                try:
                    elapsed=(datetime.datetime.fromisoformat(aft["at"].replace("Z","+00:00"))-datetime.datetime.fromisoformat(before["at"].replace("Z","+00:00"))).total_seconds()
                    if elapsed>=0:times.append(elapsed)
                except (ValueError,TypeError,KeyError):pass
                snippets.append("<li>"+clean(product["name"])+" · 첫 예상 "+clean(str(before["value"]))+"명 · 최종 "+clean(str(aft["value"]))+"명 · 실제 "+str(product["actual"])+"명</li>")
            for q in tr.get("questions",[]):
                if isinstance(q,dict):snippets.append("<li>"+clean(product["name"])+" · 질문 “"+clean(q.get("text"))+"”</li>")
        items.append("<article><h3>검토 "+str(i)+"</h3><p>"+clean(translations.get(fb.get("issue"),"쟁점 미표시"))+" · "+clean(translations.get(fb.get("usability"),"이용 난이도 미입력"))+" · "+clean(translations.get(fb.get("interpretation"),"분모 응답 없음"))+"</p><p>"+clean(fb.get("comment"))+"</p><ul>"+"".join(snippets)+"</ul></article>")
    condition_names={"random_advice":"무작위 모형 조언","random_repeat":"무작위 같은 자료 재판단","demonstration":"일반 시연"}
    armtext=" ".join(condition_names.get(k,k)+" "+str(len(v))+"쌍의 평균 오차 감소 "+fraction(sum(v),len(v))+"." for k,v in sorted(arms.items())) or "아직 비교할 가린 판단이 없습니다."
    title="구매 예측 · 연구자 회신함"
    style="body{font:17px/1.6 -apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;background:#f3f6f2;color:#17392f;max-width:980px;margin:40px auto;padding:12px}h1{letter-spacing:-.05em}section,article{background:white;padding:18px 22px;border:1px solid #dce4da;border-radius:12px;margin:12px 0}.metrics{display:flex;flex-wrap:wrap;gap:22px}.metrics strong,.metrics span{display:block}.metrics strong{font-size:1.8rem}.metrics span{font-size:.88rem}li{margin:5px 0}p{white-space:pre-wrap}"
    result="<!doctype html><html lang='ko'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"+title+"</title><style>"+style+"</style><main><h1>"+title+"</h1><p>같은 검토자의 회신은 최신 판을 남깁니다. 가린 전후 판단의 구매자 수는 해당 연구 판본의 고정된 실제 결과와 대조합니다.</p><section class='metrics'>"+metric(str(len(eligible))+"명","검토 회신")+metric(str(n_pairs)+"쌍","가린 전후 판단")+metric(fraction(baseline,n_pairs),"첫 예상 평균 절대오차")+metric(fraction(after,n_pairs),"최종 예상 평균 절대오차")+"</section><section><h2>모형 조언과 재판단</h2><p>"+clean(armtext)+"</p><p>무작위 배정에 동의한 사례에서만 두 조건을 비교합니다. 같은 연구자가 여러 사례에 답할 수 있습니다.</p></section><section><h2>이해와 결정</h2><p>구매자 수의 분모를 올바르게 해석한 검토는 "+str(correct)+" / "+str(answered)+"건입니다. 제안 대상 전략을 변경한 가린 판단은 "+str(switched)+" / "+str(n_pairs)+"쌍입니다. 같은 상위 20%에서 두 전략을 모두 채점할 수 있는 "+str(rank_pairs)+"쌍의 포착 수 차이는 합계 "+str(rank_diff)+"건입니다.</p><p>"+(" · ".join(clean(k)+" "+str(n)+"건" for k,n in issues.most_common()) or "아직 기록된 쟁점이 없습니다.")+"</p></section>"+"".join(items)+("<p>형식을 확인할 수 없는 회신 "+str(errors)+"건</p>" if errors else "")+"<p>전후 차이에는 모형 제안과 반복 판단이 함께 반영됩니다. 사용성 평가는 같은 연구자의 반복 사례를 포함할 수 있습니다.</p></main></html>"
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(result)
    print(json.dumps({"reviewers":len(eligible),"blind_pairs":n_pairs,"invalid":errors,"baseline_sum":baseline,"after_sum":after},ensure_ascii=False))
if __name__=="__main__":main()
