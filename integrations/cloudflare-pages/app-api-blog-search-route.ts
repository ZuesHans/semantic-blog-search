// Copy this file to the website repo as:
// app/api/blog-search/route.ts
//
// Required Cloudflare Pages environment variables:
// SEARCH_API_URL=https://api.keronshans.top/search
// SEARCH_API_TOKEN=<same token as semantic-blog-search config.yaml>

export const runtime = "edge";

export async function GET(request: Request) {
  const searchApiUrl = process.env.SEARCH_API_URL;
  const searchApiToken = process.env.SEARCH_API_TOKEN;

  if (!searchApiUrl || !searchApiToken) {
    return Response.json(
      { error: "Search API is not configured" },
      { status: 500 },
    );
  }

  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q")?.trim();
  const topK = searchParams.get("top_k") || "5";

  if (!query) {
    return Response.json({ error: "q is required" }, { status: 400 });
  }

  const upstreamUrl = new URL(searchApiUrl);
  upstreamUrl.searchParams.set("q", query);
  upstreamUrl.searchParams.set("top_k", topK);

  const upstreamResponse = await fetch(upstreamUrl, {
    headers: {
      Authorization: `Bearer ${searchApiToken}`,
    },
  });

  const body = await upstreamResponse.json();
  return Response.json(body, { status: upstreamResponse.status });
}
