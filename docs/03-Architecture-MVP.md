# RUGD Intelligence — MVP Architecture
**Version 1.1 | Pilot Phase | November 2026**

## Goal
Deliver a repeatable assessment engine that a non-programmer can direct at a high level. Claude in Cursor performs the majority of implementation. Autonomous loops are minimized and confined to the dedicated PC.

## High-Level Components
1. **Intake Layer**  
   Structured forms or JSON schemas capturing business data, assumptions, and documents. No free-form-only input.
2. **Analysis Layer**  
   - Deterministic financial engine (Python or equivalent) for projections, break-even, sensitivity.  
   - Claude-assisted qualitative analysis strictly bounded by the Methodology document.  
   - Explicit separation of verified inputs vs. generated text.
3. **Scoring & Recommendation Engine**  
   Rule-based application of the Methodology scoring and “recommend against” flags. Human review gate before any client-facing or investor-facing output.
4. **Report Generator**  
   Templated Markdown/PDF output following the required sections in the Methodology, including investor-readiness status.
5. **Audit & Assumption Log**  
   Persistent record of inputs, assumptions, model versions, and AI contributions.
6. **Investor Readiness Gate**  
   Deterministic check against the conditions defined in the Methodology. Release for capital sharing occurs only after human approval.

## Technical Constraints for Pilot
- Run on the dedicated PC only.  
- No background agents or scheduled tasks that access personal data or external accounts without explicit approval.  
- All financial calculations in version-controlled code, unit-tested.  
- Client/pilot data stored in project directories with clear access boundaries.  
- Claude/Cursor sessions reference `/docs` methodology files at the start of every coding task.

## Autonomy Boundaries
- Claude may generate, refactor, and test code within the approved architecture.  
- Claude may not:  
  - Change scoring weights or “recommend against” criteria without documented approval  
  - Introduce new external API costs or paid services  
  - Enable unattended operational decision-making  
  - Expand scope beyond the named pilots  
  - Automate investor outreach, matching, or capital movement
- High-level business decisions (pricing, new verticals, capital spend, go/no-go on features) require explicit user approval.

## Phased Capital Access
- Phase 1 (pilot): manual one-page investor summary only, after human approval.
- Phase 2: curated introductions on explicit request and approval.
- Phase 3: optional explicit API integrations only after documented results and legal review.

## Integration Notes
LongArc autonomous functions remain isolated. Any future shared interfaces use explicit schemas or APIs; no shared runtime on the personal Mac.