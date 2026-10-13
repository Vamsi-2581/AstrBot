# Web Search

The web search feature gives large language models internet retrieval capability for recent information, which can improve response accuracy and reduce hallucinations to some extent.

AstrBot's built-in web search functionality relies on the large language model's `function calling` capability. If you're not familiar with function calling, please refer to: [Function Calling](/en/use/function-calling).

When using a large language model that supports function calling with the web search feature enabled, you can try saying:

- `Help me search for xxx`
- `Help me summarize this link: https://github.com/Xero-Team/AstrBot`
- `Look up xxx`
- `Recent xxxx`

And other prompts with search intent to trigger the model to invoke the search tool.

## Multi-source retrieval

AstrBot queries every source in the ordered `Web Search Sources` (`websearch_route`) list in parallel, deduplicates the results by canonical URL, and fuses them with RRF (Reciprocal Rank Fusion, k=60) behind a single `web_search` tool. The list order is the priority order: earlier sources carry more weight in the fusion.

- `websearch_route`: the ordered, multi-select source list, defaulting to `["searxng", "duckduckgo"]`.
- `websearch_oversample`: the per-source candidate multiplier, defaulting to 8. Each source fetches `target results × this multiplier` candidates (clamped to each source's limit) before fusion.
- A source that is unconfigured, fails, or times out is skipped without affecting the others; when no source is usable, `web_search` returns a clear error.

Keyless `SearXNG` and `DuckDuckGo` are supported alongside the key-based `Tavily`, `BoCha`, `Baidu AI Search`, `Brave`, `Firecrawl`, `Exa`, and `AnySearch`.

![image](https://files.astrbot.app/docs/source/images/websearch/image.png)

Go to `Configuration`, scroll down to find Web Search, choose and order the sources under `Web Search Sources`, then fill in the API Key for each source you enable.

## SearXNG (self-hosted, keyless)

SearXNG already aggregates Google, Bing, DuckDuckGo, and other engines, making it the preferred keyless multi-source option. First enable `json` in `search.formats` in the instance's `settings.yml`, otherwise the endpoint returns `403`:

```yaml
search:
  formats:
    - html
    - json
```

Then fill in the instance address in `SearXNG Instance URL` (`websearch_searxng_url`), for example `http://127.0.0.1:8080`. For safety, AstrBot only contacts the endpoint you explicitly configure, does not follow redirects, and does not fetch result URLs server-side.

## DuckDuckGo (keyless fallback)

DuckDuckGo works with no configuration and serves as the keyless fallback. It parses results from its HTML endpoint without any extra dependency.

## Tavily

Go to [Tavily](https://app.tavily.com/home) to get an API Key, then fill it in the corresponding configuration item.

If you use Tavily as one of your web search sources, you will get a better experience optimization on AstrBot ChatUI, including citation source display and more:

![](https://files.astrbot.app/docs/source/images/websearch/image1.png)

## BoCha

Get an API Key from the BoCha platform, then fill it in the corresponding configuration item.

## Baidu AI Search

Get an API Key from Baidu Qianfan APP Builder, then fill it in the corresponding configuration item.

## Brave

Get an API Key from Brave Search, then fill it in the corresponding configuration item.

## Firecrawl

Go to [Firecrawl](https://firecrawl.dev) to get an API Key, then fill it in the corresponding configuration item.

## Exa

Go to [Exa](https://dashboard.exa.ai) to get an API Key, then fill it in the corresponding configuration item. Exa is an AI-native search engine that supports keyword and semantic search with category filters, domain restrictions, and date ranges.

## AnySearch

Go to the [AnySearch Console](https://anysearch.com/console/api-keys) to get your API Key, then fill it in the corresponding configuration field.

In addition to general web search, AnySearch can accept a provider-supported domain tag and a `params` object for domain-specific retrieval. Results preserve compatible structured fields as text. `max_results` is limited to 1–10 and the supported result regions are `cn` and `intl`. If the API Key is left empty, it uses anonymous mode with a daily free quota.

## Page extraction

When the source list contains `Tavily`, `Firecrawl`, or `Exa`, AstrBot also exposes the matching page-content extract tools (`tavily_extract_web_page`, `firecrawl_extract_web_page`, `exa_get_contents`). A source that is not in the list does not mount its extract tool.
