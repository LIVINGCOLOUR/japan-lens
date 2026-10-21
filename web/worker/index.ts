// 「AIで本文を読む」の予約を受け付ける API。静的なサイト（out/）は Cloudflare の静的アセットとして配信し、
// /api/* だけをこの Worker が受け持つ（wrangler.jsonc の run_worker_first）。
//
// ここでは AI を呼ばない（API の従量課金を使わないため）。読者がボタンを押した記事を予約として KV に記録し、
// 翌朝の収集（collector/reader.py）が `claude -p`（サブスクリプション）でまとめて読む。
// 読んだ結果は web/data/readings.json に入り、サイトを作り直したときに表示される。
// - 予約できるのは、サイトに載っている記事（/read-index.json）だけ
// - 媒体の robots.txt の確認や本文の取得も collector が行う

interface Env {
  ASSETS: Fetcher;
  READS: KVNamespace;
  LIMITER: RateLimit;
}

type IndexEntry = { url: string; outlet: string; target: string; event: string };

// 予約の一覧（記事の id → 予約した日時）。記事ごとのキーを一覧取得すると KV の list 操作の回数制限に当たるので、1つのキーにまとめる
const QUEUE_KEY = "queue:v1";
// 収集は1日1回なので、それより十分長く残す。読み終えた予約は collector が飛ばすので消さなくてよい
const QUEUE_DAYS = 3;
// 予約の数の上限（いたずらで一覧が膨らまないように）
const QUEUE_MAX = 300;

type Queue = Record<string, string>;
type Result = { status: "queued" | "error"; message: string };

function json(body: Result, status = 200) {
  return Response.json(body, { status, headers: { "cache-control": "no-store" } });
}

async function loadIndex(env: Env, request: Request): Promise<Record<string, IndexEntry>> {
  const res = await env.ASSETS.fetch(new URL("/read-index.json", request.url));
  return res.ok ? res.json() : {};
}

async function loadQueue(env: Env): Promise<Queue> {
  const queue = (await env.READS.get<Queue>(QUEUE_KEY, "json")) ?? {};
  const since = new Date(Date.now() - QUEUE_DAYS * 24 * 60 * 60 * 1000).toISOString();
  return Object.fromEntries(Object.entries(queue).filter(([, at]) => at >= since));
}

const QUEUED_MESSAGE = "AI が本文を読む予約をしました。毎朝6時ごろの更新でまとめて読み、ここに要約と論調を表示します。";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    // collector/reader.py が毎朝取りに来る
    if (url.pathname === "/api/read-queue" && request.method === "GET") {
      return Response.json(await loadQueue(env), { headers: { "cache-control": "no-store" } });
    }
    if (url.pathname !== "/api/read") return env.ASSETS.fetch(request);
    if (request.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

    const { id } = (await request.json().catch(() => ({}))) as { id?: string };
    if (typeof id !== "string" || !/^[0-9a-f-]{36}$/.test(id)) {
      return json({ status: "error", message: "記事の指定が正しくありません。" }, 400);
    }

    const queue = await loadQueue(env);
    if (queue[id]) return json({ status: "queued", message: QUEUED_MESSAGE });

    const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
    const { success } = await env.LIMITER.limit({ key: ip });
    if (!success) return json({ status: "error", message: "短い時間に多くの記事を予約しました。少し待ってから試してください。" }, 429);

    const entry = (await loadIndex(env, request))[id];
    if (!entry) return json({ status: "error", message: "この記事は読み込めません。" }, 404);
    if (Object.keys(queue).length >= QUEUE_MAX) {
      return json({ status: "error", message: "今日は予約が多いため受け付けられません。明日また試してください。" }, 503);
    }

    // 同時に書き込まれると取りこぼすことがあるが、もう一度押せば予約し直せる
    queue[id] = new Date().toISOString();
    await env.READS.put(QUEUE_KEY, JSON.stringify(queue));
    return json({ status: "queued", message: QUEUED_MESSAGE });
  },
} satisfies ExportedHandler<Env>;
