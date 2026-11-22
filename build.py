"""Build the open-source browser app and an optional, encrypted research edition.

Without arguments the output contains the fictional tutorial only. A private release
JSON is supplied by the study owner. Study release keys and inbox keys stay outside
this source tree. The private JSON must contain aggregate case data only.
"""
import argparse
import base64
import gzip
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")

def serialize(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def plain_demo(language):
    products = [dict(id="yuzu", name="유자 곡물칩", manufacturer="가상 제조사", scope="가상 스낵", sale="2025-04-21", dateLabel="가상 판매 시작", url=""),
                dict(id="plum", name="자두 탄산수", manufacturer="가상 제조사", scope="가상 음료", sale="2025-06-02", dateLabel="가상 판매 시작", url="")]
    methods = {"category":"품목군 구매일 순위", "logit":"행동 회귀", "hierarchy":"계층 구매확률",
               "sequence":"구매 순서 학습", "retrieval":"본인 구매 사례 검색", "blend":"세 모형 평균"}
    rows = []
    for j, prod in enumerate(products):
        actual = [12, 8][j]
        for idx, method in enumerate(methods):
            for budget in ([0] if method=="category" else [0,20,80]):
                slots, hits = 40, 4 + (idx+j)%3
                expected = None if method=="category" else round([13.3,6.1][j]+(idx-2)*0.7+([0,-1.0,0.5][[0,20,80].index(budget)]),1)
                rows.append(dict(id=prod["id"], method=method, budget=budget, update="none" if budget==0 else "global", cohort="fiction", eligible=200, observed=185-j, actual=actual, selected=slots,hits=hits,selected10=20,selected20=40,selected30=60,hits10=hits-2,hits20=hits,hits30=hits+2,first_actual=actual-1,first_hits=hits-1,expected=expected))
    return dict(version="tutorial-v1", products=products, methods=methods, primary="fiction", cohorts={"fiction":"가상 출시 두 건"},rows=rows,language=language)

def render(config):
    web = ROOT/"web"
    template = (web/"shell.html").read_text()
    js="\n".join((web/n).read_text() for n in ("app.js","simulation.js","router.js","survey.js","study.js"))
    return template.replace("/*__CSS__*/",(web/"styles.css").read_text()).replace("__CONFIG__",serialize(config).replace("<","\\u003c")).replace("/*__JS__*/",js)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study",type=Path)
    parser.add_argument("--key-file",type=Path)
    parser.add_argument("--offline",type=Path)
    parser.add_argument("--out",type=Path,default=ROOT/"dist")
    args=parser.parse_args()
    language=json.loads((ROOT/"web/language.json").read_text())
    config={"demo":plain_demo(language)}
    if args.study:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if not args.key_file:
            parser.error("--study requires an existing --key-file")
        key=base64.urlsafe_b64decode(args.key_file.read_text().strip()+"==")
        study=json.loads(args.study.read_text())
        study["language"]=language
        iv=secrets.token_bytes(12)
        encrypted=AESGCM(key).encrypt(iv,gzip.compress(serialize(study).encode(),mtime=0),None)
        config["study"]={"iv":b64(iv),"data":b64(encrypted),"codec":"gzip"}
        if args.offline:
            args.offline.write_text(render({"demo":config["demo"],"embedded":study}))
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"index.html").write_text(render(config))
    (args.out/"robots.txt").write_text("User-agent: *\nDisallow: /\n")
if __name__=="__main__":
    main()
