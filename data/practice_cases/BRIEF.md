# Practice cases: Tidewater Pay (development only, fictional)

Drafted by Claude on 3 Oct 2026 at Lina's request, for the fair rules-vs-agent comparison (DECISIONS 2026-10-03, 11:00). Singapore; same catalogue as the other deals; no Solana, no Australian market, nothing modelled on the sealed deal.

**Purpose.** The rules score 100% on Harbour Bank and the hard cases, so those deals cannot show whether an agent adds detection. These cases test both checkers on promises worded the way sales teams actually write: paraphrased capability names ("instant risk check", "audit trail", "counterparty data sharing"), units outside the catalogue ("checks", "30k"), quarter dates, a mode carried over from a previous call turn, and an unlisted network.

**Balance.** 12 commitments: 5 with issues (Polygon real time against an hourly-batch SOW; Tron, unlisted; 30k/day against a 25k limit and a 20k SOW; sanctions 120,000/day against 100,000; VASP by Q1 2027 against a June 2027 roadmap date) and 7 without (Ethereum real time, Polygon batch, case audit history, alert assignment, 20k/day, plus one exploratory and one conditional statement that must not be flagged). Clean cases measure false flags, so an over-eager checker is penalised.

**Disclosed bias.** Claude wrote these knowing the rules' vocabulary, so most issue cases use wording the rules do not recognise. Expect the rules to miss them; that is what the set is for. A result here shows whether the agent recovers what the rules miss without adding false flags. It is not an unbiased estimate of either checker; Coral Pay on 14 Oct is.

**Signed off by Lina, 3 Oct 2026.** Three judgement calls confirmed (Tron is a firm screening promise by reference to the preceding turn; 30k/day against the SOW's unqualified 20,000/day is a contractual contradiction; graph analytics is conditional, no issue). Two wording corrections applied before freezing (PC-04 "every case"; PC-02 "sanctions checks"). Frozen in `data/practice_cases.sha256` (five documents, manifest, two label files). This BRIEF, the labels and the fingerprint file are never extraction or checker inputs.

**Next, after Lina's commit:** one extraction run (`python extract.py practice_cases`, about $0.02, needs the API key); pin the exact run file in `config.LEDGER_IMPORT_RUN_FILES` and add the deal to `LEDGER_DEALS`, keeping the subset checks. Labels are never changed after seeing extraction or checker results; misses and disagreements are recorded against the frozen ground truth.
