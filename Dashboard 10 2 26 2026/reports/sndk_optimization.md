# SNDK Phase-1 Robust Optimization (No New Indicators)

## Recommended simulator inputs
- Use PSAR entries/exits: **Enabled**
- PSAR start step: `0.03993689255381971`
- PSAR step: `0.0018114700254550883`
- PSAR max step: `0.5708632629304844`
- Hard Stop: **Enabled**
- Hard stop % (UI): `2.8925319132736584`
- Rolling Stop: **Enabled**
- Rolling stop % (UI): `32.16142580988382`
- Cost per trade ($): `1`
- Starting account value ($): `10000`

## Full-sample constraints and performance
- Date range: `2025-02-13` to `2026-02-25`
- Strategy final equity: `$251104.85`
- Outperformance vs Buy & Hold: `42.95%`
- Trades: `8`
- Win/Loss ratio: `inf`
- Max drawdown: `-22.12%`
- Sharpe: `4.112`

## Phase-1 validation process
- No new indicators added; only PSAR + hard stop + rolling stop params optimized.
- Used multi-split walk-forward checks and stability perturbation checks.
- Selected strictness profile: `fallback_best_robust`
- Profile thresholds: `N/A` (no profile fully passed; selected best robust fallback candidate).

## Multi-split walk-forward results
- Average validation outperformance: `-10.58%`
- Average test outperformance: `-6.99%`
- Worst validation outperformance: `-24.01%`
- Worst test outperformance: `-20.86%`

### Per-split details
- Split 1:
  - Train `2025-02-13` -> `2025-08-19` outperformance `22.01%`
  - Validation `2025-08-20` -> `2025-11-18` outperformance `-2.43%`
  - Test `2025-11-19` -> `2026-02-25` outperformance `12.39%`
- Split 2:
  - Train `2025-02-13` -> `2025-09-25` outperformance `22.01%`
  - Validation `2025-09-26` -> `2025-12-08` outperformance `-24.01%`
  - Test `2025-12-09` -> `2026-02-25` outperformance `-20.86%`
- Split 3:
  - Train `2025-02-13` -> `2025-10-31` outperformance `22.01%`
  - Validation `2025-11-03` -> `2025-12-26` outperformance `-5.30%`
  - Test `2025-12-29` -> `2026-02-25` outperformance `-12.49%`

## Stability filter (parameter perturbations)
- Perturbation samples tested: `5`
- Median outperformance across perturbations: `42.95%`
- Worst outperformance across perturbations: `29.52%`

## Profile attempt summary
- `strict` profile: `0` candidates passed
- `balanced` profile: `0` candidates passed
- `practical` profile: `0` candidates passed

## Reproduce
```bash
python3 "Dashboard 10 2 26 2026/scripts/optimize_sndk_params.py"
```
