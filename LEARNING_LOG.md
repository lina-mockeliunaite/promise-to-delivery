# Learning log

## Day 1 — Friday 25 September 2026

**Learned:** When my code calls the model, it sends a key, a model name and my message, and gets back an envelope of blocks — the model's thinking first, then the text answer. I pay per token for both, including the thinking I never see: about 65 in, 380 out, half a cent per run. The first real output also showed me the prompt decides what the system finds — it ignored "our go-live depends on it", the line that makes the promise risky.

**Stuck on:** Setup took most of the day — Claude Code not found (PATH), a placeholder API key, git not knowing who I was, GitHub refusing passwords. I followed the steps but couldn't yet explain all of them.

**Failure:** I pasted my real API key into the chat and had to revoke it. My script also crashed because it read the thinking block instead of the answer, and then printed nothing because of one stray colon — valid code that silently did the wrong thing.

**Still unclear:** Much of the setup felt too technical; I wouldn't yet know how to fix a PATH problem on my own. I spent time on three rounds of design changes after saying the design was frozen — worth watching from Day 2.

**Open question for Day 3:** Should extraction capture customer statements — reliance ("our go-live depends on it") and obligations — alongside vendor commitments?


## 2026-09-27 — Day 2

**Learned:** A region's catalogue record can hold its status, approval rule, limits and GA date together, so I can check a promise against the right market.

**Stuck on:** reading the exercise instructions (what "predict what it will print" meant; where to run commands vs edit files). Pasted file contents into Terminal once.

**Failure:** typo "reqiures" and "2027-o3-31" passed as valid JSON. Removed a comma on purpose: error reported line 5, mistake on line 4.

**Still unclear:** How to reliably extract one commitment spread across several turns of a conversation.

**Scorecard 25 Sep:** 2, 2, 1, 1, 1, 1, 1, 1, 1, 1

**Scope:** Harbour Bank drift storyline moved to Day 3 (time ceiling).


## 2026-09-28/29 — Day 3

**Learned:** A statement records exactly what was said and how firmly; a commitment groups statements with the same material terms. Contract references have to be followed to their actual terms before I decide what is included.

**Stuck on:** Whether SOW §3 and contract clause 3.4 should both produce rows. I resolved it by asking whether each sentence states material terms of its own or only points to them elsewhere.

**Failure:** The brief initially called C05 and C06 overcommitments but missed that both also meet my written expectation-gap rule. I corrected the labels rather than scoring against the brief's intended summary.

**Still unclear:** I can apply authorisation to C01, but I want to explain more crisply why it attaches to the consolidated terms once a firm promise exists, without implying that its earlier exploratory and conditional statements became firm. How to label an authorised training promise omitted from Coral Pay's contract also remains open.


## 2026-09-29 — Day 4

**Learned:** A fair baseline needs the same evidence as the later system. Catching all three planted conflicts in one run is impressive, but it does not show that every issue was found or that the result will repeat.

**Stuck on:** Separating a standard service that Elva is authorised to sell from a service actually allocated to Coral Pay's deal.

**Failure:** I initially thought 3 of 3 would be the whole story. The baseline missed C06's expectation gap even though it found C06's overcommitment, which taught me to score issues as well as cases.

**Still unclear:** Whether the rules can give a useful verdict for every commitment without producing noise when the internal note is silent, as it is for Coral Pay.
