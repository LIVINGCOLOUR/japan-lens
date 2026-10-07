// robots.txt の簡易パーサー。指定した名乗り（User-agent）にとって、そのパスを読んでよいかを返す。
// グループの選び方と Allow/Disallow の優先順位は RFC 9309 に従う（最も長く一致した規則が勝ち、同じ長さなら Allow）。

type Rule = { allow: boolean; pattern: string };
type Group = { agents: string[]; rules: Rule[] };

function parse(text: string): Group[] {
  const groups: Group[] = [];
  let current: Group | null = null;
  let lastWasAgent = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/#.*$/, "").trim();
    const m = line.match(/^([A-Za-z-]+)\s*:\s*(.*)$/);
    if (!m) continue;
    const key = m[1].toLowerCase();
    const value = m[2].trim();
    if (key === "user-agent") {
      if (!current || !lastWasAgent) {
        current = { agents: [], rules: [] };
        groups.push(current);
      }
      current.agents.push(value.toLowerCase());
      lastWasAgent = true;
    } else if ((key === "allow" || key === "disallow") && current) {
      // 空の Disallow は「すべて許可」なので規則にしない
      if (value) current.rules.push({ allow: key === "allow", pattern: value });
      lastWasAgent = false;
    } else {
      lastWasAgent = false;
    }
  }
  return groups;
}

function matches(pattern: string, path: string) {
  const anchored = pattern.endsWith("$");
  const body = anchored ? pattern.slice(0, -1) : pattern;
  const re = new RegExp("^" + body.split("*").map((s) => s.replace(/[.+?^${}()|[\]\\]/g, "\\$&")).join(".*") + (anchored ? "$" : ""));
  return re.test(path);
}

export function isAllowed(robotsTxt: string, agent: string, path: string) {
  const groups = parse(robotsTxt);
  const name = agent.toLowerCase();
  // 名乗りに一致するグループがあればそれだけを使い、なければ「*」のグループを使う
  let selected = groups.filter((g) => g.agents.some((a) => a !== "*" && name.includes(a)));
  if (selected.length === 0) selected = groups.filter((g) => g.agents.includes("*"));
  let best: Rule | null = null;
  for (const rule of selected.flatMap((g) => g.rules)) {
    if (!matches(rule.pattern, path)) continue;
    if (!best || rule.pattern.length > best.pattern.length || (rule.pattern.length === best.pattern.length && rule.allow)) {
      best = rule;
    }
  }
  return best ? best.allow : true;
}
