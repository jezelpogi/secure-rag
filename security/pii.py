"""PII detection and reversible redaction using Microsoft Presidio.

One Redactor per request: the same value always maps to the same placeholder
(<PERSON_1>, <EMAIL_ADDRESS_1>, ...) across the question and every chunk, so the
model can still reason about "the same person" without ever seeing the real value.
"""
import re

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

ENTITIES = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "EMPLOYEE_ID"]
NEVER_RESTORE = {"US_SSN"}  # these stay hidden even in the final answer
SCORE_THRESHOLD = 0.35

_analyzer = None


def _get_analyzer():
    """Load Presidio lazily (the spaCy model takes a few seconds) and add a custom recognizer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = AnalyzerEngine()
        _analyzer.registry.add_recognizer(
            PatternRecognizer(
                supported_entity="EMPLOYEE_ID",
                patterns=[Pattern("employee_id", r"\bEMP-\d{5}\b", 0.9)],
            )
        )
    return _analyzer


class Redactor:
    def __init__(self):
        self.forward = {}  # (entity, value) -> placeholder
        self.reverse = {}  # placeholder -> (entity, value)
        self.counts = {}   # entity -> how many distinct values were seen

    def _placeholder(self, entity, value):
        key = (entity, value.strip().lower())
        if key not in self.forward:
            n = self.counts[entity] = self.counts.get(entity, 0) + 1
            placeholder = f"<{entity}_{n}>"
            self.forward[key] = placeholder
            self.reverse[placeholder] = (entity, value)
        return self.forward[key]

    def redact(self, text):
        results = _get_analyzer().analyze(
            text=text, language="en", entities=ENTITIES, score_threshold=SCORE_THRESHOLD
        )
        # Keep the earliest / longest match when detections overlap.
        chosen, last_end = [], -1
        for r in sorted(results, key=lambda r: (r.start, -(r.end - r.start))):
            if r.start >= last_end:
                chosen.append(r)
                last_end = r.end
        # Replace from the end so earlier offsets stay valid.
        for r in reversed(chosen):
            value = text[r.start:r.end]
            end = r.end
            if r.entity_type == "PERSON":
                # spaCy sometimes swallows a possessive ("Priya Raman's"). Keep it outside the
                # placeholder so the same person always maps to the same placeholder.
                value = re.sub(r"['\u2019]s$", "", value)
                end = r.start + len(value)
            text = text[:r.start] + self._placeholder(r.entity_type, value) + text[end:]
        return text

    def restore(self, text):
        """Put real values back into the model's answer, except entity types in NEVER_RESTORE."""
        for placeholder, (entity, value) in self.reverse.items():
            text = text.replace(placeholder, "[REDACTED]" if entity in NEVER_RESTORE else value)
        return text