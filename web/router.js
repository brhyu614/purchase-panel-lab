function normalized(input) {
  return typeof input === "string" ? input.normalize("NFKC").replace(/\s+/gu, " ").trim() : "";
}
function matches(text, expressions) {
  return expressions.some(expression => new RegExp(expression, "iu").test(text));
}
function grams(input) {
  const text = normalized(input).toLowerCase().replace(/[^가-힣a-z0-9]/gu, "");
  const set = new Set();
  for (const size of [2, 3]) {
    for (let i = 0; i + size <= text.length; i += 1) set.add(text.slice(i, i + size));
  }
  return set;
}
function similarity(left, right) {
  if (!right.size || !left.size) return 0;
  let common = 0;
  for (const gram of left) if (right.has(gram)) common += 1;
  return (2 * common) / (left.size + right.size);
}
function classifyQuestion(input, config) {
  const text = normalized(input);
  if (!text || text.length > 600) return "out_of_scope";
  if (matches(text, config.authoring) && !/(실명|연락처|휴대전화)/u.test(text)) return "interview";
  if (matches(text, config.scope_guard)) return "out_of_scope";
  for (const [feature, expressions] of config.patterns) {
    if (matches(text, expressions)) return feature;
  }
  const query = grams(text);
  if (!query.size) return "out_of_scope";
  const scores = Object.entries(config.examples).map(([key, candidates]) => [key, Math.max(0, ...candidates.map(s => similarity(query, grams(s))))]);
  scores.sort((a,b) => b[1] - a[1] || (a[0] < b[0] ? 1 : a[0] > b[0] ? -1 : 0));
  const [a,b] = scores;
  return a[1] >= config.fallback_similarity.min && a[1] - b[1] >= config.fallback_similarity.margin ? a[0] : "out_of_scope";
}
