"""Offline behavioral interview flashcards (no LLM required)."""

from typing import TypedDict


class Flashcard(TypedDict):
    prompt: str
    framework: str
    checklist: str


CARDS: list[Flashcard] = [
    {
        "prompt": "Tell me about a time you disagreed with your manager.",
        "framework": "STAR in ~90s: Situation → Task → Action → Result. End with what you learned.",
        "checklist": "Name the disagreement without blame · show how you raised it · describe the outcome · reflect on trust.",
    },
    {
        "prompt": "Describe a project that failed or missed a deadline.",
        "framework": "Own the miss early · explain constraints · what you changed next time · metrics if possible.",
        "checklist": "No excuses-only framing · show accountability · concrete follow-up · emotional steadiness.",
    },
    {
        "prompt": "Give an example of working with a difficult teammate.",
        "framework": "Focus on collaboration mechanics: communication, expectations, boundaries, escalation path.",
        "checklist": "Assume good intent · specific behavior (not personality) · how you de-escalated · team impact.",
    },
    {
        "prompt": "Tell me about a time you influenced without authority.",
        "framework": "Stakeholders + data + pilot · build allies · show persistence without steamrolling.",
        "checklist": "Clear ask · evidence · small experiment · how you handled pushback · adoption signal.",
    },
    {
        "prompt": "Describe a high-pressure situation and how you prioritized.",
        "framework": "Triage criteria (customer risk, deadlines) · communicate trade-offs · delegate if relevant.",
        "checklist": "Show judgment under uncertainty · explicit trade-offs · communication cadence · result.",
    },
    {
        "prompt": "Tell me about giving someone hard feedback.",
        "framework": "Private, timely, specific behavior → impact → ask + plan · follow-up.",
        "checklist": "No surprise feedback in a review · examples · empathy · measurable improvement plan.",
    },
    {
        "prompt": "Describe a time you learned something quickly on the job.",
        "framework": "Motivation → resources used → practice loop → outcome · humility + agency.",
        "checklist": "Name sources (docs, mentors, experiments) · timeboxed learning · proof of skill.",
    },
    {
        "prompt": "Why do you want this role / company?",
        "framework": "Bridge your past strengths to their mission/product · 2–3 specifics · curiosity question at end.",
        "checklist": "Avoid generic praise · tie to real work you'd do · show you researched thoughtfully.",
    },
    {
        "prompt": "Tell me about a time you made a decision with incomplete data.",
        "framework": "Define the uncertainty → list assumptions → pick a reversible action → monitor signals and adjust.",
        "checklist": "State risks explicitly · explain why speed/accuracy trade-off was acceptable · show how you validated.",
    },
    {
        "prompt": "Describe a time you took ownership beyond your formal role.",
        "framework": "Spot gap → clarify impact → volunteer ownership → align stakeholders → deliver and hand off sustainably.",
        "checklist": "Show initiative without overstepping · mention coordination · measurable outcome · lasting process change.",
    },
    {
        "prompt": "Tell me about a time you had to say no to a request.",
        "framework": "Acknowledge request → explain constraints/principles → offer alternatives → align on next step.",
        "checklist": "Respectful tone · clear rationale · constructive alternative · preserved relationship.",
    },
    {
        "prompt": "Describe a conflict between two priorities and how you handled it.",
        "framework": "Define competing priorities → apply decision criteria → communicate trade-offs → revisit with new info.",
        "checklist": "Transparent criteria · stakeholder alignment · concrete consequence management · no vague 'balanced both'.",
    },
    {
        "prompt": "Give an example of a time you improved a process.",
        "framework": "Baseline pain point → diagnose root cause → implement change → measure before/after impact.",
        "checklist": "Quantify improvement · highlight adoption plan · show iteration after first rollout.",
    },
    {
        "prompt": "Tell me about a time you handled ambiguous requirements.",
        "framework": "Break ambiguity into clarifying questions → define scope → ship smallest valuable version → refine.",
        "checklist": "Questions asked upfront · alignment artifact (doc/mock) · incremental delivery · reduced rework.",
    },
    {
        "prompt": "Describe a time you had to learn from a critical mistake.",
        "framework": "Own error clearly → immediate mitigation → root-cause analysis → prevention mechanism.",
        "checklist": "No blame shifting · customer/team impact acknowledged · specific prevention control added.",
    },
    {
        "prompt": "Tell me about a time you mentored or supported a teammate.",
        "framework": "Assess current gap → create learning plan → coach with feedback loops → track independence.",
        "checklist": "Concrete coaching actions · growth evidence · avoided micromanagement · team-level benefit.",
    },
    {
        "prompt": "Describe a time you had to persuade a skeptical stakeholder.",
        "framework": "Understand objections first → tailor argument to stakeholder goals → use evidence + pilot → earn commitment.",
        "checklist": "Empathy for concerns · data/examples used · objection handling · final decision and impact.",
    },
    {
        "prompt": "Tell me about a time you delivered bad news.",
        "framework": "Communicate early and directly → provide context and impact → propose recovery options → follow through.",
        "checklist": "No delay/deflection · clear ownership · actionable recovery plan · trust-preserving communication.",
    },
    {
        "prompt": "Give an example of balancing quality and speed.",
        "framework": "Define non-negotiable quality bar → identify safe shortcuts → ship incrementally → monitor and harden.",
        "checklist": "Explicit guardrails · risk mitigation · phased rollout · post-release learnings.",
    },
    {
        "prompt": "Tell me about a time you worked cross-functionally.",
        "framework": "Align on shared objective → define interfaces/ownership → maintain communication cadence → resolve friction fast.",
        "checklist": "Roles clarified early · proactive updates · conflict resolution approach · business outcome.",
    },
    {
        "prompt": "Describe a time you had to prioritize technical debt vs features.",
        "framework": "Quantify debt cost/risk → compare with product impact → propose balanced roadmap → communicate trade-offs.",
        "checklist": "Business framing, not only technical framing · sequencing rationale · stakeholder buy-in.",
    },
    {
        "prompt": "Tell me about a time you adapted after feedback you disagreed with.",
        "framework": "Listen fully → test assumptions objectively → apply what helps → close the loop with results.",
        "checklist": "Shows coachability · no defensiveness tone · evidence-based adjustment · outcome after change.",
    },
    {
        "prompt": "Give an example of leading under tight deadlines.",
        "framework": "Clarify mission-critical scope → assign owners by strengths → short feedback cycles → visible risk tracking.",
        "checklist": "Prioritization discipline · communication rhythm · calm leadership behavior · deadline outcome.",
    },
    {
        "prompt": "Tell me about a time you advocated for the customer.",
        "framework": "Identify customer pain signal → connect to business risk/opportunity → champion fix → validate customer impact.",
        "checklist": "Real customer signal cited · trade-offs acknowledged · tangible impact after change.",
    },
    {
        "prompt": "Describe a time you had to recover from a production issue.",
        "framework": "Stabilize first → communicate incident status → identify root cause → implement durable prevention.",
        "checklist": "Incident triage clarity · stakeholder comms · blameless postmortem · specific guardrails added.",
    },
    {
        "prompt": "Tell me about a time you simplified something complex.",
        "framework": "Understand complexity source → remove unnecessary layers → align on simpler model → verify outcomes.",
        "checklist": "Clear before/after contrast · maintainability gains · no loss of core capability.",
    },
    {
        "prompt": "Give an example of setting boundaries to protect focus or quality.",
        "framework": "Recognize overload risk → set explicit boundaries/priorities → communicate availability and commitments.",
        "checklist": "Professional assertiveness · clarity on trade-offs · improved delivery quality.",
    },
    {
        "prompt": "Tell me about a time you created alignment after a team disagreement.",
        "framework": "Surface differing goals → define shared success metric → evaluate options transparently → commit as a team.",
        "checklist": "Facilitated, not dominated · decision criterion explicit · follow-through after decision.",
    },
]
