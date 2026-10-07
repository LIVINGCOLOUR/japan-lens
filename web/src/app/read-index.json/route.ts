import { getFeed } from "@/lib/data";

// 「AIで本文を読む」で読んでよい記事の一覧。Worker（worker/index.ts）はここにある記事だけを取得する
// （任意の URL を取りに行く踏み台にされないように）。ビルド時に静的な JSON として書き出す
export const dynamic = "force-static";

export async function GET() {
  const feed = getFeed();
  const articles: Record<string, { url: string; outlet: string; target: string; event: string }> = {};
  for (const ev of feed.events) {
    for (const a of ev.articles) {
      if (!a.url.startsWith("http")) continue;
      articles[a.id] = {
        url: a.url,
        outlet: feed.outlets.find((o) => o.id === a.outlet_id)?.name ?? a.outlet_id,
        target: ev.target ?? "",
        event: ev.title_ja,
      };
    }
  }
  return Response.json(articles);
}
