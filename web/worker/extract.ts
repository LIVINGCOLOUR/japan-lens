// 記事ページの HTML から本文を取り出す（collector/body.py と同じ考え方）。
// 多くのサイトが持つ構造化データ（JSON-LD の articleBody）を優先し、なければ段落を集める。

const MAX_CHARS = 12000;

function decode(s: string) {
  return s
    .replace(/<[^>]+>/g, "")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/\s+/g, " ")
    .trim();
}

function fromJsonLd(html: string): string {
  for (const m of html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)) {
    let data: unknown;
    try {
      data = JSON.parse(m[1].trim());
    } catch {
      continue;
    }
    const stack = [data];
    while (stack.length) {
      const x = stack.pop();
      if (Array.isArray(x)) stack.push(...x);
      else if (x && typeof x === "object") {
        const body = (x as Record<string, unknown>).articleBody;
        if (typeof body === "string" && body.length > 200) return body;
        stack.push(...Object.values(x));
      }
    }
  }
  return "";
}

// <p> だけに一致させる（<path> や <picture> を拾わないよう、タグ名の直後は空白か > に限る）
function fromParagraphs(html: string): string {
  const paras = [...html.matchAll(/<p(?:\s[^>]*)?>([\s\S]*?)<\/p>/gi)].map((m) => decode(m[1])).filter((t) => t.length > 40);
  return paras.join("\n");
}

export function extractText(html: string) {
  const text = fromJsonLd(html) || fromParagraphs(html);
  return text.slice(0, MAX_CHARS);
}

export function extractTitle(html: string) {
  const m = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return m ? decode(m[1]) : "";
}
