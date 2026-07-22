# Risk Policy — MEXC 200x CROSS mode (user preference)

| Parameter | Value |
|-----------|--------|
| Leverage | **200x** |
| Margin mode | **CROSS** (default) — Isolated optional in UI |
| Init margin / stop budget | **≤ 0.5% of wallet** |
| Stop vs liquidation | Stop **must** be before liquidation |

## Isolated vs Cross (samajh lo)

| | Isolated | Cross |
|--|----------|-------|
| Margin | Sirf us trade ka | Poora wallet share |
| Liquidation pe max loss | ~us position ka margin (~0.5% agar size sahi) | **Zyada ho sakta hai** — wallet ka bada hissa |
| 200x pe | Safer for “0.5% cap” | Flexible, lekin khatarnak |

Tum **CROSS** use kar rahe ho: is liye **0.5% sirf initial margin / stop budget** hai —
liquidation aayi to loss 0.5% se **zyada** ho sakta hai. Is liye stop bilkul tight +
liq se pehle zaroori hai.

## Math (long, approx)

```
init_margin ≈ equity × 0.5%
notional ≈ init_margin × 200
liq ≈ entry × (1 - 1/200 + mmr)   # estimate; CROSS venue math differs
```
