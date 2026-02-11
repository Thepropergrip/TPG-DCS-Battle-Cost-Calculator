**# TPG DCS Battle Cost Calculator (V1.2)**

A real-cost, real-time economic warfare tracker for DCS World.

Tracks actual weapon expenditures and platform losses using individually priced database entries — not broad categories. Displays coalition spending, percentage of total war cost, and full line-item breakdowns during mission runtime.

Designed for realism, analysis, and large-scale scenario evaluation.

---

**## What It Tracks**

- Missiles fired  
- Rockets and bombs  
- Ground unit losses  
- Static object destruction  
- Aircraft crashes  
- Naval losses  
- Individual weapon quantities  
- Coalition-specific totals  
- Real USD-based pricing (2026 adjusted)  
- Currency conversion (Top 10 global currencies)  

**Every weapon and unit is priced individually inside the database.**

If something shows `$0`, check `dcs.log` or the on-screen display for the exact object name and add it to the DB.

---

**## Display Modes**

Radio menu → **TPG Battle Cost Counter**

- Expanded Display (full breakdown)  
- Minimal Display (coalition totals only)  
- Display OFF (still recording)  
- Script ON / OFF (hard stop)  
- Export Full Report to `dcs.log`  
- Currency Selection  

Expanded mode shows:

- Weapon name  
- Quantity fired  
- Line-item cost total  
- Percentage of coalition total  
- Coalition subtotal  
- Overall war total  

---

**## Cost Philosophy**

All pricing is:

- Adjusted to 2026 USD  
- Based on public procurement data  
- Secondary market estimates for legacy systems  
- Realistic modern export valuations where applicable  

**This script intentionally does not use generalized aircraft category pricing. Each item is individually defined.**

---

**## Installation**

1. Open Mission Editor  
2. Add Trigger → **MISSION START**  
3. Add Action → **DO SCRIPT FILE**  
4. Load: `TPG_Battle_Cost_Calculator_v1.2.lua`  

No external frameworks required.

---

**## Adding New Weapons**

Inside the `unitCosts` table:

```lua
["Exact_DCS_Object_Name"] = 123456,
