# High-impact primary-source claim ledger

Date: 2026-07-27
Status: verified primary-source reading; bounded design input only

## Purpose and boundary

This ledger repairs five high-impact claims selected from the user-supplied
human-AI software-lifecycle research package. It reads the primary research or
official survey surfaces directly, binds every quantitative statement to its
observed setting, and records both allowed uses and forbidden inferences.

This is claim and citation verification, not independent reproduction of any
study. It does not accept the source report wholesale, promote a hard standard,
prove a live Harness result, rank Matt against Superpowers or another
candidate, or justify a self-authored capability.

## Repaired claims

### DORA 2025: organizational amplification and delivery tension

DORA describes AI as an amplifier of an organization's existing system rather
than a standalone fix. Its official release summary draws on nearly 5,000
technology professionals, reports 90% self-reported use at work, and reports
relationships with both delivery throughput or product performance and
delivery instability.

The allowed use is a paired measurement design: local speed or perceived
productivity must be reconciled with downstream throughput, stability, product,
rollback, and organizational outcomes. The finding is not causal proof, a
universal effect, or validation of the current Harness.

Primary surfaces:

- <https://dora.dev/research/2025/dora-report/>
- <https://cloud.google.com/blog/products/ai-machine-learning/announcing-the-2025-dora-report>
- <https://dora.dev/research/2025/errata/>

### Stack Overflow 2025: trust and reported rework

For the accuracy question, 46% of 33,244 respondents distrusted AI-tool
accuracy, 33% trusted it, and 3% highly trusted it. For a separate multi-select
frustration question, 66% of 31,476 respondents selected nearly-correct
solutions and 45% selected extra debugging time.

These are cross-sectional attitudes and reported experiences from a
self-selected survey recruited mainly through Stack Overflow-owned channels.
They are not model error rates, controlled productivity measurements, or a
probability sample of every developer.

Primary surfaces:

- <https://survey.stackoverflow.co/2025/ai>
- <https://survey.stackoverflow.co/2025/methodology/>

### METR 2025: measured time versus perceived acceleration

Sixteen experienced open-source developers completed 246 real issues in mature
repositories they knew well. In this early-2025 randomized setting, the
adjusted estimate was 19% longer when AI was allowed, while developers expected
a 24% speedup beforehand and still estimated a 20% speedup afterward.

The allowed use is forecast calibration and realistic task-cost measurement:
cycle time, prompting, waiting, review, post-review rework, and quality belong
together. The result cannot be generalized to most developers, current models,
novices, prototypes, unfamiliar repositories, or a full software lifecycle.

Primary surfaces:

- <https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/>
- <https://arxiv.org/abs/2507.09089>

### Laban et al. 2025: simulated multi-turn unreliability

The study compares complete single-turn instructions with information-equivalent
requirements revealed through controlled shards. Across 15 models, six
generation tasks, and more than 200,000 simulated conversations, aggregate
performance was about 90 in the full setting and 65 in the sharded setting;
average unreliability increased by about 112%. Early assumptions, premature
answers, and reliance on earlier wrong answers were observed failure modes.

The result supports a falsifiable Harness design with a frozen source, an
information-equivalent multi-turn arm, repeated trajectories, hop-level deltas,
and a source-backed recovery arm. It does not prove host compression behavior,
a token threshold, automatic new-thread creation, repository-anchored handoff,
or lossless recovery.

Primary surfaces:

- <https://arxiv.org/abs/2505.06120>
- <https://arxiv.org/html/2505.06120>
- <https://www.microsoft.com/en-us/research/publication/llms-get-lost-in-multi-turn-conversation/>

### Shen and Tamkin 2026: immediate skill formation

In a preregistered randomized experiment, 52 Python programmers who were new to
Trio completed two short tasks. The AI-assisted group scored 4.15 points lower
on a 27-point immediate quiz, which the authors describe as a 17% score
difference; average task-time acceleration was not statistically significant.

This supports separating output correctness and time from the human
supervisor's independent conceptual, code-reading, debugging, and review
competence. It does not prove long-term skill decay, an agentic-tool effect, a
best interaction style, or a universal 17% acceptance threshold.

Primary surfaces:

- <https://arxiv.org/abs/2601.20245>
- <https://arxiv.org/html/2601.20245>
- <https://osf.io/w49e7>

## Matrix effect

The ledger enriches scenario design only. In particular:

- research and requirements scenarios gain repeated-trajectory and
  assumption-delta checks;
- learning gains separate immediate, delayed, transfer, and supervision
  competence;
- implementation and review gain realistic cycle-time, review, rework,
  process-fidelity, and human-supervision measures;
- release and operations pair throughput with stability and recovery;
- management reconciles self-report, forecast, measured outcome, team or
  lifecycle effects, and long-term competence.

No scenario evidence state is promoted by this literature review. The primary
sources are dated and future source drift must be rechecked before quantitative
reuse.
