"""Legacy compatibility module for Promise Extractor.

FEATURE NOTICE:
This module has been renamed to `ai.promise_extractor` to provide unambiguous,
feature-based naming for engineers and clarify that it extracts customer commitments from transcripts.

Please import directly from `ai.promise_extractor` in all new code.
"""

from ai.promise_extractor import (
    SYSTEM_PROMPT,
    PromiseExtractor,
)

__all__ = [
    "PromiseExtractor",
    "SYSTEM_PROMPT",
]
