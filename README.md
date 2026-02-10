TPG Battle Cost Counter (DCS World) – V1

Real-time economic warfare tracking for DCS World.

TPG Battle Cost Counter monitors every tracked weapon fired and every qualifying unit loss during a mission, using real 2026 USD cost estimates — not broad category averages. It calculates coalition totals, percentage balance of fire, and displays a live economic dashboard in-game.

Designed for realism-focused scenarios, large-scale modern warfare missions, and post-mission economic analysis.

 Features

Tracks individual weapon expenditures

Tracks aircraft, ground, naval, and static unit losses

Real-world 2026 USD cost estimates per unit

Live in-game economic balance chart

Coalition breakdown (Blue vs Red)

Expanded / Minimal / Hidden / No Display modes

Script hard ON/OFF toggle

Export full report to DCS.log

Drop-in ready (DO SCRIPT FILE / MISSION START)

 What It Shows

Total economic impact per coalition

Percentage share of total war cost

Itemized fired weapons with cost and % of coalition spend

Itemized losses with cost and % impact

Full war total

Everything updates live during the mission.

 Installation

Open your mission in Mission Editor

Add a trigger:

Type: MISSION START

Action: DO SCRIPT FILE

Select the TPG script

Save mission

No dependencies required.

🎛 Radio Menu Controls (F10 Other)

Expanded Display

Minimal Display

Hidden Display

No Display (Silent Running)

Script ON

Script OFF (Hard Stop)

Export Full Report to Log

 How Costs Work

All calculations are stored in 2026 USD.

If something isn’t counting:

Check the in-game display (it prints the exact DCS object name with a $0 if not found)

Or check dcs.log / debrief log for the exact unit or weapon name

Add it to the unitCosts database

⚠ Notes

Small arms burst spam and some cannon fire are intentionally excluded.

Costs are derived from public sources and inflation-adjusted estimates.

This script is for entertainment and mission realism purposes only.

 Ideal For

Modern naval engagements

Large-scale air wars

Realism events

PvP economic warfare scenarios

Post-mission cost analysis
