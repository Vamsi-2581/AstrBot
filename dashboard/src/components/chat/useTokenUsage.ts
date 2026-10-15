import { computed, ref, type Ref } from 'vue';
import { providerApi } from '@/api/v1';
import {
  formatUsagePercent,
  readStoredValue,
  readTokenCount,
} from '@/components/chat/chatHelpers';
import type { ChatRecord } from '@/domain/chat';
import {
  contextLimit,
  formatTokenCount,
  type ProviderModelMetadata,
  type ProviderMetadataSource,
} from '@/utils/providerMetadata';

interface TokenProviderConfig extends ProviderMetadataSource {
  id: string;
  enable?: boolean;
}

interface UseTokenUsageOptions {
  tm: (key: string, params?: Record<string, string | number>) => string;
  activeMessages: Ref<ChatRecord[]>;
  isUserMessage: (message: ChatRecord) => boolean;
}

export function useTokenUsage(options: UseTokenUsageOptions) {
  const tokenProviderConfigs = ref<TokenProviderConfig[]>([]);
  const tokenModelMetadata = ref<Record<string, ProviderModelMetadata>>({});
  const selectedTokenProviderId = ref('');

  const currentTokenProvider = computed(() => {
    const selectedProvider = tokenProviderConfigs.value.find(
      (provider) => provider.id === selectedTokenProviderId.value,
    );
    return selectedProvider || tokenProviderConfigs.value[0] || null;
  });

  const currentTokenMetadata = computed(() => {
    const model = currentTokenProvider.value?.model;
    return model ? tokenModelMetadata.value[model] || null : null;
  });

  const latestContextTokens = computed(() => {
    for (
      let index = options.activeMessages.value.length - 1;
      index >= 0;
      index -= 1
    ) {
      const message = options.activeMessages.value[index];
      if (options.isUserMessage(message)) continue;
      const stats = message.content?.agentStats;
      if (!stats) continue;
      if (
        stats.current_context_tokens !== undefined &&
        stats.current_context_tokens !== null
      ) {
        return readTokenCount(stats.current_context_tokens);
      }
      const usage = stats.token_usage;
      if (!usage) continue;
      return (
        readTokenCount(usage.input_other) +
        readTokenCount(usage.input_cached) +
        readTokenCount(usage.output)
      );
    }
    return 0;
  });

  const tokenUsageIndicator = computed(() => {
    const used = latestContextTokens.value;
    const limit = contextLimit(
      currentTokenProvider.value,
      currentTokenMetadata.value,
    );
    if (used <= 0 || limit <= 0) return null;

    const percent = (used / limit) * 100;
    return {
      used,
      limit,
      percent: Math.min(100, Math.max(0, percent)),
      tooltip: options.tm('tokenUsage.tooltip', {
        used: formatTokenCount(used),
        limit: formatTokenCount(limit),
        percent: formatUsagePercent(percent),
      }),
    };
  });

  function syncSelectedTokenProvider() {
    if (typeof window === 'undefined') return;
    selectedTokenProviderId.value = readStoredValue('selectedProvider');
  }

  async function loadTokenProviders() {
    syncSelectedTokenProvider();
    try {
      const response = await providerApi.listByProviderType('chat_completion');
      if (response.data.status === 'ok') {
        tokenModelMetadata.value = (response.data.model_metadata ||
          {}) as Record<string, ProviderModelMetadata>;
        tokenProviderConfigs.value = (
          (response.data.data || []) as unknown as TokenProviderConfig[]
        ).filter((provider) => provider.enable !== false);
      }
    } catch (error) {
      console.error('Failed to load provider context metadata:', error);
    }
  }

  return {
    tokenProviderConfigs,
    tokenModelMetadata,
    selectedTokenProviderId,
    currentTokenProvider,
    currentTokenMetadata,
    latestContextTokens,
    tokenUsageIndicator,
    syncSelectedTokenProvider,
    loadTokenProviders,
  };
}
