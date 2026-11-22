const surveyTopics = [
  ["record","각 고객의 제품 구매"],
  ["minimum","고객군 전체 수요"],
  ["reason","제품을 고른 이유"]
];
function surveyQuestion(p, topic, minimum) {
  if (topic==="minimum") return p.name+" 출시 15~28일에 패널 "+minimum+"명 이상에게 구매가 기록될까요?";
  if (topic==="reason") return p.name+"을 보았을 때 어떤 다른 제품과 비교했고, 선택에 가장 영향을 준 점은 무엇인가요?";
  return p.name+" 출시 15~28일에 이 제품을 산 기록이 귀하의 제출 영수증에 한 번 이상 남을까요?";
}
function panelSurveyCard(t) {
  const draft=t.surveyDraft;
  const detail=draft?'<div class="note"><strong>만든 질문</strong><p>'+esc(surveyQuestion(selected(),draft.topic,draft.minimum))+'</p><button class="btn alt" type="button" id="run-ap-survey">이 질문을 패널에 묻기</button></div>':'';
  return '<details id="survey-panel" '+(draft?'open':'')+'><summary>내가 만든 문항으로 패널 조사하기</summary><p class="small" style="margin:9px 0">궁금한 결정을 고르면 이 제품에 맞는 질문을 만듭니다. 구매 결과에 답할 때는 현재 선택한 모형의 확률을 사용합니다.</p><form id="survey-form" class="stack">'+field("survey-topic","알고 싶은 것",select("survey-topic",surveyTopics,draft?.topic||"record"))+
    '<div id="minimum-wrap" '+(draft?.topic==="minimum"?'':'hidden')+'>'+field("survey-minimum","판단할 최소 구매자 수 (명)",'<input type="number" id="survey-minimum" min="1" max="'+currentRow().eligible+'" step="1" value="'+(draft?.minimum||10)+'">')+'</div><div><button class="btn alt" type="submit">문항 만들기</button></div></form>'+detail+'</details>';
}
function surveyQuantile(d, t) {
  let total=0;
  for (let i=0;i<d.probabilities.length;i++) {
    total+=d.probabilities[i];
    if (total>=t) return i;
  }
  return d.tail_from;
}
function runPanelSurvey() {
  const p=selected(), t=trial(), draft=t.surveyDraft, r=currentRow();
  if (!draft) return;
  const question=surveyQuestion(p,draft.topic,draft.minimum);
  let answer;
  if (draft.topic==="reason") {
    answer="이유를 확인할 실제 응답은 0건입니다. 영수증으로는 비교한 대안이나 구매 이유를 알 수 없어 이 문항을 실제 고객 인터뷰 후보로 저장했습니다. 이어서 ‘마지막으로 그렇게 고른 때의 상황을 말씀해 주세요’라고 물을 수 있습니다.";
  } else if (r.expected==null) {
    answer="현재 선정 기준은 판매 명단의 순위만 제공합니다. ‘행동 회귀’나 ‘세 모형 평균’을 고른 뒤 이 문항을 다시 실행하면 기록 구매확률을 집계합니다.";
  } else if (draft.topic==="minimum") {
    const d=r.dist, k=draft.minimum;
    if (!d) answer="이 방법의 패널 합계 분포가 없어 문턱을 넘을 확률을 계산할 수 없습니다. 연구 사례에서 ‘세 모형 평균’을 선택하면 모의조사를 실행할 수 있습니다.";
    else if(k>d.tail_from) {
      const limit=d.tail_probability<.001?"0.1% 미만":(Math.ceil(d.tail_probability*1000)/10).toFixed(1)+"% 이하";
      answer="저장한 분포의 마지막 구간은 "+d.tail_from+"명 이상을 합칩니다. "+k+"명 이상일 확률은 "+limit+"입니다.";
    }
    else {
      const probability=d.probabilities.slice(k).reduce((a,v)=>a+v,0)+d.tail_probability;
      const displayProbability=probability<.001?"0.1% 미만":probability>.999?"99.9% 초과":pct(probability,1);
      answer="각 고객의 기록 구매가 주어진 확률에서 독립이라고 가정하면 "+k+"명 이상이 기록될 모형 확률은 "+displayProbability+"입니다. 전체 적격자는 "+n(r.eligible)+"명입니다.";
    }
    if(t.seen) answer+=" 실제로 기록된 "+n(r.actual)+"명은 설정한 문턱을 "+(r.actual>=k?"충족했습니다.":"밑돌았습니다.");
  } else {
    answer="모형으로 답한 행동 문항입니다. 적격 "+n(r.eligible)+"명의 구매확률을 합하면 ‘구매 기록 있음’은 평균 "+f(r.expected)+"명, ‘구매 기록 없음’은 "+f(r.eligible-r.expected)+"명입니다. 후자에는 영수증을 제출하지 않을 사람도 포함됩니다.";
    if(r.dist) answer+=" 개인 간 독립을 가정한 구매자 수 분포의 가운데 90%는 "+surveyQuantile(r.dist,.05)+"~"+surveyQuantile(r.dist,.95)+"명입니다.";
    if(t.seen) answer+=" 실제 영수증에서 대조한 기록 구매자는 "+n(r.actual)+"명입니다.";
  }
  t.questions.push({text:question,intent:"panel_survey_"+draft.topic,answer,context:p.name+" · "+db.methods[method]+" · 초기 "+r.budget+"명",at:iso()});
  if(t.questions.length>25)t.questions.shift();
  store();display();document.querySelector(".chatlog")?.scrollIntoView({block:"nearest"});
}
function bindPanelSurvey() {
  on("survey-topic",e=>{document.querySelector("#minimum-wrap").hidden=e.target.value!=="minimum";},"change");
  on("survey-form",e=>{
    e.preventDefault();
    const topic=document.querySelector("#survey-topic").value, input=document.querySelector("#survey-minimum");
    if(topic==="minimum"&&!input.reportValidity())return;
    trial().surveyDraft={topic,minimum:topic==="minimum"?Number(input.value):10};
    store();display();document.querySelector("#run-ap-survey")?.focus({preventScroll:true});
  },"submit");
  on("run-ap-survey",runPanelSurvey);
}
const personaMethods = [
  ["full_match","비슷한 합성 프로필","full_match_null"],
  ["full_factors","함께 언급한 음식 요인","full_factors_null"],
  ["full_augment100","실제·합성 이력 혼합","full_augment100_null"]
];
function personaCard(p, t) {
  const all=db.personaComparison?.filter(row=>row.id===p.id);
  if (!all?.length) return "";
  const design=t.personaView||{method:"full_match",budget:0};
  const choice=personaMethods.find(m=>m[0]===design.method)||personaMethods[0];
  const scenarios=[["구매·음식 속성만 사용","direct"],[choice[1],choice[0]],["합성 속성 조합을 섞은 대조",choice[2]]];
  const rows=scenarios.map(([label,key])=>{
    const row=all.find(x=>x.method===key&&x.budget===design.budget);
    if (!row) return "";
    return "<tr><td>"+esc(label)+"</td><td>"+f(row.expected)+"명</td>"+(t.seen?"<td>"+n(row.hits)+" / "+n(row.actual)+"건</td>":"")+"</tr>";
  }).join("");
  return '<details id="persona-compare" '+(t.personaOpen?'open':'')+'><summary>이 제품에 NVIDIA 합성 프로필을 더하면</summary><p class="small" style="margin:9px 0">공개된 한국어 프로필 100만 건의 음식 언급을 영수증 예측에 더한 별도 시험입니다. 같은 고객과 같은 판매 자리로 비교합니다.</p><div class="inlinefields">'+field("persona-method","합성 정보 이용법",select("persona-method",personaMethods.map(m=>m.slice(0,2)),choice[0]))+
    field("persona-budget","이 시험의 초기 관측 설계",select("persona-budget",[[0,"0명"],[80,"80명"]],design.budget))+'</div><div class="tablebox"><table><thead><tr><th>입력</th><th>예상 기록 구매자</th>'+(t.seen?'<th>상위 20% 포착 / 전체 구매</th>':'')+'</tr></thead><tbody>'+rows+'</tbody></table></div><p class="small">표의 예측은 별도 속성 모형으로 다시 계산했습니다. 2026년에 공개된 합성 자료를 2025년 실제 영수증에서 후향 비교했습니다.</p></details>';
}
function bindPersona() {
  const panel=document.querySelector("#persona-compare");
  if (!panel) return;
  panel.ontoggle=()=>{if(panel.isConnected){trial().personaOpen=panel.open;store();}};
  function change() {
    const t=trial();
    t.personaView={method:document.querySelector("#persona-method").value,budget:Number(document.querySelector("#persona-budget").value)};
    t.personaOpen=true;store();display();
  }
  on("persona-method",change,"change");on("persona-budget",change,"change");
}
