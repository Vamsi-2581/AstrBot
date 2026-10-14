export function buildChatRequestFlags(
  enableStreaming = true,
  enableReasoning = true,
) {
  return {
    enable_inline_genui: true,
    enable_default_system_prompt: true,
    enable_streaming: enableStreaming,
    enable_reasoning: enableReasoning,
  };
}
