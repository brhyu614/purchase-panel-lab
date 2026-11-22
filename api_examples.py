"""Ask the configured local gateway for one new illustration from a fixed public prompt.

The browser never calls this tool. Set up your own llmgw account and verify an
inexpensive model using "python3 -m llmgw models deepseek" before providing its name.
"""
import argparse

SCENARIOS={
    "exposure":"가상의 유자 곡물칩을 매장에서 실제로 접했는지를 확인하려 한다.",
    "alternative":"가상의 자두 탄산수와 마지막까지 비교한 다른 음료를 확인하려 한다.",
    "channel":"신제품 간식의 오프라인 구매 기회를 조사하려 한다.",
}
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--model",required=True);parser.add_argument("--scenario",choices=SCENARIOS,default="exposure")
    args=parser.parse_args()
    from llmgw import ask
    prompt=SCENARIOS[args.scenario]+" 한국어로 중립적인 인터뷰 질문 하나와 후속 질문 하나를 써 주세요. 구매 동기나 결과를 가정하지 마세요."
    result=ask(prompt,provider="deepseek",model=args.model,temperature=0,cache=True,tag="purchase-panel-public-question",max_tokens=1000)
    print(result)
if __name__=="__main__":main()
