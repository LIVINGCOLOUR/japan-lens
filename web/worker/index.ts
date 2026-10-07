// 「AIで本文を読む」の API。静的なサイト（out/）は Cloudflare の静的アセットとして配信し、
// /api/* だけをこの Worker が受け持つ（wrangler.jsonc の run_worker_first）。
//
// 読者がボタンを押したときだけ、その1記事を取得して Claude に要約・論調判定させる。
// - 読んでよいのは、サイトに載っている記事（/read-index.json）だけ
// - 媒体の robots.txt が「人に頼まれて AI が読むこと」（Claude-User）を拒否していれば読まない
// - 一度読んだ結果は KV に保存して使い回す（同じ記事で何度も API を呼ばない）

import Anthropic from "@anthropic-ai/sdk";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { z } from "zod";
import { extractText, extractTitle } from "./extract";
import { isAllowed } from "./robots";

interface Env {
  ASSETS: Fetcher;
  READS: KVNamespace;
  LIMITER: RateLimit;
  ANTHROPIC_API_KEY?: string;
}

type IndexEntry = { url: string; outlet: string; target: string; event: string };

const USER_AGENT =
  "JapanLensReader/0.1 (+https://japan-lens.makoto-monda.workers.dev/about; fetches one article only when a reader asks for an AI summary)";
// robots.txt はこの名乗りと Claude-User（人に頼まれて Claude が読む場合の名乗り）の両方で許可されている必要がある
const ROBOT_AGENTS = ["JapanLensReader", "Claude-User"];
const MODEL = "claude-haiku-4-5";
const CACHE_VERSION = "v1";
const CACHE_TTL = 60 * 60 * 24 * 30; // 読めた結果は30日
const BLOCKED_TTL = 60 * 60 * 24; // 読めなかった結果は1日（サイト側の設定が変わることがあるので短め）

const Reading = z.object({
  summary_ja: z.string(),
  angle: z.string(),
  tone: z.enum(["crit", "neu", "fav", "none"]),
  evidence: z.string(),
});

type Result =
  | ({ status: "ok"; title: string } & z.infer<typeof Reading>)
  | { status: "blocked" | "unavailable" | "error"; message: string };

const SYSTEM = `あなたは海外メディアの日本報道を比較するニュースサイトの編集者です。
読者の依頼で、1本の記事の本文を読んで次をまとめます。
- summary_ja: 記事が何を伝えているかを日本語で3〜4文。記事に書かれていないことは足さない。原文をそのまま訳さず要点をまとめる。
- angle: 記事が何に焦点を当てているかを12字以内で。
- tone: 「評価の対象」に対する記事の見方。"crit"（否定的・懸念や批判を強調）、"fav"（肯定的・成果や支持を強調）、
  "neu"（両方が釣り合う、または事実を淡々と伝える）、"none"（評価の対象がない、または手がかりがない）。
  媒体の一般的な評判では判断せず、この記事の本文だけで判断する。
- evidence: 判定の根拠にした語句を本文から原文のまま12語以内で。"none" のときは空文字。
人名がローマ字でしか書かれていない場合は漢字を推測せずカタカナで書く。`;

function json(body: Result, status = 200) {
  return Response.json(body, { status, headers: { "cache-control": "no-store" } });
}

async function loadIndex(env: Env, request: Request): Promise<Record<string, IndexEntry>> {
  const res = await env.ASSETS.fetch(new URL("/read-index.json", request.url));
  return res.ok ? res.json() : {};
}

async function robotsAllows(url: URL) {
  let res: Response;
  try {
    res = await fetch(`${url.origin}/robots.txt`, { headers: { "user-agent": USER_AGENT } });
  } catch {
    return false; // 確認できなければ読まない
  }
  // robots.txt がない（4xx）なら制限なし、サーバーエラーなら読まない（RFC 9309）
  if (res.status >= 400 && res.status < 500) return true;
  if (!res.ok) return false;
  const text = await res.text();
  const path = url.pathname + url.search;
  return ROBOT_AGENTS.every((agent) => isAllowed(text, agent, path));
}

async function read(entry: IndexEntry, env: Env): Promise<Result> {
  const url = new URL(entry.url);
  if (url.hostname === "news.google.com") {
    return { status: "unavailable", message: "この記事は Google News 経由のリンクのため、本文を取得できません。記事は媒体のサイトで読めます。" };
  }
  if (!(await robotsAllows(url))) {
    return { status: "blocked", message: `${entry.outlet} は、AI が記事を読むことを認めていません（robots.txt）。記事は媒体のサイトで読めます。` };
  }
  let html: string;
  try {
    const res = await fetch(url, { headers: { "user-agent": USER_AGENT, accept: "text/html" }, redirect: "follow" });
    if (!res.ok) {
      return { status: "unavailable", message: `記事ページを取得できませんでした（${res.status}）。媒体のサイトで読んでください。` };
    }
    html = await res.text();
  } catch {
    return { status: "unavailable", message: "記事ページを取得できませんでした。媒体のサイトで読んでください。" };
  }
  const text = extractText(html);
  if (text.length < 300) {
    // 有料記事などで本文がページに含まれていない
    return { status: "unavailable", message: "記事ページから本文を取り出せませんでした（有料記事の可能性があります）。" };
  }
  if (!env.ANTHROPIC_API_KEY) {
    return { status: "error", message: "AI による要約はまだ準備中です。" };
  }
  const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const response = await client.messages.parse({
    model: MODEL,
    max_tokens: 1024,
    system: SYSTEM,
    messages: [
      {
        role: "user",
        content: JSON.stringify({ outlet: entry.outlet, event: entry.event, target: entry.target, article_text: text }),
      },
    ],
    output_config: { format: zodOutputFormat(Reading) },
  });
  if (!response.parsed_output) {
    return { status: "error", message: "AI の応答を読み取れませんでした。時間をおいて試してください。" };
  }
  return { status: "ok", title: extractTitle(html), ...response.parsed_output };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname !== "/api/read") return env.ASSETS.fetch(request);
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

    const { id } = (await request.json().catch(() => ({}))) as { id?: string };
    if (typeof id !== "string" || !/^[0-9a-f-]{36}$/.test(id)) {
      return json({ status: "error", message: "記事の指定が正しくありません。" }, 400);
    }

    const key = `read:${CACHE_VERSION}:${id}`;
    const cached = await env.READS.get<Result>(key, "json");
    if (cached) return json(cached);

    // まだ読んでいない記事を読むときだけ回数を制限する（保存済みの結果を返すのは制限しない）
    const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
    const { success } = await env.LIMITER.limit({ key: ip });
    if (!success) return json({ status: "error", message: "短い時間に多くの記事を読み込みました。少し待ってから試してください。" }, 429);

    const entry = (await loadIndex(env, request))[id];
    if (!entry) return json({ status: "error", message: "この記事は読み込めません。" }, 404);

    let result: Result;
    try {
      result = await read(entry, env);
    } catch (e) {
      console.error("read failed", id, e);
      return json({ status: "error", message: "AI による要約に失敗しました。時間をおいて試してください。" }, 502);
    }
    if (result.status === "ok") await env.READS.put(key, JSON.stringify(result), { expirationTtl: CACHE_TTL });
    else if (result.status !== "error") await env.READS.put(key, JSON.stringify(result), { expirationTtl: BLOCKED_TTL });
    return json(result);
  },
} satisfies ExportedHandler<Env>;
