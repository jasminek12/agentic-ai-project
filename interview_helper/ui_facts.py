"""Short tips shown while the batch question generator runs (no extra LLM calls)."""

INTERVIEW_FACTS: list[str] = [
    "STAR works for behavioral prompts: Situation, Task, Action, Result — keep it under ~90 seconds.",
    "For system design, interviewers often score trade-off clarity more than diagram beauty.",
    "If you're stuck, narrate your assumptions — it mirrors how senior engineers align in real teams.",
    "Big-O matters, but explaining *why* a structure fits the access pattern often wins the point.",
    "Interviewers frequently probe edge cases — empty input, duplicates, concurrency, and failure modes.",
    "A crisp 30-second outline before details signals structured thinking.",
    "Asking one clarifying question can be stronger than guessing silently.",
    "For coding, state your invariants before you optimize — it prevents silent logic bugs.",
    "Behavioral answers land better with one measurable outcome (latency, cost, reliability).",
    "Whiteboard interviews reward communication: think aloud and revise openly.",
    "Many loops test learning: when you miss a hint, show how you'd incorporate feedback.",
    "For leadership stories, conflict + resolution beats conflict + venting.",
    "Read the room: if time is short, prioritize the core path over perfect completeness.",
    "Companies often evaluate ownership: show how you'd follow through after shipping.",
    "If you don't know, propose how you'd find out — tests, profiling, docs, or a teammate.",
]
