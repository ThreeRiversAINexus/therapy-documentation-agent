from typing import Any, List, Optional, Sequence
from llama_index.core.base.llms.types import (
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
    ChatMessage,
    MessageRole,
    ChatResponse,
    ChatResponseGen,
)
from llama_index.core.base.llms.base import BaseLLM
from llama_index.core.callbacks import CallbackManager

class MockLLM(BaseLLM):
    """Mock LLM for testing that implements llama-index's LLM interface"""
    
    def __init__(self, callback_manager: Optional[CallbackManager] = None):
        super().__init__(callback_manager=callback_manager or CallbackManager())

    @property
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""
        return LLMMetadata(
            context_window=4096,  # max context length
            num_output=256,  # max output length
            model_name="mock-llm",
            model_version="0.0.1",
            is_function_calling_model=True  # Enable function calling
        )

    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        """Complete the prompt."""
        if "slept well" in prompt.lower():
            response = """I'll help document that information about your sleep.

First, let me record your observation about sleeping well.

I'll use the set_category_observations tool to document this:
{"category_id": "sleep", "observations": "Had a good night's sleep with no dreams"}

That's great to hear you slept well! Not remembering dreams is actually quite common and can sometimes indicate deep sleep. How do you feel after getting such good rest? Do you notice any difference in your energy levels today?"""
        else:
            response = "I understand. Let me help document that information."

        return CompletionResponse(text=response)

    def stream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseGen:
        """Stream complete the prompt."""
        response = self.complete(prompt, formatted=formatted, **kwargs)
        yield response

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        """Chat with the LLM."""
        # Combine all messages into a single prompt
        prompt = "\n".join([f"{msg.role}: {msg.content}" for msg in messages])
        completion_response = self.complete(prompt, **kwargs)
        
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=completion_response.text,
            ),
            raw=completion_response,
        )

    def stream_chat(
        self, messages: Sequence[ChatMessage], **kwargs: Any
    ) -> ChatResponseGen:
        """Stream chat with the LLM."""
        response = self.chat(messages, **kwargs)
        yield response
