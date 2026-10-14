import { defineStore } from 'pinia';

import { logApi, pluginApi, statsApi } from '@/api/v1';
import { fetchWithAuth } from '@/api/http';
import type { PluginMarketItem } from '@/types/extensions';
import { getMarketPluginId, isMarketMetaKey } from '@/utils/marketPluginKey';

interface LogEntry {
  uuid: string;
  [key: string]: unknown;
}

interface CommonState {
  eventSource: AbortController | null;
  log_cache: LogEntry[];
  sse_connected: boolean;
  log_cache_max_len: number;
  startTime: number;
  astrbotVersion: string;
  dashboardVersion: string;
  pluginMarketData: PluginMarketItem[];
}

const toOptionalString = (value: unknown): string | undefined =>
  typeof value === 'string' ? value : undefined;

const toStringOr = (value: unknown, fallback: string): string =>
  typeof value === 'string' ? value : fallback;

const firstStringArray = (...candidates: unknown[]): string[] => {
  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate.filter(
        (value): value is string => typeof value === 'string',
      );
    }
  }
  return [];
};

const normalizePluginMarketEntry = (
  key: string,
  rawPlugin: unknown,
): PluginMarketItem | null => {
  if (isMarketMetaKey(key)) {
    return null;
  }

  const pluginData =
    rawPlugin && typeof rawPlugin === 'object'
      ? (rawPlugin as Record<string, unknown>)
      : {};
  const name =
    typeof pluginData.name === 'string' && pluginData.name.trim()
      ? pluginData.name
      : key;
  const { market_plugin_id: _ignoredMarketPluginId, ...record } = pluginData;
  const item: PluginMarketItem = {
    ...record,
    name,
    desc: toOptionalString(pluginData.desc),
    short_desc: toStringOr(pluginData.short_desc, ''),
    author: pluginData.author,
    repo: toOptionalString(pluginData.repo),
    installed: false,
    version: toStringOr(pluginData.version, '未知'),
    social_link: toOptionalString(pluginData.social_link),
    tags: Array.isArray(pluginData.tags)
      ? pluginData.tags.filter(
          (value): value is string => typeof value === 'string',
        )
      : [],
    logo: toStringOr(pluginData.logo, ''),
    pinned: Boolean(pluginData.pinned),
    stars: typeof pluginData.stars === 'number' ? pluginData.stars : 0,
    updated_at: toStringOr(pluginData.updated_at, ''),
    download_url: toStringOr(pluginData.download_url, ''),
    display_name: toStringOr(pluginData.display_name, ''),
    i18n:
      pluginData.i18n && typeof pluginData.i18n === 'object'
        ? (pluginData.i18n as Record<string, unknown>)
        : {},
    astrbot_version: toStringOr(pluginData.astrbot_version, ''),
    category: toStringOr(pluginData.category, ''),
    support_platforms: firstStringArray(
      pluginData.support_platforms,
      pluginData.support_platform,
      pluginData.platform,
    ),
  };
  const marketPluginId = getMarketPluginId(item);
  if (marketPluginId) {
    item.market_plugin_id = marketPluginId;
  }
  return item;
};

const normalizePluginMarketData = (marketData: unknown): PluginMarketItem[] => {
  if (!marketData || typeof marketData !== 'object') {
    return [];
  }

  return Object.entries(marketData).flatMap(([key, rawPlugin]) => {
    const item = normalizePluginMarketEntry(key, rawPlugin);
    return item ? [item] : [];
  });
};

const createLogUuid = (): string => {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID();
  }

  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const randomNibble = (Math.random() * 16) | 0;
    const value = char === 'x' ? randomNibble : (randomNibble & 0x3) | 0x8;
    return value.toString(16);
  });
};

export const useCommonStore = defineStore('common', {
  state: (): CommonState => ({
    eventSource: null,
    log_cache: [],
    sse_connected: false,
    log_cache_max_len: 1000,
    startTime: -1,
    astrbotVersion: '',
    dashboardVersion: '',
    pluginMarketData: [],
  }),
  actions: {
    async createEventSource() {
      if (this.eventSource) {
        return;
      }

      const token = localStorage.getItem('token');
      if (!token) {
        this.sse_connected = false;
        return;
      }

      const controller = new AbortController();
      const { signal } = controller;
      const headers = {
        'Content-Type': 'multipart/form-data',
        Authorization: `Bearer ${token}`,
      };

      const scheduleReconnect = (error: unknown) => {
        if (signal.aborted) {
          return;
        }
        console.error('SSE error:', error);
        this.sse_connected = false;
        this.eventSource = null;
        this.log_cache.push({
          type: 'log',
          level: 'ERROR',
          time: Date.now() / 1000,
          data: 'SSE Connection failed, retrying in 5 seconds...',
          uuid: `error-${Date.now()}`,
        });
        setTimeout(() => {
          void this.createEventSource();
        }, 1000);
      };

      fetchWithAuth(logApi.liveUrl(), {
        method: 'GET',
        headers,
        signal,
        cache: 'no-cache',
      })
        .then((response) => {
          if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
              this.sse_connected = false;
              this.eventSource = null;
              return;
            }
            throw new Error(`SSE connection failed: ${response.status}`);
          }

          if (!response.body) {
            throw new Error('SSE response body is missing.');
          }

          console.log('SSE stream opened');
          this.sse_connected = true;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let bufferedText = '';

          const processStream = ({
            done,
            value,
          }: ReadableStreamReadResult<Uint8Array>): Promise<void> | void => {
            if (done) {
              console.log('SSE stream closed');
              setTimeout(() => {
                this.eventSource = null;
                void this.createEventSource();
              }, 2000);
              return;
            }

            bufferedText += decoder.decode(value, { stream: true });
            const segments = bufferedText.split('\n\n');
            bufferedText = segments.pop() || '';

            segments.forEach((segment) => {
              const line = segment.trim();
              if (!line.startsWith('data: ')) {
                return;
              }

              const logLine = line.replace('data: ', '').trim();
              if (!logLine) {
                return;
              }

              try {
                const parsed = JSON.parse(logLine);
                const logObject =
                  parsed && typeof parsed === 'object'
                    ? (parsed as LogEntry)
                    : ({ uuid: createLogUuid(), data: parsed } as LogEntry);
                if (!logObject.uuid) {
                  logObject.uuid = createLogUuid();
                }

                this.log_cache.push(logObject);
                if (this.log_cache.length > this.log_cache_max_len) {
                  this.log_cache.splice(
                    0,
                    this.log_cache.length - this.log_cache_max_len,
                  );
                }
              } catch (error) {
                console.warn(
                  'Failed to parse SSE log line, skipping:',
                  error,
                  logLine,
                );
              }
            });

            return reader.read().then(processStream);
          };

          void reader.read().then(processStream).catch(scheduleReconnect);
        })
        .catch(scheduleReconnect);

      this.eventSource = controller;
    },
    closeEventSource() {
      if (this.eventSource) {
        this.eventSource.abort();
        this.eventSource = null;
      }
    },
    getLogCache() {
      return this.log_cache;
    },
    async fetchStartTime() {
      const res = await statsApi.startTime();
      this.startTime = Number(res.data.data.start_time ?? -1);
      return this.startTime;
    },
    setAstrBotVersion(version: unknown, dashboardVersion = '') {
      this.astrbotVersion = String(version || '').replace(/^v/i, '');
      this.dashboardVersion = String(dashboardVersion || '');
    },
    async fetchAstrBotVersion(force = false) {
      if (!force && this.astrbotVersion) {
        return this.astrbotVersion;
      }
      const res = await statsApi.version();
      const data = res.data?.data || {};
      this.setAstrBotVersion(data.version, data.dashboard_version);
      return this.astrbotVersion;
    },
    getStartTime() {
      if (this.startTime !== -1) {
        return this.startTime;
      }
      this.fetchStartTime().catch(() => undefined);
      return this.startTime;
    },
    async getPluginCollections(
      force = false,
      customSource: string | null = null,
    ) {
      if (!force && this.pluginMarketData.length > 0 && !customSource) {
        return Promise.resolve(this.pluginMarketData);
      }

      const res = await pluginApi.market({
        force_refresh: force || undefined,
        custom_registry: customSource || undefined,
      });
      const data = normalizePluginMarketData(res.data.data);
      this.pluginMarketData = data;
      return data;
    },
  },
});
