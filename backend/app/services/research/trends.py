"""Trend research: idea → semantic keywords → real-world signals → research brief.

Signals (all free; only YouTube needs a key):
  - YouTube + Google search suggestions: what people actually type about this idea
  - Google News (region-aware): fresh, citable facts so scripts aren't invented
  - Google Trends daily feed: what the country is searching today
  - YouTube Data API (optional key): top-viewed recent Shorts for the keywords —
    the hooks/titles that are working right now

The brief is passed to the script writer, and the sources are saved with the
video so the UI can show what each video was inspired by.
"""

import asyncio
import html
import logging
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

from app.core.config import get_settings
from app.services.llm import LLMError, generate_json
from app.services.media.http import TTLCache, client, get_json
from app.services.media.stock import relevance

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=256, ttl=3 * 3600)

MAPPER_PROMPT = """You map a short-video idea to search intent. Reply with JSON only:
{
  "niche": "2-4 words, e.g. 'personal finance', 'indian weddings', 'phone tips'",
  "emotion": "the main feeling the video should trigger (curiosity, nostalgia, awe, FOMO, joy, relief...)",
  "audience": "who this is for in one short phrase",
  "seeds": ["3 short search phrases (2-4 words each) people would type about this idea"],
  "is_personal": true or false   // a private event/story (own wedding, own trip) rather than a public topic
}"""


async def _map_idea(idea: str, language: str) -> Dict[str, Any]:
    def validate(obj):
        seeds = [str(s).strip() for s in (obj.get("seeds") or []) if str(s).strip()][:3]
        if not seeds:
            raise ValueError("no seeds")
        obj["seeds"] = seeds
        return obj

    return await generate_json(
        [{"role": "system", "content": MAPPER_PROMPT},
         {"role": "user", "content": f"Idea: {idea}\nVideo language: {language}"}],
        validate=validate, temperature=0.3, max_tokens=400,
    )


async def _suggestions(seed: str, youtube: bool) -> List[str]:
    s = get_settings()
    key = f"sugg:{youtube}:{seed}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    params = {"client": "firefox", "hl": "en", "gl": s.TREND_REGION, "q": seed}
    if youtube:
        params["ds"] = "yt"
    data = await get_json("https://suggestqueries.google.com/complete/search", params=params)
    out = [x for x in (data[1] if isinstance(data, list) and len(data) > 1 else []) if x.lower() != seed.lower()][:8]
    _cache.set(key, out)
    return out


async def _rss(url: str) -> str:
    try:
        resp = await client().get(url, timeout=10.0)
        return resp.text if resp.status_code == 200 else ""
    except Exception as e:
        logger.info(f"RSS fetch failed {url[:60]}: {e}")
        return ""


def _items(xml: str) -> List[str]:
    return re.findall(r"<item>(.*?)</item>", xml, re.S)


def _tag(item: str, tag: str) -> str:
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", item, re.S)
    return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)).strip()) if m else ""


async def _news(seed: str) -> List[Dict[str, str]]:
    s = get_settings()
    key = f"news:{seed}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    region = s.TREND_REGION
    xml = await _rss(
        f"https://news.google.com/rss/search?q={seed.replace(' ', '+')}+when:1y"
        f"&hl=en-{region}&gl={region}&ceid={region}:en"
    )
    out = []
    for it in _items(xml)[:15]:
        title = _tag(it, "title")
        source = _tag(it, "source")
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        try:
            date = parsedate_to_datetime(_tag(it, "pubDate")).date().isoformat()
        except Exception:
            date = ""
        # Google News matches loosely — keep only headlines that are actually about the seed
        rel = relevance(seed, title)
        if rel >= 0.6:
            out.append({"title": title, "source": source, "date": date, "url": _tag(it, "link"), "rel": rel})
    _cache.set(key, out)
    return out


async def _trending_today() -> List[Dict[str, str]]:
    s = get_settings()
    key = f"trends:{s.TREND_REGION}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    xml = await _rss(f"https://trends.google.com/trending/rss?geo={s.TREND_REGION}")
    out = []
    for it in _items(xml)[:20]:
        out.append({
            "query": _tag(it, "title"),
            "traffic": _tag(it, "ht:approx_traffic"),
            "headline": _tag(it, "ht:news_item_title"),
        })
    _cache.set(key, out)
    return out


async def _top_shorts(seed: str) -> List[Dict[str, Any]]:
    s = get_settings()
    if not s.YOUTUBE_API_KEY:
        return []
    key = f"yt:{seed}"
    cached = _cache.get(key)
    if cached is not None:
        return cached
    after = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    search = await get_json("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "q": f"{seed} #shorts", "type": "video", "videoDuration": "short",
        "order": "viewCount", "publishedAfter": after, "regionCode": s.TREND_REGION,
        "maxResults": 10, "key": s.YOUTUBE_API_KEY,
    }) or {}
    ids = [i["id"]["videoId"] for i in search.get("items", []) if i.get("id", {}).get("videoId")]
    out = []
    if ids:
        stats = await get_json("https://www.googleapis.com/youtube/v3/videos", params={
            "part": "statistics,snippet", "id": ",".join(ids), "key": s.YOUTUBE_API_KEY,
        }) or {}
        for v in stats.get("items", []):
            out.append({
                "title": html.unescape(v["snippet"]["title"]),
                "channel": v["snippet"].get("channelTitle", ""),
                "views": int(v.get("statistics", {}).get("viewCount", 0)),
                "url": f"https://www.youtube.com/shorts/{v['id']}",
            })
        out.sort(key=lambda x: -x["views"])
    _cache.set(key, out[:6])
    return out[:6]


async def gather_research(idea: str, language: str = "English") -> Dict[str, Any]:
    """Run the full research step. Never raises — returns {} if everything fails."""
    s = get_settings()
    if not s.RESEARCH_ENABLED:
        return {}
    try:
        mapping = await _map_idea(idea, language)
    except LLMError as e:
        logger.warning(f"Idea mapping failed: {e}")
        mapping = {"seeds": [" ".join(re.findall(r"\w+", idea)[:4])], "niche": "", "emotion": "", "is_personal": False}
    seeds = mapping["seeds"]
    personal = bool(mapping.get("is_personal"))

    tasks = []
    for seed in seeds:
        tasks += [_suggestions(seed, True), _suggestions(seed, False)]
        if not personal:
            tasks += [_news(seed), _top_shorts(seed)]
    tasks.append(_trending_today())
    results = await asyncio.gather(*tasks, return_exceptions=True)
    results = [r if not isinstance(r, Exception) else [] for r in results]

    searches, news, shorts = [], [], []
    i = 0
    for _ in seeds:
        searches += results[i] + results[i + 1]
        i += 2
        if not personal:
            news += results[i]
            shorts += results[i + 1]
            i += 2
    trending = results[i]

    def dedupe(items, key):
        seen, out = set(), []
        for it in items:
            k = (key(it) or "").lower()
            if k and k not in seen:
                seen.add(k)
                out.append(it)
        return out

    research = {
        "niche": mapping.get("niche", ""),
        "emotion": mapping.get("emotion", ""),
        "audience": mapping.get("audience", ""),
        "is_personal": personal,
        "seeds": seeds,
        "searches": dedupe(searches, lambda x: x)[:12],
        "news": sorted(dedupe(news, lambda x: x["title"]), key=lambda x: (-x["rel"], x["date"]))[:6],
        "top_shorts": sorted(dedupe(shorts, lambda x: x["url"]), key=lambda x: -x["views"])[:6],
        "trending_today": trending[:12],
        "region": s.TREND_REGION,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        f"Research: niche={research['niche']!r} seeds={seeds} searches={len(research['searches'])} "
        f"news={len(research['news'])} shorts={len(research['top_shorts'])} trending={len(trending)}"
    )
    return research


def research_brief(research: Dict[str, Any]) -> str:
    """Compact text block for the writer prompt."""
    if not research:
        return ""
    lines = ["RESEARCH (real data gathered just now — build on it):"]
    if research.get("niche"):
        lines.append(f"- Niche: {research['niche']} · target emotion: {research.get('emotion', '')} · audience: {research.get('audience', '')}")
    if research.get("searches"):
        lines.append("- What people actually search about this: " + "; ".join(research["searches"][:10]))
    if research.get("top_shorts"):
        lines.append("- Top-performing recent Shorts (title — views) — learn the hook style, never copy:")
        lines += [f"    · {v['title']} — {v['views']:,}" for v in research["top_shorts"][:5]]
    if research.get("news"):
        lines.append("- Fresh facts from news (use these instead of inventing numbers; you may name the source):")
        lines += [f"    · {n['title']} ({n['source']}, {n['date']})" for n in research["news"][:5]]
    if research.get("trending_today"):
        lines.append(f"- Trending in {research.get('region', '')} today (tie in ONLY if genuinely related): "
                     + "; ".join(t["query"] for t in research["trending_today"][:10]))
    return "\n".join(lines)


def research_sources(research: Dict[str, Any]) -> Dict[str, Any]:
    """Slim version stored on the video for the 'inspired by' panel."""
    if not research:
        return {}
    return {
        "niche": research.get("niche"),
        "emotion": research.get("emotion"),
        "searches": research.get("searches", [])[:6],
        "news": research.get("news", [])[:4],
        "top_shorts": research.get("top_shorts", [])[:4],
    }
