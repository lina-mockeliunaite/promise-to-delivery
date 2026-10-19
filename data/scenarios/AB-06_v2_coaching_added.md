# DRAFT Statement of Work — Alder Bank

Date: 16 October 2026

Between Elva ("Provider") and Alder Bank ("Customer"). Draft for discussion. Annex A forms part of this Statement of Work.

## 1. Purpose

This Statement of Work describes implementation of the Provider's scam protection for the Customer's outbound instant payments.

## 2. Hosting

Provider will host the Customer's dedicated environment on Amazon Web Services in the Sydney region.

## 3. Payment decisions

Provider will score outbound instant payments in accordance with the Payment Decision Specification in Annex A. Real-time scoring will handle up to 200,000 payments per day at launch.

## 4. Investigations

Payments held for review will open as cases in Provider's case management workspace, with a full case audit history.

## 5. Scam coaching detection

Through its connector to BioCatch, Provider will use behavioural signals from the Customer's mobile and internet banking to flag customers who appear to be coached by a scammer, from the 1 February 2027 launch, subject to the beta terms agreed in the pricing schedule.

## 6. Governance

The parties will hold a weekly project status meeting during implementation.

## Annex A — Payment Decision Specification

A.1 Outbound instant payments of AUD 1,000 or more are scored in real time before the payment is released.

A.2 Outbound instant payments below AUD 1,000 are scored in batches at hourly intervals after release.

A.3 This specification applies to outbound instant payments from Alder personal and business accounts.
