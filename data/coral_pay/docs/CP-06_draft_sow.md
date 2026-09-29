# DRAFT Statement of Work — Coral Pay

Date: 25 November 2026

Between Elva ("Provider") and Coral Pay ("Customer"). Draft for discussion. Annex A forms part of this Statement of Work.

## 1. Purpose

This Statement of Work describes implementation of the Provider's controls for Customer's contractor payout launch.

## 2. Hosting

Provider will deploy Customer's production environment on Microsoft Azure in the Australia East region.

## 3. Payout ledger integration

The payout ledger connector will handle up to 12,000 payouts per day at launch.

## 4. Sanctions screening

Provider's sanctions screening API will screen up to 25,000 payer and beneficiary names per day.

## 5. Payout exceptions

Payout exceptions will be managed in Provider's case management workspace.

## 6. Wallet screening

Provider will provide NUSD recipient-wallet screening for Customer's Solana payouts through Elva's pre-built analytics integration, in accordance with the Wallet Screening Specification in Annex A.

## 7. Out of scope

Screening of Customer's Ethereum payout wallets, which Customer performs through its own provider.

## 8. Governance

The parties will hold a weekly project status meeting during implementation.

## Annex A — Wallet Screening Specification

A.1 Solana: each NUSD recipient wallet is screened through the analytics integration in real time before the payout is released.

A.2 This specification applies to NUSD payouts on Solana.
