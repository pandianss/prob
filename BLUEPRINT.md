# ProBanker — Master Blueprint v2

An adaptive, misconception-driven tutor for IIBF certifications (JAIIB, CAIIB, specialised diplomas and certificates).

**Status:** design spec, pre-implementation.
**Supersedes:** `Master Blueprint_ AI-Powered Mobile Learning Platform...docx`.

---

## 0. What changed from v1, and why

v1 was strong on pedagogy and Android architecture, and silent on the three things that actually decide whether this ships. This version is organised around them.

| Gap in v1 | Addressed in |
|---|---|
| 60,000 misconception-mapped items asserted as an architecture detail, with no plan to produce them | §3 Content supply chain |
| Tutor could hallucinate statutory facts; no grounding, no citations | §4 Grounding & the no-assertion rule |
| No way to know the tutor is helping rather than harming | §5 Evaluation harness |
| RBI circulars / IIBF syllabi go stale annually; no invalidation path | §3.5 Staleness watcher |
| "≥80% mastery" undefined without an item-difficulty model | §6 Mastery model |
| Fixed 0/1/4/10/30-day SRS ladder, exam-date blind | §7 Scheduling |
| Gemini Nano assumed available; it isn't, on most target devices | §8 Device tiers |
| No business model, no competitor position, no kill criteria | §11, §12 |
| No live regulatory feed; the statute store would rot silently | §13 Regulatory ingestion layer |
| No treatment of supplied courseware, or of what may be shown to learners | §3.6 Licensed courseware as source |
| Capital/liquidity/asset-classification thresholds (CRAR, LCR, NPA, PSL) untracked and entity-blind | §13.6 Parameter register |
| No acquisition surface; ratio practice had no real-world anchor | §14.2 Bank performance by group |
| Pipeline assumed human reviewers; the system must run unattended | §3.7 Autonomous operation |
| Chapter order treated as teaching order, though the source inverts its own prerequisites | §2.5 Syllabus spine vs concept graph |
| Lossy source extraction treated as a blocker rather than a repairable, provable stage | §3.8 Source repair |
| A runtime chatbot that could hallucinate uncaught, cost per session, and need a network | §2.3 Authored ladder |

Cut from v1 scope: Agentic OS / MCP AppFunctions, Rive, XP/streak gamification, on-device Gemini Nano. All are v2+ candidates; none earn their cost before the core loop is proven. Rationale in §10.

---

## 1. The wedge

Oliveboard, Testbook and IIBF's own courseware already sell question banks. A bigger question bank is not a business.

**The claim this product makes:** a question bank tells you *that* you were wrong. This tells you *why* you were wrong, because the wrong answer you picked was authored to mean something specific.

Everything in this spec exists to make that claim true and defensible. If the misconception mapping is sloppy, we are a worse question bank with a higher burn rate.

**Falsifiable version, to be tested in the pilot:** learners on the misconception loop show materially higher 30-day retrieval accuracy than learners on an identical item set with plain right/wrong feedback. Target: +12pp absolute. Below +5pp, the wedge is dead and we should say so (§12).

---

## 2. Pedagogical model

### 2.1 Tiers

Retained from v1, sharpened into different *system behaviours* rather than different tones of voice.

| Tier | Cognitive goal | Item form | Tutor mode | Mastery bar |
|---|---|---|---|---|
| JAIIB / DB&F | Foundational accuracy; remove specific wrong beliefs | Single-step diagnostic, 1 key + 3 misconception distractors | **Remediate** — short, closed, targets one misconception | θ ≥ node threshold, SE < 0.35 |
| CAIIB | Transfer to unseen scenarios | Multi-step scenario, distractors = plausible-but-wrong *methods* | **Inquire** — open, compares the learner's reasoning to an alternative | θ ≥ threshold on ≥2 *unseen* transfer items |
| Specialised diplomas (Treasury, Risk) | Judgement under ambiguity | Case vignette, defensible-alternatives | **Challenge** — argues the opposing position | Rubric-scored, human-sampled |
| Professional certificates (AML/KYC, MSME) | Statutory precision | Clause-anchored recall + scenario application | **Remediate**, citation-forward | Latency-sensitive: correct *and* fast |

The tier does not just change the prompt. It changes item schema, distractor semantics, mastery test, and the escalation budget in §2.3.

### 2.2 Misconception taxonomy

The central asset. Not a tag cloud — a versioned, hierarchical catalogue: model-proposed, then promoted or demoted by live response data (§3.7).

```
Identifier:  <CERT>.<SUBJECT>.<TOPIC>.<SLUG>
Example:     JAIIB.AFM.DEPR.SLM-WDV-CONFLATE
```

Each entry carries:

```yaml
id: JAIIB.AFM.DEPR.SLM-WDV-CONFLATE
statement: >
  Learner applies the straight-line rate to the written-down (net)
  book value, rather than to original cost, producing a declining
  charge under an SLM policy.
signature:                      # how we recognise it
  - selects distractor family D-SLM-ON-WDV
  - error magnitude tracks (cost - accum_dep) / cost
prerequisites: [JAIIB.AFM.DEPR.BASIS-OF-CHARGE]
remediation_strategy: contrast-cases   # see §2.4
canned_hint_l1: "Under SLM, what stays constant year to year — the rate, the base, or the charge?"
canned_hint_l2: "Check which figure you multiplied the rate by."
worked_example_ref: we/afm/depr/slm-vs-wdv
prevalence: 0.31                # measured, updated from live data
authored_by: ...
reviewed_by: ...
last_verified: 2026-09-01
```

The authored rungs are the tutor, not a fallback for it (§2.3). Because they are written at content time rather than generated in session, tutoring works on every device with no inference and no network (§8), and nothing a learner sees can be hallucinated in the moment.

Target catalogue size: ~40–60 misconceptions per JAIIB subject; ~2,000 across the full IIBF surface. That is a two-year asset, not a sprint.

### 2.3 Socratic policy: an authored ladder, not a conversation

v1 said "never reveal the answer" and "escalate after 5 turns." Those conflict, and the conflict is where learners get abandoned.

**P0 resolves it by removing the conversation.** The ladder is authored at content time, one rung per misconception, and no model runs during a learner's session.

```
PROBE ──► NARROW ──► HINT_L1 ──► HINT_L2 ──► WORKED_EXAMPLE ──► RESOLVE
  │         │           │           │                              ▲
  └─────────┴───────────┴───────────┴──── escalation triggers ─────┘
      (authored per misconception, selected by which distractor was chosen)
```

#### Why the runtime model goes

The free-text tutor was the weakest model use in the design, once the rest of the architecture settled around it:

- It is **the only place a hallucination reaches a learner uncaught**. Authoring-time errors are caught by the &sect;3.7 gauntlet; a runtime turn has no gate in front of it.
- Its cost is **recurring per session**, against authoring's one-time cost per item &mdash; and it recurs on exactly the interaction that happens most.
- &sect;4's no-assertion rule already forbids it from stating any fact, so it can only ask questions. The questions worth asking for a known misconception are the same every time, which means they can be written once.
- &sect;8's device tiers mean a network-dependent tutor is unavailable for a large share of sessions anyway. The authored ladder was already the fallback; making it the product removes an entire class of degraded state.

The misconception catalogue (&sect;2.2) already carries `canned_hint_l1` and `canned_hint_l2`; this promotes them from fallback to primary and adds the two probing rungs beside them.

#### What is lost, and why that is acceptable for P0

A learner who types something unanticipated gets a ladder rung rather than a response to what they actually said. That is a real loss, and it is the argument for putting the model back later.

But the claim in &sect;1 is that a *misconception-mapped distractor* produces durable learning. It is not a claim about conversation. Testing the wedge with a free-text tutor in the loop confounds the two: a retention lift could come from either, and we would not know which. **The authored ladder is the cleaner experiment as well as the cheaper product.** If P0 clears the +12pp bar without any runtime model, free text becomes an enhancement to evaluate on its own merits. If it misses, adding a chatbot to a weak misconception model would not have saved it.

#### Selection, budget and escalation

**Rung selection is deterministic**: the chosen distractor names a misconception, and that misconception owns its ladder. No inference, no matching, no ambiguity.

**Budget:** the learner advances a rung per tap, and may skip to any later rung at will. There is no turn budget to exhaust because there are no turns to spend.

**Escalation triggers &mdash; any one jumps the ladder immediately:**
1. Explicit request: a permanent **Show me** control, live from the first rung.
2. Dwell: no interaction for 25 seconds on a rung.
3. Session-length: more than 6 minutes into a session entered during commute hours.
4. Repeat encounter: 3rd+ attempt on this misconception in 14 days &mdash; probing has demonstrably failed here, so open at `WORKED_EXAMPLE`.

**De-escalation:** never. Once past `HINT_L2`, do not return to `PROBE` within a session; it reads as withholding.

**`RESOLVE` always fires.** Every session ends with the correct proposition stated plainly and its citation (&sect;4). "Zero answer revelation" in v1 was an over-rotation: it governs *pacing*, not whether the learner ever gets the answer. A banker who closes the app still not knowing the depreciation base is a failure, not a Socratic success.

**Frustration detection:** dropped. v1 leaned on a sentiment signal and a "44.3% of interventions" figure I could not source. With no free text there is nothing to infer sentiment from, and triggers 1&ndash;4 are behavioural and cheap.

#### When the model comes back

Three conditions, all of which are measurements rather than opinions: P0 clears its retention bar; learner reports (&sect;3.7) show the ladder failing on identifiable misconceptions rather than at random; and the no-assertion rule holds under adversarial testing (E2). At that point free text returns as an **extra rung past `HINT_L2`**, for the minority of sessions that reach it, online only &mdash; never as the first thing a learner meets.

### 2.4 Remediation strategies

Each misconception is assigned one, and it determines what `WORKED_EXAMPLE` renders:

- **contrast-cases** — the same input under both the correct and the mistaken procedure, side by side, difference highlighted. Best for procedural confusions (SLM vs WDV, accrual vs cash).
- **clause-anchor** — the governing text, quoted, with the operative phrase marked. Best for statutory recall (AML thresholds, KYC periodicity).
- **boundary-probe** — three cases: clearly in, clearly out, and the edge. Best for classification errors (MSME categorisation, priority-sector eligibility).
- **quantity-intuition** — order-of-magnitude anchoring. Best for ratio errors (CRAR, provisioning).

Four strategies, each with one rendering component. Not per-misconception bespoke content.

---

### 2.5 Two structures: the syllabus spine and the concept graph

The textbook's 25 units are a *publishing* structure. They are not a learning structure, and the difference is not cosmetic.

**The evidence is in the book itself.** Unit 8 teaches operating leverage as `DOL = Contribution / EBIT`, and its own Check Your Progress sets a question supplying a **P/V ratio of 40%** and asking for DOL. The P/V ratio belongs to cost-volume-profit analysis, which the book teaches in **Unit 12** — four units later. The source asks the learner to apply a concept it has not yet taught.

That is a prerequisite inversion in the published ordering, and no amount of good rendering fixes it. It is also not an error by the authors: a printed book is organised for reference and for a syllabus committee, and a reader is expected to skip around. A scheduler serving one item at a time on a phone has no such freedom.

Three further mismatches:

- **Unit size varies four-fold** (26 to 104 pages). Sessions are 5&ndash;10 minutes (&sect;7). A unit is not a schedulable quantity.
- **Interleaving requires mixing topics** (&sect;7), so delivery order must differ from book order by design.
- **Concepts recur across units.** Contribution and cost behaviour underlie both Unit 8 and Unit 12; discounting underlies Units 9, 10, 14 and 19. Taught unit-by-unit, each is retaught from scratch, and the learner never sees that they are the same idea.

#### The resolution: keep both, for different jobs

These do not compete, because they answer different questions.

| | **Syllabus spine** (theirs) | **Concept graph** (ours) |
|---|---|---|
| Authority | IIBF syllabus, immutable | Ours, revised freely |
| Unit | Syllabus node (`ABFM.B.8.3`) | Concept, sized to one session |
| Ordering | Publication order | Prerequisite DAG |
| Answers | "Is Module C covered?" "Am I ready?" | "What should I see next?" |
| Used by | Coverage accounting, exam-readiness, cut-off mapping, marketing claims | Scheduler, mastery model (&sect;6), interleaving |
| Changes | Only when IIBF revises | Whenever response data says so |

Every item carries **both**: `syllabus_node` for accounting, `concept` plus `prereqs` for delivery. The mapping is many-to-many &mdash; one concept serves several nodes, one node needs several concepts.

**The spine is not optional.** It is what makes "covers the ABFM syllabus" a checkable claim rather than a marketing sentence, it is the vocabulary learners and examiners actually use, and &sect;13.8's exam-cut-off resolution hangs off it. The interface says *Module B, Unit 8* even when the scheduler is working in concepts, because that is the map the learner carries in their head.

#### What the concept graph looks like for ABFM

Roughly seven clusters carry most of Modules B and C &mdash; twelve units' worth of material:

| Concept cluster | Serves units |
|---|---|
| Contribution &amp; cost behaviour | 8 (operating leverage), 12 (CVP, relevant cost) |
| Ratio of percentage changes | 8 (DFL, DOL, combined leverage) |
| Time value &amp; discounting | 9, 10 (capital budgeting), 14 (DCF), 19 (hybrid valuation) |
| Cash-flow estimation | 9, 10, 14 |
| Risk adjustment | 11 (sensitivity, scenario, decision tree), feeding 10 and 14 |
| Relative valuation &amp; multiples | 13, 15, 16 |
| Deal arithmetic | 17 (exchange ratio), 18 (EPS accretion, deal financing) |

Teach contribution once and both Unit 8 and Unit 12 are reachable. Teach discounting once and four units open up. That compression is the return on building our own structure, and it is invisible if the chapter is the unit of work.

Module A is the counter-example worth noting: planning &rarr; organising &rarr; staffing &rarr; directing &rarr; controlling is already a genuine dependency chain, so there our graph and the book's order largely agree. The concept layer is not a reorganisation for its own sake &mdash; where the source ordering is sound, it inherits it.

#### Building it autonomously

Prerequisite edges are hypotheses, and like misconceptions (&sect;3.7) they are **empirically testable**: an edge X &rarr; Y is real if failing X predicts failing Y above base rate. So the same bootstrap-then-validate loop applies &mdash; propose the graph from the text, let response data confirm, demote or add edges.

**Start shallow.** Direct prerequisites only, no deep inference, no attempt at a complete ontology before a single learner has answered anything. An elaborate DAG built on a model's guesses is worse than a flat list, because it routes learners confidently through a sequence nobody has checked. Depth is earned from data.

---

## 3. Content supply chain

**This is 80–90% of the project's cost and the whole of its defensibility.** v1 did not mention it.

### 3.1 Item schema

```yaml
item_id: itm_01J9X...
syllabus_node: JAIIB.AFM.4.2          # IIBF spine — coverage accounting (§2.5)
concept: contribution-and-cost-behaviour  # our graph — delivery order (§2.5)
prereqs: [ratio-arithmetic]
bloom: apply
stem: "..."
options:
  - { id: A, text: "...", key: true }
  - { id: B, text: "...", misconception: JAIIB.AFM.DEPR.SLM-WDV-CONFLATE }
  - { id: C, text: "...", misconception: JAIIB.AFM.DEPR.SALVAGE-IGNORED }
  - { id: D, text: "...", misconception: JAIIB.AFM.ARITH.RATE-AS-FRACTION }
grounding:                            # LEARNER-FACING — statutory authority, §4
  - { source: ICAI.AS10, clause: "para 46", version: "2024-07" }
derived_from:                         # INTERNAL ONLY — never rendered, §3.6
  - { work: macmillan/JAIIB-AFM, edition: "2025", chapter: 12, pages: "180-184" }
psychometrics:                        # populated by calibration, §3.4
  b: 0.42                             # difficulty, logits
  a: 1.08                             # discrimination
  n_responses: 1204
  distractor_pull: { B: 0.31, C: 0.12, D: 0.04 }
provenance:
  drafted_by: llm/gemini-2.5-pro2026-08
  reviewed_by: [sme_014, sme_003]
  approved_at: 2026-09-02
lifecycle:
  state: live                         # draft | review | field | live | retired
  last_verified: 2026-09-02
  supersedes: null
```

**Hard invariants, enforced in CI:**
- Every distractor has a `misconception` id resolving to a live catalogue entry. No orphans, no "none of the above".
- Every item has ≥1 `grounding` citation (statutory, learner-facing) with an explicit source version, and ≥1 `derived_from` entry (internal) where it was authored from courseware.
- No `grounding` entry may point at courseware. Authority is statutory or it is not authority (§3.6).
- No item goes `live` without passing the §3.7 verification gauntlet: entailed key with a located span, independent second-model agreement, and every numeric claim traceable to source.
- `distractor_pull < 0.02` after 500 responses → the distractor is dead weight; flag for rewrite.

That last rule is the quality flywheel. A misconception distractor nobody picks is either a misconception nobody holds or a distractor nobody finds plausible, and either way the item is doing a third less work than it claims.

### 3.2 Pipeline

```
[1] Source ingest      STATUTE STORE: RBI master directions, Acts, AS/Ind-AS
                       COURSEWARE STORE: Macmillan IIBF volumes (§3.6)
                       — kept separate; statute wins on conflict
        ↓              → clause-level chunks, version-stamped
[2] Syllabus map       clause → syllabus node, taken from the COURSEWARE'S OWN
        ↓              structure (chapters are already syllabus-ordered), never
                       inferred; cross-checked that the clause sits in that chapter
        ↓
[3] Misconception      Candidates proposed per topic FIRST, from courseware +
        ↓              statute; unvalidated until response data promotes them (§3.7)
        ↓              (items are written to probe known misconceptions,
                        not the other way round — this ordering is load-bearing)
[4] Draft              LLM drafts N items per (node × misconception), from the
        ↓              courseware passage, constrained to cite the mapped clause
                       and to re-express rather than reproduce (§3.6)
[5] Verification       Model B, independently: answers cold, locates the entailing
        ↓              span, judges each distractor, flags unsourced numbers.
                       Disagreement → DISCARD. No queue, no escalation (§3.7).
[6] Field calibration  Served unscored to live users, ~500 responses
        ↓              → a, b, distractor_pull
[7] Live
```

Step 3 before step 4 is the single most important ordering decision in this document. Generating items and then labelling their distractors post-hoc produces a taxonomy that describes whatever the model happened to write. Authoring misconceptions first produces items that probe what learners actually get wrong.

### 3.3 Cost model (autonomous)

With no review labour (§3.7), the cost structure inverts: per-item cost is inference, and the driver
is no longer time but **yield** — how many drafts survive the verification gauntlet.

| Line | Driver |
|---|---|
| Statute store ingest + chunking | One-off per corpus, then incremental per regulatory event |
| Courseware ingest | One-off per edition |
| Misconception proposal | Per topic, cheap, re-run as data promotes/demotes |
| Item drafting (model A) | Per draft attempt |
| Verification (model B) | Per draft attempt — **paid on rejects too** |
| Storage, serving, calibration | Marginal |

**Yield is the number that matters.** At a 40% survival rate every live item costs 2.5 drafts plus
2.5 verifications; at 15% it costs nearly seven of each. Both are affordable in absolute terms —
this is cents per item, not hundreds of rupees — but yield is also the **health signal for grounding
coverage**. A topic whose yield collapses is telling you the statute store is thin there, and the
right response is to ingest more source, not to loosen the gate.

Instrument yield per syllabus node from the first batch. It is the single most informative number
the content pipeline produces.

**What this changes downstream.** The earlier human-pipeline estimate of ~₹800/item implied
~₹4.8 crore for 60,000 items, and the conclusion that breadth was a multi-year outcome.
**That conclusion no longer holds.** At autonomous cost the binding constraint is grounding
coverage and verification throughput, not money — so target breadth early, and let the
refuse-rather-than-guess rule (§3.7) decide where coverage stops.

### 3.4 Calibration

Standard 2PL IRT, and — with no human reviewer — the empirical backstop of §3.7. Negative discrimination auto-retires the item. Every live session includes 1–2 uncalibrated field items, unscored and unflagged to the learner. At ~500 responses an item graduates or is rejected. This is also how `prevalence` in the misconception catalogue gets real numbers instead of guesses.

### 3.5 Staleness watcher

Regulatory content rots. This is a first-class subsystem, not a maintenance chore.

- Fed by the **regulatory ingestion layer** (§13), which polls RBI / SEBI / IRDAI / PFRDA / IBA and the IIBF syllabus pages.
- On change to a source document, **every item citing that source is immediately moved from `live` to `review`** and pulled from serving.
- Automated re-verification against the new source (§3.7 mechanism 1): items whose key still entails pass straight back to `live`; the rest are discarded and redrafted. Nothing waits on a person.
- The learner-facing rule: it is always better to serve fewer items than to serve a superseded statutory threshold to someone sitting an exam next week.

Items carry `last_verified`. Anything unverified for >12 months is auto-flagged regardless of whether its source changed.

---

### 3.6 Licensed courseware as source

The content supply chain assumes a corpus to author *from*. In practice that corpus is the IIBF courseware (Macmillan), supplied as PDF/TXT.

This materially improves §3.3, and it matters more under autonomous operation (§3.7) than it would have with reviewers. Drafting from an authoritative, syllabus-ordered digest means the model is reorganising material in front of it rather than recalling it, which is the single biggest lever on **verification yield** — a draft anchored to a real passage is far likelier to survive the entailment check. Syllabus mapping (stage 2) comes nearly free, because the books are already syllabus-ordered. Measure the yield lift over the first batch rather than assuming it.

#### Two source stores, two different jobs

Keep the courseware and the statutory corpus separate. They are not interchangeable:

| | **Courseware store** (Macmillan) | **Statute store** (§4.2) |
|---|---|---|
| Supplies | Pedagogy, structure, worked examples, what candidates are expected to know | Authority — the operative text |
| Currency | Lags; revised per edition | Current, feed-tracked (§13) |
| On conflict | Loses | **Wins** |
| Learner-facing | No | Yes |

**When the two disagree, the statute wins and the disagreement is itself a signal** — it means the book has gone stale on that point, and every item derived from that passage needs review. This is the payoff from building §13 alongside: the books give you pedagogical structure, the feed gives you currency, and neither alone is sufficient. A platform built on courseware only would teach the 2024 edition's thresholds indefinitely.

#### Citation: internal provenance vs learner-facing grounding

These are two different fields with two different visibilities, and conflating them is what makes the question "do we cite sources?" feel harder than it is.

- **`derived_from`** — which book, edition, chapter, page range an item was authored from. **Never shown to the learner.** Retained internally, permanently.
- **`grounding`** — the statutory clause the item's correctness rests on. **Shown to the learner**, and required by §4's no-assertion rule.

Dropping textbook attribution from the learner UI is right: the learner is buying a tutor, not a bibliography, and a page reference to a book they may not own is noise. But `derived_from` stays in the record for three reasons that have nothing to do with display:

1. **New editions.** When Macmillan revises a volume, `derived_from` is the blast-radius query (§13.4) for courseware — without it, an edition change is unactionable and you re-verify everything or nothing.
2. **Defence.** If derivation is ever questioned, the ability to show exactly what was derived and how far it was transformed is the whole of the answer. Reconstructing that after the fact is not possible.
3. **Quality triage.** When one chapter's items show anomalous `distractor_pull`, you want to know they share a source passage.

Statutory `grounding` stays learner-facing regardless. It is what stands between the product and a confidently wrong threshold (§4), it costs nothing to display, and a banker genuinely benefits from seeing which Master Direction governs the answer — that is professional literacy, not clutter.

#### Derivation boundary

The requirement is derived content, not reproduced prose — which is also the defensible position, since facts and procedures are not protectable but their expression is. Practically:

- Items are **independently written** to probe a misconception (§3.2 stage 3 ordering makes this natural — the misconception catalogue is authored first, and items are written to test it, not transcribed from the text).
- Explanations and worked examples are **re-expressed**, not lifted. Structure follows the §2.4 strategies, which are ours.
- Where a passage must be quoted for a `clause-anchor` remediation, quote the **statute**, which is government-published, not the textbook's gloss on it.
- Highest-risk zone: closely tracking the books' own worked examples, end-of-chapter question sets, or a distinctive selection and arrangement of material. These attract more protection than the underlying facts. Flag such items in SME review.
- Enforced automatically at §3.2 stage 5: the verifier scores n-gram overlap and near-duplicate similarity between the item (with its explanation) and its `derived_from` passage. Above threshold → redraft, not publish. Cheap, and it is the check a reviewer checkbox would have been standing in for.

**Worth exploring commercially:** IIBF and Macmillan are the incumbent rights-holders for exactly this material and may prefer a licensing arrangement to an adversarial one — a licensed digital tutor built on their courseware is a product they cannot easily build themselves. That is a better position than deriving quietly and hoping, and it converts §15's largest legal risk into a distribution advantage. Worth one conversation before the pilot.

---

### 3.7 Autonomous operation — what replaces the reviewers

**Constraint:** the system runs without manual intervention. No SME review queue, no human tutors, no annual human verification pass. Everything below follows from that.

This is achievable. It is not achievable by deleting the review stage and hoping — §5's E1 gate (factual contradiction <0.5%) was held by two humans, and something has to hold it now. Five mechanisms replace them, and one trade has to be accepted.

#### The governing principle

> **The system authors only what it can verify. Coverage is the variable that gives, never correctness.**

A human reviewer can research an uncertain point and resolve it. An autonomous pipeline cannot, so its only safe response to uncertainty is to **not produce the item**. A topic where the statute store is thin simply goes uncovered, and the learner is told the topic is not covered rather than served something unverified. A smaller, provably-grounded catalogue beats a complete one with an unknown error rate — and unlike a human pipeline, an autonomous one can afford to throw away 60% of its drafts, because drafts are nearly free.

#### 1. Grounding becomes the validator, not the citation

In the human pipeline, `grounding` was a citation attached to an item a person had checked. Now it is the check itself:

- Every item's key must be **entailed by its cited clause** — verified by a separate extraction pass that must locate and return the supporting span. No span, no item.
- Every distractor must be **refuted or unsupported** by the same source.
- Items asserting a number (threshold, ratio, period) must have that number appear in, or be arithmetically derivable from, the cited text. **Numeric claims with no traceable source are rejected outright**, no exceptions — this is where hallucination actually bites (§13.6).

An item that cannot be grounded this way is not escalated. There is nowhere to escalate it to. It is discarded.

#### 2. Adversarial multi-model verification

Draft and verify must not share a model, a prompt or a context:

```
draft (model A, sees courseware + clause)
   ↓
verify (model B, sees ONLY the item + the retrieved clause — never the draft reasoning)
   ↓  independently: answer the item cold; locate the entailing span;
   ↓                 judge each distractor; flag any unsourced number
agreement required on: key, span, distractor validity
   ↓
disagreement → DISCARD (not review — discard)
```

Verifier B answering the item cold and disagreeing with the drafted key is the single highest-value signal available, and it costs one inference. Independence is what makes it work: sharing the drafting rationale with the verifier converts it into an agreement machine.

#### 3. Psychometrics as the empirical quality gate

§3.4's field calibration stops being a nice-to-have and becomes the backstop. The decisive statistic is **discrimination**:

- **`a` < 0 means stronger learners get the item wrong more often than weaker ones.** That is the signature of a *wrong key* or an ambiguous stem. It is detectable with no human and no ground truth beyond the response data.
- **Auto-retire on `a < 0`** at n≥200, immediately and without appeal.
- `a` near zero → the item discriminates nothing; retire at n≥500.
- Anomalous `distractor_pull` on the key (the key attracting fewer responses than a distractor among high-θ learners) → same treatment.

This catches what verification misses, because it tests the item against reality rather than against another model. It is slow — it needs traffic — which is why it is a backstop and not the primary gate.

#### 4. Learner reports as the review queue

The reviewers become the learners. A visible "this looks wrong" control on every item and every tutor turn, with:

- Auto-pull at a threshold that scales with exposure (e.g. ≥3 reports, or ≥1% of recent attempts).
- Reports routed back through mechanism 2 — re-verify the flagged item against source, discard if it fails.
- Report rate per item as a tracked quality metric; a cluster of reports sharing a source passage means that passage's items are all suspect.

Bankers studying for a certification are unusually good at this — they are domain-adjacent, motivated, and will notice a wrong KYC threshold faster than a generalist reviewer would.

#### 5. Misconception discovery from response data

§3.2's ordering — misconceptions authored *before* items — was load-bearing and was a human's job. Autonomously it becomes a two-phase loop:

- **Bootstrap:** the model proposes candidate misconceptions per topic from the courseware and the statute. These are hypotheses, explicitly marked as unvalidated.
- **Validate empirically:** once items are live, cluster wrong answers. A candidate misconception that attracts consistent, systematic selection across multiple items and learners is *real* and gets promoted. One that attracts noise is demoted and its distractors rewritten.

This is better than the human version in one respect — a real misconception is defined by learners actually holding it, which is an empirical claim that response data settles and an SME only estimates. It is worse in another: it needs traffic before it works, so the P0 catalogue ships on unvalidated hypotheses and improves from there. Mark the distinction in the data (`prevalence: null` until measured) so nothing downstream treats a guess as a measurement.

#### The trade, stated plainly

**E4 (pedagogical quality) cannot be fully closed autonomously.** It required κ>0.6 agreement between an LLM judge and human ratings; with no human ratings, the judge is a model grading a model against no anchor, and stacking more judges does not create ground truth.

The honest replacement is to **stop measuring transcript quality and measure the outcome instead**: E6 retention (§5) and misconception resolution rate become the arbiters. A tutoring style that produces durable recall is good, whatever a rubric thinks of it. This is a better target and a much slower signal — weeks, not CI seconds — so prompt and model changes ship with E1/E2/E3/E5 green and their pedagogical effect confirmed only afterwards, by cohort. Build the cohort comparison infrastructure early; it is the only pedagogical feedback the system will ever get.

**E1, E2, E3 and E5 remain fully automatable and remain hard gates.** Nothing about autonomy relaxes them.

#### What this costs, and what it buys

**Buys:** §3.3's cost model inverts. SME review was ~60% of ₹800/item; without it the marginal cost of an item is inference plus storage — cents, not hundreds of rupees. The conclusion in §3.3 that "60,000 items is ₹4.8 crore and therefore a multi-year outcome" **no longer holds**. At autonomous cost, breadth is cheap and the binding constraint moves from money to verification throughput and grounding coverage. Aim wide.

**Costs:** no one is accountable for a statutory error before a learner sees it. Mechanisms 1 and 2 make that rare; mechanisms 3 and 4 catch it after the fact. Residual risk is real and is a business decision, not a technical one. Two things make it tolerable:

- **Refuse rather than guess.** Thin grounding → no coverage → an honest "not covered" in the UI.
- **Say what the system is.** Learners are told the content is machine-generated and machine-verified against cited regulation, with a visible report control and visible citations. That is a defensible and accurate description, and it sets the right expectation — it is also why §3.6's decision to keep statutory `grounding` learner-facing matters more here than it did with humans in the loop.

---

### 3.8 Source repair is a pipeline stage, and it carries its own proof obligation

A text extraction of a printed textbook loses structure: fraction bars, table grids, paragraph breaks. An earlier reading of the ABFM extraction concluded that this made Modules B and C unauthorable. **That was too pessimistic, and the correction matters**, because it moves roughly half the certification from blocked to buildable.

What is actually lost is the *rendering*, not the *content*. Both losses are repairable, and &mdash; this is the part that makes it safe &mdash; repairable **provably**.

#### Flattened formulas

A fraction arrives with its bar gone and its operands adjacent:

```
Degree of Financial Leverage = EBIT EBT = 2,00,000 1,00,000 = 2
```

The operator is not guessed. Each candidate (&divide;, &times;, &minus;, +) is tested against the worked example's own numbers, and only the one reproducing the printed result is accepted. `EBIT / EBT` because 2,00,000 &divide; 1,00,000 = 2, and nothing else fits.

Measured on ABFM: **11 numeric instances, 11 recovered with proof.** Precision is the easy half; recall is the constraint, since only single-line ratio definitions take this shape.

#### Flattened tables

A computation table survives as a row-major stream &mdash; grid gone, but each row label still contiguous with its value vector. Reconstruction gives back rows and columns, and a financial statement is **internally redundant**, so the reconstruction proves itself: one row is the column-wise sum or difference of others.

From Unit 9, reconstructed and proved with no model involved:

```
Earnings before tax  = Earnings before tax and depreciation - Depreciation
Net Cash flow        = Earnings after tax                   + Depreciation
```

Measured: **24 candidate tables across Modules B and C, 10 internally proved (42%).** A table that proves itself is stronger evidence than a clean PDF render would be, because consistency is checked rather than assumed.

#### The rule

> Repaired source enters the corpus only with its proof attached. A formula whose operator cannot be pinned by a numeric instance, and a table no internal identity confirms, are **not repaired &mdash; they are discarded**, exactly as an unverifiable draft is (&sect;3.7).

This makes source repair the first place the refuse-rather-than-guess rule applies, and the cheapest: a wrong repair at this stage would otherwise propagate into every item built on it.

#### Consequences

- **Page images beat any text extraction of them.** The supplied PDF has no text layer — each page is an image — and that turns out to be the useful property: stacked fractions, boxed definitions and table grids are all still visually intact. OCR would flatten them again, exactly as the original extraction did, so the quantitative units are authored from the page images directly (`tools/pdf_pages.py`, `tools/author.py --images`). Every numeric key is still recomputed by the arithmetic gate, so reading from an image changes the source, not the proof obligation.
- **A better source raises recall, not correctness.** What survives repair is already proved; a PDF with structure intact would simply yield more of it. Worth getting, no longer a blocker.
- **Coverage is now measurable per unit before authoring begins.** Units where repair yields little are the units to leave uncovered, and that is knowable in advance rather than discovered through collapsing verification yield.
- **Report repair rate alongside verification yield** (&sect;3.3). They are different failure modes: repair rate measures how much of the source is usable, yield measures how much of the usable source becomes items.

---

## 4. Grounding, and the no-assertion rule

The largest correctness risk in this product: a confident tutor inventing a KYC periodicity or a CRAR floor. An exam candidate cannot tell the difference, which is precisely why they're here.

### 4.1 The structural insight

A Socratic tutor is *safer* than a direct one, because questions don't assert facts. Lean on that deliberately:

> **No-assertion rule.** In states `PROBE`, `NARROW`, `HINT_L1`, `HINT_L2`, the model may not state a statutory or numerical fact. It may only ask, reflect the learner's own statement back, or point at the item's given data. Facts appear only in `WORKED_EXAMPLE` and `RESOLVE`, and only from retrieved, cited text.

This turns hallucination from a pervasive risk into one confined to two states — where we can constrain it hard.

### 4.2 Statute store

Versioned corpus, clause-addressable: RBI master circulars and directions, BR Act, RBI Act, PMLA + rules, SARFAESI, NI Act, AS/Ind-AS, IIBF courseware editions.

`RESOLVE` and `WORKED_EXAMPLE` are **extractive-first**: the response is assembled from the item's authored explanation plus the retrieved clause. The model's job is to phrase, not to know. Every factual sentence carries a clause reference the learner can tap to see the source text.

**If retrieval returns nothing above threshold, the tutor says so and ends the session at the item's authored explanation.** No improvisation. A hedge costs a moment of friction; a fabricated threshold costs someone their exam.

### 4.3 Authoring-time vs runtime models

Two different risk regimes, deliberately separated:

- **Authoring time** — large model, expensive, generous context, generating items and explanations. Every output passes the §3.7 gauntlet: independent second-model verification against retrieved source, with discard as the only failure mode. Hallucination here is caught, or the item does not exist.
- **Runtime** — **no model at all in P0** (§2.3). What a learner meets was authored and verified before it shipped, so there is no runtime hallucination surface left to constrain. This is the reason the two regimes stopped needing to be balanced against each other: one of them was removed.

When free text returns (§2.3) it comes back under the no-assertion rule, as a late rung only, and it must share neither prompts nor model configuration with the authoring path.

---

## 5. Evaluation harness

Nothing ships without this. It runs in CI and gates every prompt, model or retrieval change.

**E1 — Factual contradiction.** 500 golden statutory Q&A pairs, **machine-extracted from the statute store with the answering span recorded** — the clause is the ground truth by construction, so this set needs no human and regenerates whenever the corpus updates. Tutor transcripts scanned for contradiction of the golden answer. Gate: **<0.5%**. This is the safety gate; a regression blocks release outright.

**E2 — Premature reveal.** 150 adversarial transcripts where a scripted learner tries to extract the answer ("is it B?", "I'm out of time", "my teacher said B"). Gate: reveal before `HINT_L2` in **<3%**.

**E3 — Abandonment.** Scripted struggling learner. Gate: **100%** of sessions reach `RESOLVE` within the turn budget. No learner is ever left without the answer.

**E4 — Pedagogical quality.** *Not closable autonomously* (§3.7). The LLM-judge rubric still runs as a smoke test for gross regressions, but it is a model grading a model with no anchor and is **never a release gate**. The real arbiter is E6 plus misconception-resolution rate, measured by cohort over weeks.

**E5 — Citation integrity.** Every factual sentence in `RESOLVE` resolves to a real, live, non-superseded clause. Gate: **100%**. Broken or stale citations are a build failure.

**E6 — Live retention (not CI).** Weekly cohort: accuracy on items first seen ≥21 days ago. This is the north-star leading indicator (§11).

---

## 6. Mastery model

v1's "≥80%" is undefined without knowing the difficulty of what was answered — 80% on easy items and 80% on hard items are different states of the world.

**Per-node ability θ**, 2PL: `P(correct) = 1 / (1 + exp(-a(θ - b)))`.

- **Mastery** at node `n`: `θ_n ≥ b_exam(n)` with `SE(θ_n) < 0.35`, where `b_exam(n)` is the calibrated difficulty of that node's typical IIBF exam item.
- **Item selection**: serve items where predicted `P(correct) ∈ [0.70, 0.85]`. Not maximum-information selection — that targets 0.5 and feels brutal on a phone at 8am.

  **What that costs, measured** (`tools/simulate.py`, 400 synthetic learners): the band needs a median **48 items** to reach mastery against **33** for maximum-information selection — about 45% more — while the learner experiences **79% accuracy instead of 50%**. Both reach mastery for 100% of learners and end at comparable standard error, so the trade is items-per-concept bought with engagement, not accuracy of measurement.

  That 15-item gap is a **content-volume decision, not just a UX one**: it sets how many items each concept needs before the catalogue can carry a learner to mastery. Budget for it.
- **Below `θ - 1.0` on a node's prerequisites**: stop serving the node. Route to the prerequisite. v1's "revert to simple language" treats a knowledge-structure problem as a tone problem.
- **Misconception state is separate from θ.** A learner can have adequate θ and still reliably hold one specific wrong belief. Track per-misconception: `active` → `remediated` (2 consecutive correct on items with that distractor, ≥7 days apart) → `stale` (no encounter in 60 days, re-test).

---

## 7. Scheduling

Replace v1's fixed 0/1/4/10/30 ladder with **FSRS** (open-source, well-validated, materially better than SM-2), with two banking-specific modifications:

1. **Exam-date awareness — corrected by measurement.** The learner supplies their exam date, and the scheduler never lets an interval run past it.

   The original specification here said intervals should *compress* as the exam approached. `tools/simulate.py` measured that against an independent forgetting model and it **loses at every horizon a candidate cares about**:

   | Days to exam | Plain | Compressed | Hard clamp |
   |---|---|---|---|
   | 5 | **0.461** | 0.345 | 0.366 |
   | 10 | **0.449** | 0.354 | 0.362 |
   | 21 | **0.548** | 0.416 | 0.417 |
   | 47 | **0.725** | 0.597 | 0.562 |
   | 90 | 0.760 | **0.827** | 0.707 |

   *(mean recall on exam day; fixed review budget throughout)*

   Compression pulls every review earlier, so less has been forgotten when it happens, so each review consolidates less. Under a fixed session budget that trade is simply bad: **cramming harder near the exam costs recall on the day.** The intuition was wrong, and it was wrong in the direction that feels most obviously right.

   It pays only past ~8 weeks, where the mechanism is different — plain scheduling lets intervals grow so long that items fall due after the paper. So the rule is **never defer past the exam**, applied smoothly, not **compress near it**.

   Hard-clamping to the eve of the exam was worst of all (0.562 at 47 days): it piles every item onto one day, which exceeds what a session can hold, and the surplus is never reviewed at all. Session capacity, not interval length, is the binding constraint.
2. **Interleaving constraint.** Within a session, no two consecutive items from the same **concept** (§2.5) — not the same syllabus node, since one concept can span several nodes and interleaving those would not actually vary the retrieval. Interleaving is one of the better-evidenced effects in the literature and it is nearly free to implement.

**Session shape:** 5–10 minutes, 8–12 items, one of which is a field-calibration item. Fully resumable — the Socratic session state persists, so a session interrupted by a customer at the counter resumes intact.

---

## 8. Device reality

v1 assumed Gemini Nano via AICore. AICore is on a narrow slice of recent flagships; the target user — a clerk or officer in a tier-2 branch — is on a mid-range Android with 4GB RAM. Design for that, and treat on-device inference as an optimisation for the few, never a dependency.

| Tier | Device | Online | Offline |
|---|---|---|---|
| **A** | AICore-capable flagship | Authored ladder | Authored ladder — identical |
| **B** | Mid-range, ≥4GB | Authored ladder | Authored ladder — identical |
| **C** | Low-end / metered data | Authored ladder | Authored ladder — identical |

**The key move:** with the ladder authored at content time (§2.3), *every tier behaves identically, online or off, with no inference anywhere.* There is no degraded mode to design, no tier-dependent quality, and nothing a learner meets that was generated in the moment. The three columns above are the same column three times, which is exactly the point.

Content packs: per-subject, downloadable on Wi-Fi, ~20–40MB (items + hints + worked examples + the cited clause excerpts). Delta updates when the staleness watcher fires.

---

## 9. Technical architecture

Largely as v1 — it was sound. Deltas noted.

**Client:** Kotlin, Jetpack Compose, MVI/UDF, Hilt. Room for items, attempts, misconception state, Socratic session state. DataStore for preferences and scheduler metadata. WorkManager for content-pack sync and offline attempt upload.

**Server:** the parts v1 had no room for, and they're the substance —

- **Verification service** — the §3.7 gauntlet as a pipeline: draft, retrieve, verify, score derivation overlap, admit or discard. Every decision logged with its span and its reason, because rejects are the only diagnostic available for grounding coverage. *Build this first;* it is what the learner app is worthless without.
- **Content service** — item CRUD, lifecycle states, yield metrics per syllabus node, learner-report intake.
- **Statute store** — versioned corpus + clause-addressable retrieval.
- **Tutor service** — the §2.3 state machine. Model calls constrained by the no-assertion rule; all transcripts logged for E1–E5 replay.
- **Psychometrics** — nightly IRT recalibration, distractor-pull stats, prevalence updates.
- **Staleness watcher** — §3.5.

**Client/server boundary:** scheduling and item selection run **on-device** against cached psychometrics. It must work on a train with no signal, and it keeps the learner's response history local by default. Only the free-text tutor needs the network.

**Privacy.** v1 claimed "privacy-first" and derived it from on-device inference, which §8 just removed. The honest version: response history and mastery state stay on-device; free-text tutor turns go to the cloud and the learner is told so plainly at first use; no PII in prompts; transcripts retained 30 days for eval replay, then deleted. If we later sell to bank L&D (§11), employer-visible progress is opt-in and per-learner, and that promise needs to survive the first enterprise deal that asks us to break it.

---

## 10. What was cut, and why

- **Agentic OS / MCP AppFunctions.** Lock-screen voice queries are a demo, not retention. Zero evidence any learner wants this. v3 at the earliest.
- **Rive / Compose Canvas visualisations.** Yield-curve animations are expensive to author and orthogonal to the wedge. The four §2.4 rendering components cover real remediation need.
- **XP, streaks, SDT framing.** Streaks mostly optimise for streak-preservation. Revisit with data; if we add motivation mechanics, make them exam-date-anchored progress ("you are on track for 12 March"), which is honest and more motivating for adults.
- **On-device Gemini Nano, and the cloud tutor with it.** §2.3. With the ladder authored, P0 runs no model in a learner session at all — which removes the hallucination surface, the per-session cost and the offline degraded mode in one move.
- **Media3 video.** v1's worked-example videos cost more per minute than anything else in the content pipeline. Static contrast-cases first; add video only where the pilot shows static explanations failing.

Each of these is a real feature. None of them is the thing that makes this work.

---

## 11. Metrics and business model

**North star:** verified IIBF pass-rate delta vs matched non-users. Slow, noisy, and the only thing that matters.

**Leading indicators:**
- D30 retrieval accuracy on items first seen ≥21 days ago (§5 E6) — the closest weekly proxy for durable learning.
- Misconception resolution rate: `active → remediated` per learner-week.
- Session completion rate (proxy for the escalation policy being tuned right).

**Deliberately not tracked as goals:** DAU, time-in-app, streak length. A product that works well *reduces* time-in-app. Optimising engagement here is directly opposed to optimising learning.

**Revenue hypotheses, in order of confidence:**
1. **B2B2C — bank L&D.** Banks already pay IIBF fees and reimburse staff. Selling cohort licences to an L&D function is a shorter path to real revenue than consumer acquisition, and pass-rate reporting is exactly what an L&D head is measured on. Highest-conviction path; validate with 3 discovery conversations before writing more code.
2. **Consumer per-certification unlock.** One subject free (AML/KYC — the pilot), single-price unlock per certification. Not a subscription: the learner's relationship with a certification ends when they pass it, and subscriptions to finite goals churn brutally.
3. Institutional bulk / coaching-centre white-label. Later.

---

## 12. Sequencing, and kill criteria

**P0 — vertical slice (~12 weeks).** AML/KYC only. 50 misconceptions, ~400 calibrated items, statute store over PMLA + the relevant RBI master directions, cloud-only tutor, authored offline hints, FSRS with exam-date awareness, E1–E5 green, plus the §13.10 feed slice (RBI + SEBI RSS, blast-radius query, rate reference card, seeded parameter register). No Nano, no MCP, no gamification, no video.

*Exit criterion:* 200 real learners, 4 weeks, E6 retention measured against a plain right/wrong control arm on the identical item set.

**P1 — prove it generalises (~16 weeks).** JAIIB end to end. Verification gauntlet hardened and yield instrumented per syllabus node. Staleness watcher and automated re-verification in production. First B2B2C pilot with one bank's L&D.

**P2 — breadth.** CAIIB, specialised diplomas. Revisit Tier A on-device, motivation mechanics, video.

**Kill criteria — write these down now, while it's cheap to be honest:**
- P0 retention delta **< +5pp** vs control → the misconception wedge does not work as theorised. Stop, or pivot to a conventional bank with better UX.
- **Verification yield stays below ~10%** across a topic after corpus expansion → the grounding is too thin to author against autonomously, and that topic cannot be covered honestly. Narrow the scope rather than loosening the gate.
- **Auto-retire rate (negative discrimination) exceeds ~5% of calibrated items** → verification is passing items it should not, and the gauntlet needs work before more content is generated.
- E1 contradiction rate cannot be held **< 0.5%** → do not ship a statutory tutor. This one is non-negotiable.

---

## 13. Regulatory ingestion layer

The subsystem that feeds §3.5 and §4.2. Treated as core infrastructure, not a nice-to-have: without it the statute store silently rots and §4's citations start pointing at repealed text.

### 13.1 Sources — verified availability

Checked live on 2026-09-20. Status is what the endpoint actually returned to a plain client.

| Regulator | Channel | Endpoint | Status |
|---|---|---|---|
| RBI | Notifications RSS | `https://www.rbi.org.in/notifications_rss.xml` | ✅ 200, XML |
| RBI | Press releases RSS | `https://www.rbi.org.in/pressreleases_rss.xml` | ✅ 200, XML |
| RBI | Publications / Speeches / Tenders RSS | `Publication_rss.xml`, `speeches_rss.xml`, `tenders_rss.xml` | listed on `rbi.org.in/Scripts/rss.aspx` |
| RBI | Master Directions index | `rbi.org.in/scripts/bs_viewmasterdirections.aspx` | HTML, scrape |
| RBI | Master Circulars index | `rbi.org.in/scripts/BS_ViewMasterCirculars.aspx` | HTML, scrape |
| SEBI | Single aggregate RSS (press releases + circulars + orders) | `https://www.sebi.gov.in/sebirss.xml` | ✅ 200, XML, `ttl=60` |
| SEBI | Master Circulars | `sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=6&smid=0` | HTML, scrape |
| IRDAI | — | `irdai.gov.in` | ⚠️ **403 to non-browser clients.** No usable RSS found |
| PFRDA | — | `pfrda.org.in` | 200, HTML only |
| FBIL | Benchmark rates (MIBOR, T-Bill, OIS, reference rates) | `fbil.org.in` | 200, **redistribution licensing applies — §13.7** |
| IIBF | Syllabus / courseware editions | `iibf.org.in` | HTML, scrape |

**The practical picture:** RBI and SEBI are solved by RSS — that part is genuinely a day's work. IRDAI, PFRDA and IIBF need polite scraping: real browser UA, honour `robots.txt`, low rate, backoff. IRDAI's 403 is the main engineering annoyance and should be spiked in week 1 rather than discovered in week 9.

Do not build on third-party GitHub scrapers of these feeds. No SLA, and a silently dead scraper produces exactly the failure mode §3.5 exists to prevent — content that looks current and isn't.

### 13.2 Why this is urgent, with a live example

On **31 July 2026**, RBI consolidated **628 circulars and master circulars** from its Department of Supervision into **64 new Master Directions**, and a companion circular formally repealed all 628 predecessors. Substance unchanged; but every citation to those 628 documents now points at repealed text.

A single event, invalidating a substantial fraction of any banking-education corpus. A platform without this layer would still be serving those citations today and would not know. Build the watcher before the corpus, not after.

**Design consequence:** the pipeline must model *supersession*, not just *change*. A document can be repealed and replaced with identical substance — items stay pedagogically valid, but every citation must be rewritten. That is a bulk re-citation job and should be semi-automated (map old clause → new clause, SME confirms in batch), not a 628-document manual slog.

### 13.3 Normalised event schema

Every source, RSS or scraped, normalises to one shape:

```yaml
reg_event_id: rev_01J9...
regulator: RBI                        # RBI | SEBI | IRDAI | PFRDA | IIBF | IBA
doc_type: master_direction            # notification | circular | master_circular
                                      # | master_direction | press_release | syllabus
ref_no: "DoS.CO.PPG.SEC.../2026-27"
title: "..."
issued_on: 2026-07-31
effective_from: 2026-07-31
url: "https://..."
content_hash: sha256:...              # of extracted text, NOT the HTML
supersedes: [rev_..., rev_...]        # parsed from the repeal clause where present
applies_to: [commercial_banks, sfb, nbfc]
subjects: [AML-KYC, PSL]              # classifier output + confidence
impact: high                          # triage priority, §13.4
first_seen: 2026-07-31T09:14:00+05:30
```

Hash the extracted text, not the raw page. Regulator sites churn markup constantly, and hashing HTML produces a flood of false positives that trains the SME queue to be ignored — which is the same as having no queue.

### 13.4 Event → content pipeline

```
poll (RSS 15 min, scrape 6 h)
   ↓ dedupe on ref_no + content_hash
classify  → doc_type, subjects, applies_to, impact
   ↓
resolve supersession → which statute-store clauses are affected
   ↓
BLAST RADIUS: all items citing those clauses → `live` → `review`
   ↓                                          (pulled from serving immediately)
automated re-verification against the new source (§3.7)
   ↓
  ├─ re-cite   (key still entails under the new clause — recite, restore)
  ├─ redraft   (entailment broken — discard, regenerate from new source)
  └─ retire    (no successor clause — topic uncovered, and said so in the UI)
```

**Impact triage:** `high` if it touches AML/KYC, capital adequacy, PSL or provisioning — where a wrong answer is both exam-relevant and professionally damaging. SLA 5 working days (§3.5); everything else 15.

**Serving policy during review:** items are pulled, not served-with-a-warning. A slightly thinner item pool beats a confidently wrong statutory threshold.

### 13.5 Dynamic data catalogue

#### Three update regimes — read this before building any of it

"Dynamic" has been doing too much work in this section. These sources do not share an update pattern, and the pattern determines the infrastructure. Most of what follows needs no feed at all.

| Regime | Pattern | Examples | Infrastructure |
|---|---|---|---|
| **1. Streaming** | Continuous or scheduled, published immediately | Circulars, policy rates, small savings (quarterly), payment limits, scheme parameters, gold/FX | Pollers, watchers, staleness alarms — **the §13 machinery** |
| **2. Episodic** | Rare, unscheduled, high consequence | Regulatory parameter changes (§13.6), mergers, D-SIB list, PCA entries/exits, licence actions | **No new scrapers.** These arrive *as circulars* — regime 1 already catches them. What's needed is classification, not collection |
| **3. Periodic-static** | Annual or half-yearly publication, long lag | Bank performance (§14.2), branch network, workforce, BSR tables | **A calendar, a parser and a sanity check.** No watcher, no alarm |

**Regime 2 is the cheap insight.** A CRAR floor change or a bank merger does not need its own monitor — RBI announces it through the notification feed already being polled. The work is a classifier on the existing stream, not another integration. Anything proposing a dedicated scraper for regime 2 has misread where the data comes from.

**Regime 3 needs no pipeline.** *Trend & Progress* lands roughly once a year; the Financial Stability Report twice. That is a scheduled parse against an expected schema, guarded by range and year-on-year anomaly checks: a cell that moves implausibly, or fails its bound, is **held and rendered as not-yet-ingested** rather than published. Conservative failure, no person in the loop — eight or so publications a year, not a data platform. This materially reduces what §14.2 costs to build, and it means the §13.9 failure-mode alarms apply to regime 1 only. Alarming on a source that updates annually is noise.

**The honesty cost of regime 3.** An annual publication with a 9–12 month lag, stale for the following twelve months, means the dashboard can be showing figures close to two years old at the end of a cycle. That is acceptable for teaching structure and distribution; it is not acceptable if the interface implies currency. The as-of date requirement in §14.2 is not a nicety — for regime 3 it is the difference between a reference and a misrepresentation.

#### Tiering by value

Within regime 1, order by **(exam load-bearing × volatility × feed availability)**, which produces a different ranking from intuition — small savings rates matter more here than the gold price.

#### Tier 1 — exam load-bearing, must be fed

These appear directly in questions, change often enough that courseware is routinely stale on them, and are cheap to source.

| Series / set | Source | Cadence | Why it matters |
|---|---|---|---|
| **Small savings rates** (PPF, SCSS, NSC, KVP, SSY, POMIS, POTD) | MoF / DEA quarterly notification | **Quarterly** | The highest-churn examinable numbers in retail banking. A textbook is stale within a quarter of printing. |
| Policy rates (repo, SDF, MSF, Bank Rate) | RBI MPC statements + press-release feed | Per MPC | Baseline. |
| CRR, SLR | RBI notifications | Irregular | Also parameters (§13.6). |
| **Government scheme parameters** (PMMY/Mudra limits, CGTMSE cover, KCC limits & interest subvention, PMEGP, Stand-Up India, PM Vishwakarma) | Respective ministry + RBI PSL Master Direction | Irregular, revised often | Heavily examined in PSL/MSME modules; the fastest-rotting content in any banking textbook. |
| **Payment system limits** (UPI per-txn and per-category caps, NEFT/RTGS/IMPS limits and timings, positive-pay threshold) | NPCI circulars + RBI | Several times a year | Core to operational certificates and to daily branch work. |
| Customer-protection limits (Integrated Ombudsman compensation ceilings; unauthorised-transaction liability timelines) | RBI | Rare but high-impact | Frequently examined; getting these wrong is professionally damaging. |
| DICGC deposit insurance cover | DICGC / RBI | Rare | Perennial exam favourite. |

#### Tier 2 — practice-relevant, exam-marginal

**This is where gold and the rupee actually sit, and the distinction is worth being precise about.**

Exams test the *mechanism*, not the level. A question asks how gold-loan LTV is applied or what a reference rate is for — not what gold closed at yesterday. So these series should **not** parametrise items (§13.8); an item reading "with gold at ₹X" would change its own answer weekly and destroy its psychometric calibration (§3.4).

They are genuinely valuable on the **reference card** — the thing a practising officer opens at their desk — and that is the §14 compliance-surface wedge, not the exam product.

| Series | Source | Cadence | Note |
|---|---|---|---|
| Gold price (and silver) | IBJA / RBI gold-loan context | Daily | **Gold-loan LTV is a parameter (§13.6), not a series.** The cap is examinable; the price is not. |
| USD/INR, EUR, GBP, JPY reference rates | RBI reference rate, published daily | Daily | Relevant to trade-finance and forex-operations certificates. |
| Forward premia, FX swap rates | RBI / FBIL | Daily | **FBIL licensing, §13.7.** |
| G-Sec yields, T-Bill cut-offs | RBI auction press releases | Weekly | Treasury/CAIIB context. |
| MCLR (system median), EBLR | RBI / bank disclosures | Monthly | Useful for lending-rate mechanics. |
| MIBOR, OIS | FBIL | Daily | **Licensed, §13.7.** |

#### Tier 3 — macro context

Rarely the answer to a question; frequently the setting for a CAIIB scenario, and useful for the quantity-intuition strategy (§2.4).

CPI / WPI inflation (MoSPI, monthly) · GDP growth · IIP · fiscal deficit · money supply M0/M1/M3 and reserve money · **forex reserves** (RBI Weekly Statistical Supplement) · current account balance · **aggregate credit and deposit growth, C-D ratio** (RBI WSS, weekly) · system GNPA/NNPA (RBI Financial Stability Report, half-yearly — also the source for the bank-group performance surface, §14.2).

#### Tier 4 — structural facts, not numbers

An underrated category, because these are *assertions in prose* that quietly become false, and no rate-watcher would ever catch them.

- **D-SIB list** — RBI publishes annually; a textbook naming the wrong set is simply wrong.
- **Banks under PCA** — changes; commonly examined as a framework, occasionally as a fact.
- **Scheduled commercial bank list, mergers and amalgamations, licence grants and cancellations, NBFC deregistrations.** Statements like "there are N public sector banks" have been invalidated repeatedly by amalgamation.
- **Regulatory entity-category changes** — new licence types, revised NBFC layering.

Treat these as regulatory events (§13.3) with `doc_type: structural`, and blast-radius them against items whose text asserts the fact. This is the one category where a full-text search over item prose, not just citations, is warranted.

#### Special case — the IIBF exam calendar

Not market data, but the most product-critical dynamic source in this list: exam dates, registration windows and **syllabus cutoff dates**. The entire exam-cutoff resolution in §13.6 and §13.8 depends on knowing each certification's cutoff. Scrape `iibf.org.in`; treat a parse failure as a P1 incident, because silently defaulting to `now` would reintroduce exactly the error §13.8 exists to prevent.

#### Access reality

RBI's DBIE — now `data.rbi.org.in`, formerly `dbie.rbi.org.in` — is the authoritative warehouse and exports CSV/Excel/PDF, but it is a JavaScript portal with **no documented public API or SDMX endpoint**. Plan for scheduled export-scraping plus parsing of MPC press releases for same-day policy changes. Treat "DBIE has an API" as unverified until confirmed. Small savings rates come from DEA notifications; payment limits from NPCI circulars; neither has a feed, so both need scrapers.

**Storage:** append-only `(series_id, as_of_date, value, source_url, ingested_at)`. Never update in place — revisions are new rows. Questions about "the rate in FY2024-25" need history, and an overwritten series cannot answer them.

#### Restraint

Every series is a scraper, a watcher and a standing failure surface (§13.9). Forty series is a data engineering team nobody has budgeted. **P0 should carry six or seven**: small savings, policy rates, CRR/SLR, scheme parameters, payment limits, the exam calendar — plus gold and USD/INR only if the desk reference card ships in the pilot. Everything else earns its place by being asked for.

### 13.6 Regulatory parameter register

§13.5 covers rates. Rates are not the same thing as **regulatory parameters**, and conflating them — as an earlier draft of this document did by listing CRAR alongside CRR — produces a system that tracks the easy half and hallucinates the hard half.

**Three distinct classes:**

| Class | Example | Who sets it | Changes | Feed treatment |
|---|---|---|---|---|
| **Rate** | Repo, CRR, SLR, Bank Rate | RBI, directly | Scheduled, frequent | Time series, §13.5 |
| **Parameter** | CRAR floor 9%, CCB 2.5%, LCR 100%, NPA at 90 days, PSL 40% of ANBC | RBI, as a *minimum or threshold a bank must meet* | Rare, phased, entity-scoped | **Parameter register — this section** |
| **Computation** | Compute a bank's CRAR from its RWA and capital | Nobody — it's a skill | Never | Item logic; cites the parameter |

CRR and SLR happen to sit in both: RBI sets the number *and* it's a maintenance obligation. That coincidence is what made the earlier draft's categorisation feel fine. CRAR breaks it — RBI does not publish "the CRAR," it publishes a floor that each bank must exceed, and the floor is what an exam tests.

**Why parameters are the higher risk of the two.** Rates change often, so staleness is obvious and self-correcting. Parameters change once every few years, which means a wrong value sits in the corpus undetected for a long time, and they are precisely the values an exam question turns on. §4's worked example — "a confident tutor inventing a CRAR floor" — is a parameter failure, not a rate failure.

#### Schema

```yaml
param_id: CRAR.MIN.TOTAL
label: "Minimum total capital to risk-weighted assets ratio"
value: 9.0
unit: percent
applies_to: [scheduled_commercial_bank]     # ENTITY-SCOPED — see below
effective_from: 2013-04-01
effective_to: null                          # null = current
source: { doc: "RBI Master Direction — Basel III Capital Regulations", clause: "4.2.1" }
supersedes: null
scheduled_successor: null                   # future-dated phase-ins live here
verification:                               # §3.7 — no human signature exists
  extracted_span: "...minimum of 9 per cent..."
  second_model_agrees: true
  corroborating_sources: 2                  # distinct documents stating the same value
last_verified: 2026-09-21
```

**Entity scoping is not optional.** The single most common way a banking tutor is confidently wrong is answering a question about one entity type with another's parameter:

- CRAR floor: **9%** for scheduled commercial banks, **15%** for small finance banks, **15%** for NBFC-ND-SI, different again for UCBs and RRBs.
- Priority sector targets differ for domestic banks, foreign banks with <20 branches, SFBs, RRBs.
- KYC periodicity differs by customer risk category.

A learner sitting the SFB paper who is told "9%" has been actively taught the wrong thing. Every parameter lookup must therefore carry an entity, and the tutor may not answer a parameter question until the entity is resolved — from the item's context, or by asking. **A parameter with no entity scope is a schema violation, rejected in CI**, the same way an orphan distractor is (§3.1).

#### Phase-ins and future-dated values

Basel-style parameters arrive with a schedule — a value effective now and a different value effective later. The register stores both, and `effective_from` resolves against **the learner's exam cutoff**, exactly as §13.8's rate parametrisation does. This matters more here than for rates: a learner preparing for a March paper must be taught the value in force in March, not the one that took effect in June.

#### Seed coverage for P0/P1

Indicative scope, ~80–120 parameters for JAIIB + CAIIB + the compliance certificates:

| Domain | Parameters |
|---|---|
| Capital adequacy | CRAR total / Tier 1 / CET1 floors, capital conservation buffer, countercyclical buffer, leverage ratio, D-SIB surcharge — each per entity type |
| Liquidity | LCR, NSFR, run-off factors, HQLA haircuts |
| Asset classification | NPA 90-day rule, SMA-0/1/2 boundaries, sub-standard / doubtful / loss ageing, provisioning percentages per category (secured vs unsecured) |
| Priority sector | Overall ANBC target, agriculture, small & marginal farmers, micro enterprises, weaker sections — per entity type |
| MSME | Investment and turnover thresholds per micro / small / medium |
| AML/KYC | CTR threshold, cross-border wire threshold, STR timelines, periodic KYC update intervals by risk category, record retention periods |
| Deposits | DICGC cover, unclaimed-deposit transfer timelines |
| Exposure | Large exposure limits, single / group borrower ceilings |

**These values are deliberately not listed here.** A blueprint is the wrong container for them — the register is, where each carries a clause citation, an effective date, an entity scope, the extracted span it was read from, and second-model agreement. Any figure written into prose is a figure nobody will re-verify. That is also the honest answer to "is CRAR covered?": it is covered by *building the register*, not by my asserting 9% in a design document — and note that the July 2026 consolidation (§13.2) rewrote the citation path for a large share of exactly these parameters.

#### Autonomous verification of parameters

Parameters are the highest-consequence values in the system and the ones a human would most obviously have signed off. Three automated rules carry that weight instead:

1. **Span-anchored extraction.** A parameter exists only if its value is literally present in the cited clause. No inference, no arithmetic, no "commonly understood to be".
2. **Corroboration.** Where two or more live documents state the same parameter, they must agree. Disagreement holds the parameter and suppresses every item depending on it — a contradiction in the corpus is exactly the case where guessing is worst.
3. **Change requires a cause.** A parameter's value may only change when a §13.3 event supersedes its source. A value that appears to change with no amending document behind it is a parse error, not a regulatory change, and is rejected. This single rule blocks the most damaging silent-corruption path in an unattended system.

#### Feed linkage

Parameters attach to the §13.4 blast radius like any other citation, with one addition: a regulatory event classified as `capital_adequacy`, `asset_classification` or `priority_sector` **also** flags every parameter sourced from the affected document, not just the items. Parameters are reviewed first, then items — because an item citing a stale parameter is wrong even if the item text is untouched.

Parameter changes are always `impact: high`. There is no low-priority capital-adequacy amendment.

#### Product surface

The §13.8 reference card extends to a **parameter lookup** — entity-scoped, effective-dated, citation-linked. "CRAR minimum, small finance bank, as at my exam cutoff → 15%, per [clause], in force since [date]."

This is the single most useful non-learning feature in the product, and the cheapest to build once the register exists. It is also the feature a practising officer opens at their desk, which is the wedge into §14's compliance surface.

### 13.7 Licensing — the part that bites

**FBIL benchmark rates are licensed.** Displaying them in a commercial product is not obviously covered by fair use; FBIL operates a commercial licensing regime for redistribution. Same class of problem for NSE/BSE market data. **Do not ship FBIL-sourced rates to end users before someone reads the licence.** RBI's own published rates (repo, CRR, SLR, reference rate) are government-published and far safer ground.

This sits alongside the IIBF courseware question in §15: a legal item with the power to invalidate engineering already done. Both belong before the pilot, not during.

### 13.8 What learners actually see

A raw regulatory firehose is a feature for a compliance officer and a distraction for a JAIIB candidate three weeks from an exam. Differentiate by tier:

- **JAIIB / DB&F:** nothing by default. A changed circular surfaces only as a quietly corrected item. Noise here directly degrades the §7 scheduler.
- **CAIIB / diplomas:** opt-in weekly digest, filtered to enrolled subjects — *"3 updates affecting Risk Management this week"* — each linked to a practice item. This is the tier where regulatory currency is part of the competence being certified.
- **AML/KYC & compliance certificates:** digest on by default. Currency *is* the skill.
- **Rates:** one always-current reference card (repo / CRR / SLR / Bank Rate, with last-change date) plus a sparkline. Cheap, genuinely useful, and it anchors the quantity-intuition strategy in §2.4.

**Live-parametrised items.** Items whose stem depends on a current rate hold a series reference instead of a hardcoded number:

```yaml
stem: "With the repo rate at {{series:REPOexam_cutoff}}, compute ..."
```

Resolved at render time. One authored item then stays correct across every rate change instead of going stale at the next MPC — which also removes a whole category of §3.5 churn.

**The exam-cutoff subtlety, and it matters:** IIBF exams are set against a syllabus cutoff date, so *today's* repo rate may be the wrong answer for a paper sat next month. Parametrised items therefore resolve against **the learner's exam cutoff, not `now`**, and the reference card shows both:

> Repo rate — **5.50%** current (as at 6 Aug 2026) · **5.50%** as at your exam cutoff (31 Mar 2026)

Getting this backwards teaches the learner the right fact and fails them on the paper. It is the kind of detail that only surfaces if the feed is taken seriously rather than bolted onto the home screen as a ticker.

### 13.9 Failure modes to instrument

**Regime 1 only** (§13.5). A feed that dies quietly is worse than no feed, because §3.5 assumes it works. Regime 3 sources update annually and need a calendar reminder, not an alarm.

- **Staleness alarm** per source: no new event in `N × median_interval` → page someone. RBI notifications going quiet for a week is normal; a month is a broken scraper.
- **Markup drift:** extraction yields <50% of expected fields → alarm, never silently write nulls.
- **Hash storms:** >20 events from one source in an hour is almost certainly a template change, not a regulatory earthquake. Quarantine; do not blast-radius the corpus.
- **Supersession gaps:** a document repealed with no successor mapped → its items are retired and the topic is marked uncovered. Never silently re-pointed at a guessed successor.

### 13.10 Build order

Feeds are cheap to start and expensive to retrofit. P0 slice, ~2 engineer-weeks, worth doing *during* pilot content authoring rather than after:

1. RBI + SEBI RSS → normalised event store. Both verified working.
2. `content_hash`, dedupe, supersession parsing.
3. Blast-radius query: clause → affected items → `review`.
4. Automated re-verification on blast radius (§3.7), with discard-and-redraft as the default outcome.
5. RBI policy-rate series + the learner-facing reference card.
6. **Parameter register** (§13.6), seeded for the AML/KYC and capital-adequacy domains. Entity scoping enforced in CI from day one — retrofitting it later means re-verifying every parameter.

Deferred to P1: IRDAI / PFRDA scraping, DBIE historical backfill, FBIL (pending §13.7), the learner digest.

---

## 14. Adjacent product surfaces

Two things the data layers unlock that are not the tutor. Both change the business case in §11; neither is P0.

### 14.1 Regulatory currency

The feed layer is built for defence — keeping §4's citations honest. But it is also the only part of this system a **bank's compliance function** would pay for on its own. An L&D head buys pass rates; a compliance head buys "every officer in this branch has been tested on the KYC amendment that landed last month, and here is the evidence."

That is a second product sharing one pipeline: same events, same blast-radius query, different surface — assign-and-attest rather than learn-and-retain. It is the highest-value thing the ingestion layer unlocks and it should inform the B2B2C conversations in §11, but it is explicitly **not** P0. Build the feed for correctness first; if the compliance pull is real, the discovery calls will surface it without us building anything speculative.

### 14.2 Bank performance, by bank group

A comparative view of banking-system performance, grouped by bank type — public sector, private, foreign, small finance, payments, RRB, cooperative.

#### Why this belongs here rather than being scope creep

Three reasons, in descending strength:

1. **Peer-group comparison is the analytical method, not a filter.** CAIIB's Bank Financial Management and the Risk/Treasury diplomas teach bank analysis, and no one assesses a bank in isolation — you assess it against its group. Comparing an SFB's CRAR to SBI's is not a harder version of the same question, it is a *wrong* question, because they face different floors (§13.6). The grouping is the pedagogy.
2. **It makes §2.4's quantity-intuition strategy real.** Order-of-magnitude anchoring on invented numbers is a poor substitute for seeing the actual distribution of GNPA across public sector banks. Ratio misconceptions are the ones abstract practice fails hardest on.
3. **It is the only organic acquisition surface in this spec.** §11 has a business model and no distribution. A public, free, accurate bank-performance view is the kind of thing bankers bookmark and share, and it costs nothing per visitor. For a content product with no existing channel, that is worth more than it looks.

#### The design decision that makes it ours

A dashboard on its own is a commodity — anyone can render RBI's tables. The thing nobody else can build is the **bidirectional link between the data surface and the item engine**:

- **Learning → data.** Miss a CRAR item, and the `WORKED_EXAMPLE` shows where real banks in the learner's own group actually sit. The abstraction acquires a reference distribution.
- **Data → learning.** Tap any metric on the dashboard and get the item that teaches how it is computed, plus its statutory floor from the parameter register.

Without that link this is a side project competing with free RBI PDFs. With it, the dashboard is a funnel into the tutor and the tutor is what makes the dashboard mean something.

**Personalisation, cheaply:** the learner's own employer is the highest-value comparator available, and you already need their bank type for §13.6 entity scoping. "Your bank vs the PSB median" makes every metric personal, and it is the single most compelling thing to put in front of a bank L&D head.

#### Metric families

Aligned to the BFM/Risk syllabus, so every metric is already something the certification expects a candidate to interpret:

| Family | Metrics |
|---|---|
| Capital | CRAR, CET1, Tier 1, leverage ratio — **shown against the group's regulatory floor from §13.6** |
| Asset quality | GNPA %, NNPA %, provision coverage ratio, slippage ratio, restructured book, SMA distribution |
| Profitability | NIM, ROA, ROE, cost-to-income, spread |
| Liquidity & mix | CD ratio, CASA ratio, LCR, NSFR |
| Productivity | Business per employee, profit per employee, branches, ATMs |
| Growth | Credit growth, deposit growth |
| Priority sector | PSL achievement against target, by sub-target |

Rendering CRAR against the entity-specific floor is the parameter register earning its keep: *"16.2% against a 15% floor for small finance banks"* is a sentence that teaches, where a bare 16.2% does not.

#### Display specification

Groups, as RBI itself classifies them: **Public sector · Private sector · Foreign · Small finance · Payments · Regional rural · Urban cooperative**, with *All scheduled commercial banks* as the reference row.

P1 fields. "Available" means RBI publishes it group-wise in *Trend & Progress* or the *FSR* — **each cell should be confirmed against the current edition before a scraper is written**, because table composition changes between editions and my read of what is published is not a substitute for opening them.

| Metric | Unit | Notes |
|---|---|---|
| **Structure** | | |
| Number of banks | count | Changes with mergers — a §13.5 Tier 4 structural fact |
| Branches, banking outlets, ATMs | count | Expanded below — population-group split is the load-bearing part |
| Employees, by cadre | count | Expanded below |
| **Balance sheet** | | |
| Deposits, advances, investments, total assets | ₹ crore | |
| Deposit growth, credit growth | % YoY | |
| Credit–deposit ratio | % | Not meaningful for payments banks |
| CASA ratio | % | Verify group-wise availability |
| **Capital** | | |
| CRAR | % | **Rendered against the group's floor from §13.6** |
| CET1, Tier 1 | % | FSR, for scheduled commercial banks |
| Leverage ratio | % | FSR |
| **Asset quality** | | |
| GNPA ratio, NNPA ratio | % | The headline pair |
| Provision coverage ratio | % | |
| Slippage ratio, write-offs | % | |
| SMA / restructured book | % | FSR, coverage varies by edition |
| **Profitability** | | |
| Return on assets, return on equity | % | |
| Net interest margin | % | |
| Cost-to-income ratio | % | |
| Net profit, provisions, operating profit | ₹ crore | |
| **Liquidity** | | |
| LCR, NSFR | % | FSR; thin for the smaller groups |
| **Priority sector** | | |
| PSL achievement vs target, by sub-target | % | Group-wise in *Trend & Progress*; ties to §13.6 targets |

Roughly 25 fields × 8 groups. Each renders as a current value, its as-of date, the group distribution, and a multi-year series.

**The matrix is sparse, and that is a display requirement, not an inconvenience.** Payments banks cannot lend, so GNPA, CD ratio and PCR are not "missing" for them — they are *undefined*. Conflating that with absent data teaches a learner something false about what a payments bank is.

Three distinct empty states, rendered differently:

- **Not applicable** — the metric has no meaning for this group. Say so, and let it teach: *"Payments banks do not extend credit, so asset-quality metrics do not apply."* This is one of the better free lessons in the product.
- **Not published** — RBI does not report it group-wise for this group in this edition. Name the limitation.
- **Not yet ingested** — our gap, not theirs. Never dressed up as either of the above.

**Deliberately excluded:** market capitalisation, share price, P/B, P/E, analyst estimates, any forward-looking figure, and any derived composite score of our own construction. The first four make this investment content (§14.2 constraints); the last makes us the author of a judgement rather than a reporter of published data.

#### Network and workforce

The two structure rows above collapse a lot. Both deserve expanding, because both are examined directly and both carry a regulatory parameter the raw count does not show.

**Branch network.** The count matters far less than the **population-group split**, which is RBI's own classification and the basis of branch authorisation policy and financial inclusion assessment:

| Field | Breakdown |
|---|---|
| Branches by population group | Rural · Semi-urban · Urban · Metropolitan |
| **Banking outlets** | Branches + BC outlets meeting RBI's banking-outlet criteria |
| Business correspondent outlets | Fixed-point BC locations |
| ATMs | On-site · off-site; cash recyclers |
| Specialised branches | SME, agriculture, AD/forex, treasury, corporate |
| Overseas presence | Indian banks abroad; foreign-bank branches in India |
| Currency chests | |
| Openings and closures | Net additions; rationalisation after amalgamation |
| Regional distribution | State / region-wise |

**Render each population-group share against its regulatory requirement**, the same motif as CRAR against its floor: *"X% of new banking outlets in unbanked rural centres, against a 25% requirement"* teaches, where a branch count does not. The parameter comes from §13.6; the achievement comes from the data. That pairing is the consistent design idea across this whole surface.

**Branch vs banking outlet is itself a misconception worth cataloguing (§2.2).** RBI's 2017 redefinition means a qualifying BC outlet counts as a banking outlet, so "branches" and "banking outlets" are different numbers that learners routinely conflate — an excellent distractor, and one the dashboard makes concrete rather than abstract.

**Do not rebuild the branch locator.** RBI's DBIE already carries a Banking Outlet Locator. Aggregate statistics are the product here; a branch-finder is someone else's.

**Workforce.** The cadre breakdown is the part that matters, because **the learners are the workforce being counted**:

| Field | Breakdown |
|---|---|
| Total employees | By bank group |
| By cadre | Officers · clerical · subordinate |
| Productivity | Business per employee, profit per employee |
| Composition | Gender; where published |
| Trend | Multi-year, by group |

An officer looking at officer-to-clerical ratios across bank groups, or at the divergence between public and private sector headcount over a decade, is looking at their own career structure. That is the most personally engaging data in the product and it costs nothing extra to render — it comes from the same tables.

**Sourcing.** Branch and employee statistics come from RBI's Basic Statistical Returns (BSR-1 for credit, BSR-2 for deposits and employees) and the Master Office File on bank offices, rather than from *Trend & Progress*. **Cadre-wise and gender splits need confirming against the current BSR edition before scoping** — group-wise availability is less consistent than the headline counts, and this is exactly the kind of field that is present in one year's tables and absent the next.

#### Sources, and the staging that follows from them

| Source | Granularity | Cadence | Lag |
|---|---|---|---|
| RBI *Report on Trend and Progress of Banking in India* | **Bank group** | Annual | ~6–9 months |
| RBI *Financial Stability Report* | **Bank group** | Half-yearly | ~2–3 months |
| RBI *Statistical Tables Relating to Banks in India* | Bank-wise | Annual | ~9–12 months |
| RBI *Basic Statistical Returns* (BSR-1/2) + Master Office File | Branch & employee detail | Annual | ~9–12 months |
| Basel III Pillar 3 disclosures | Bank-wise | Quarterly | ~6 weeks |
| Exchange filings / investor presentations | Bank-wise | Quarterly | Days — **licensing, §13.7** |

**RBI's own group-wise publications are already grouped in exactly the taxonomy requested**, which makes the group-level view dramatically cheaper than the bank-level one: one authoritative source, no reconciliation, no per-bank scrapers, minimal attribution risk.

So:

- **P1 — group level.** RBI Trend & Progress + FSR. ~20 metrics × 7 groups. This is regime 3 (§13.5): a scheduled annual parse with schema and anomaly guards, not a pipeline. This is most of the pedagogical value for a fraction of the cost, and it is the version that ships.
- **P2 — bank level.** STRBI annually, Pillar 3 quarterly for the timely capital and liquidity metrics. 40+ bank websites is 40+ scrapers and a reconciliation problem; earn it with demonstrated demand.
- **Never.** Real-time market data, valuations, price targets, or anything resembling a recommendation.

#### Constraints that are not optional

The learners are employees of the banks being displayed. That inverts the usual risk calculus: a wrong number about someone's own employer damages trust far more than a wrong exam answer, and it will be noticed immediately.

- **Official published sources only.** No estimates, no interpolation, no filling a gap with a plausible figure. A missing cell renders as missing.
- **Every figure carries its as-of date and source**, prominently. RBI annual data is 6–12 months lagged; a learner who thinks it is current has been misled by the interface rather than the data.
- **No editorial ranking.** Report the numbers and the group distribution. No "best performing", no "worst", no league tables, no colour-coding that implies a verdict. Rank order is something the learner derives; publishing it as a judgement is a different product with a different liability.
- **Not investment content.** This is professional education and a reference for practitioners. No buy/sell framing, no valuation metrics, no forward-looking commentary, and an explicit disclaimer that it is neither investment advice nor a solicitation. The line is easy to hold if the metric families stay as listed above, and easy to cross by adding one P/B ratio.
- **Corrections process.** A visible route to report an error, an SLA to fix it, and a changelog. Assume a bank's investor-relations team will eventually be in touch, and make that a two-email exchange rather than an incident.
- **Exchange-sourced data is licensed** (§13.7), the same problem as FBIL. RBI publications are not. Another reason the group-level P1 is the right first cut.

---

## 15. Open questions

1. **Courseware rights.** The Macmillan IIBF volumes are the authoring source (§3.6). Deriving facts and procedures from them and writing original items is the defensible position; the risk sits in how closely derived explanations and worked examples track the originals, which is an SME-review discipline (§3.6) rather than a yes/no legal gate. The live question is commercial: is a licensing or partnership arrangement with IIBF/Macmillan available, and would it convert this from a risk into distribution? Worth one conversation before the pilot.
2. **FBIL / market-data licensing.** Can we display FBIL benchmark rates in a paid product, and on what terms? §13.7. RBI-published rates are the safe subset; decide before building anything on top of FBIL.
3. **Bank-level performance data.** Is quarterly bank-wise detail (§14.2 P2) actually wanted, or is the group view sufficient for the syllabus? The answer decides whether 40+ Pillar 3 scrapers and a reconciliation layer are ever justified. Ask three CAIIB candidates before building any of it.
4. **IRDAI access.** Their site 403s non-browser clients. Is there a sanctioned feed, or do we need a headless-browser scraper and an acceptable-use read? Affects whether insurance-side certificates are in scope at all.
5. **Verification yield.** Unknown until the first batch runs, and it sets both cost and coverage (§3.3). Measure it per syllabus node before committing to any breadth target.
6. **Language.** English-only for v1? IIBF exams are offered in Hindi. Misconception distractors do not translate mechanically — they'd need re-authoring per language, which roughly doubles §3.3.
7. **The v1 LearnLM figure.** The "5.5pp more likely to solve novel problems" and "44.3% of tutor interventions" claims need sources before either appears in anything external. Motivating, not load-bearing — nothing in this spec depends on them.
8. **Exam-date honesty.** If a learner's exam is in 5 days, the right advice may be "do mock papers, not this." Are we willing to say that? It builds trust and costs engagement.
