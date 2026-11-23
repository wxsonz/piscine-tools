# 002 Parallel workers for v0
Status: accepted
Date: 2026-11-22

## Context
The Code Book (PLAN-1) and rule 11.04 say a v0 is one agent. The user asked
for a swarm of workers: the tool must work by Monday 2026-11-23 and the work
splits into folders with little overlap.

## Choice
Breaks PLAN-1 / 11.04 on purpose, for this v0 only. The lead writes the top
first (PLAN.md, AGENTS.md, tool/SHAPES.md, every CONTRACT.md, subject.txt,
the wiring file, tests/run.py). Then one worker per folder (PLAN.md §10),
each writing only the folders it OWNs, coding against the contracts. The lead
integrates and runs the one check.

## Why
Speed for the deadline. The cost 11.04 warns about (ceremony, tokens) is kept
down by: no boards, no QA cards, no review rounds; contracts as the only
coordination; one check command. After Monday, back to one agent.
