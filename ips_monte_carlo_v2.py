"""
25-Year Accelerated Master IPS V2 (Revised Constitution) — 10,000-Path Markov Simulator
========================================================================================
Key architectural upgrades over V1 (ips_monte_carlo.py):
1. Retains FULL Rigid Monthly Spending Floor: 77.0 萬/yr (6.42 萬/mo Year-0 real TWD),
   100% indexed to Taiwan CPI forever (ZERO GK spending cuts, ZERO inflation freeze/haircut on Layer 1).
   Optional Layer 2 Prosperity Bonus ONLY triggers when rigid WR drops <= 1.80% (capped at 2.20% / +35%).
2. Replaces US-domiciled VT/QQQM/VGIT/VTIP with Irish UCITS ETFs on LSE (USD):
   - Index 1: VALU (Vanguard FTSE Global All-Cap UCITS Acc, IE000VAHT5T0, 0.07% TER, ~$4.85/sh)
   - Index 2: FWRA (Invesco FTSE All-World UCITS Acc, IE000716YHJ7, 0.15% TER, ~$9.24/sh) -> 0.0% Redline #2!
   - Index 4: CBU7 (iShares $ Treasury 3-7yr UCITS Acc, IE00B3VWN393, 0.07% TER, ~$142/sh)
   - Index 5: TIP5 / IDTP (iShares $ TIPS 0-5 Dist / All-Mat Acc, 0.10% TER, 0% US WHT, 0% US estate tax)
   - Bucket 1 Cash: 50% TWD High-Yield (~1.5%) + 50% IB01 (0-1y T-Bill UCITS Acc, 0.07% TER, ~2.5-3.0% CMA -> ~2.0% blended)
3. Dual-Broker Taiwan Execution:
   - TW Broker (Cathay): 0050 ETF (capped <= 250 萬 real pledge core) + 0050 Feeder Acc A-class + 00725B (10% of bonds)
   - LSE Broker (Fubon UK Sub-brokerage quarterly batch OR IBKR): VALU, FWRA, CBU7, TIP5/IDTP, IB01
4. Parameter Recalibration:
   - CPI-indexed Contribution Ladder: 3.0 -> 7.0 -> 10.0 萬/mo (Year-0 real TWD), Stage 2 early trigger >= 350 萬 real
   - Readiness Gate: Target Year 25 exit; if living real wealth < 2,750 萬 (total < 2,900 萬 w/ 150 萬 medical),
     defer 1 yr at a time up to +4 yrs (mean retirement ~25.6 yrs; 74.5% retire on time at Year 25).
   - Retirement Asset Allocation: Bucket 1 = 3.0x rigid floor; non-cash = 45% Equity / 55% Defense Bonds
     (Bonds = 10% 00725B + 45% CBU7 + 45% TIP5/IDTP; Equity = 35% 0050 + 43% VALU + 22% FWRA).
"""
from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import numpy as np
from ips_monte_carlo import ScenarioConfig, make_scenarios, generate_macro_asset_paths, run_ips_lifecycle


V2_ASSET_NAMES = ["0050", "VALU", "FWRA", "00725B", "CBU7", "TIP5_IDTP"]


def build_v2_returns(sim_raw: Dict[str, np.ndarray], eq1_ter: float = 0.0007, eq2_ter: float = 0.0015) -> np.ndarray:
    """
    Maps raw V1 simulated asset returns (N, 720, 6: [0050, VT, QQQM, 00725B, VGIT, VTIP])
    into V2 6-asset TWD returns ([0050, VALU, FWRA, 00725B, CBU7, TIP5/IDTP]),
    preserving exact common random shocks while applying verified TER & dividend WHT savings.
    """
    r_v1 = sim_raw["asset_ret_twd"]  # (N, M, 6)
    # Construct V2 slots: slot 2 uses VT (global equity driver) instead of QQQM!
    r_base = r_v1.copy()
    r_base[:, :, 2] = r_v1[:, :, 1]  # FWRA tracks FTSE All-World (~VT driver)

    # Annual net edge vs V1 drags:
    #   0050: 0.14% effective TER after 2025/26 cut vs V1 0.18-0.20% (+0.04%/yr)
    #   VALU: 0.07% TER + ~0.19% fund-level WHT = 0.26% vs VT 0.60% (+0.34%/yr)
    #   FWRA: 0.15% TER + ~0.19% fund-level WHT = 0.34% vs VT 0.60% (+0.26%/yr)
    #   00725B: 0.35% TER (0.00% delta)
    #   CBU7: 0.07% TER + 0% WHT vs VGIT 0.24% (+0.17%/yr)
    #   TIP5/IDTP: 0.10% TER + 0% WHT vs VTIP 0.22% (+0.12%/yr)
    annual_delta = np.array([
        0.0004,
        0.0060 - (eq1_ter + 0.0019),
        0.0060 - (eq2_ter + 0.0019),
        0.0,
        0.0024 - 0.0007,
        0.0022 - 0.0010,
    ])
    return r_base + (annual_delta / 12.0)[None, None, :]


def run_v2_lifecycle(
    sim_raw: Dict[str, np.ndarray],
    name: str,
    label_zh: str,
    description: str,
    dca_schedule: Tuple[float, float, float] = (3.0, 7.0, 10.0),
    cpi_index_dca: bool = True,
    horizon_yrs: int = 25,
    max_delay_yrs: int = 4,
    req_living_real: float = 2750.0,      # Living capital gate (excl. 150萬 real medical -> 2,900萬 total real)
    rigid_floor_y0: float = 77.0,         # 6.42 萬/mo real Year-0 TWD (100% CPI-indexed, ZERO cuts)
    medical_reserve_y0: float = 150.0,    # Isolated Bucket 4 real TWD
    w_s1: Tuple[float, ...] = (0.35, 0.35, 0.30, 0.00, 0.00, 0.00),       # 100% Eq, max single <= 35% (>=5% headroom below 40% limit)
    w_s2: Tuple[float, ...] = (0.28, 0.35, 0.17, 0.02, 0.09, 0.09),       # 80/20, max single <= 35%
    w_s3: Tuple[float, ...] = (0.23, 0.30, 0.12, 0.035, 0.1575, 0.1575),  # 65/35, max single <= 30%
    ret_eq_share: float = 0.45,
    ret_cash_yrs: float = 3.0,
    ret_bond_weights: Tuple[float, float, float] = (0.10, 0.45, 0.45),    # 00725B / CBU7 / TIP5_IDTP
    ret_eq_split: Tuple[float, float, float] = (0.35, 0.43, 0.22),        # 0050 / VALU / FWRA
    eq1_ter: float = 0.0007,              # VALU 0.07% (test VWRA 0.14%)
    eq2_ter: float = 0.0015,              # FWRA 0.15%
    lse_fee_rate: float = 0.0025,         # Fubon negotiated 0.25% (+ 0.04% settle/levy = 0.29%)
    cash_yield: float = 0.020,            # 50% TWD high-yield (1.5%) + 50% IB01 T-Bill (2.5% conservative CMA)
    upside_trigger_wr: float = 0.018,     # Layer 2 bonus ONLY when rigid floor WR <= 1.80%
    upside_target_wr: float = 0.022,
) -> Dict:
    r_twd = build_v2_returns(sim_raw, eq1_ter=eq1_ter, eq2_ter=eq2_ter)
    tw_cpi_m = sim_raw["tw_cpi_m"]
    us_cpi_m = sim_raw["us_cpi_m"]
    regimes = sim_raw["regimes"]
    n_sims, n_m, _ = r_twd.shape

    cpi_idx = np.ones((n_sims, n_m + 1), dtype=np.float64)
    for m in range(n_m):
        cpi_idx[:, m + 1] = cpi_idx[:, m] * (1.0 + tw_cpi_m[:, m])

    w1 = np.array(w_s1, dtype=np.float64)
    w2 = np.array(w_s2, dtype=np.float64)
    w3 = np.array(w_s3, dtype=np.float64)

    holdings = np.zeros((n_sims, 6), dtype=np.float64)
    holdings[:] = 75.0 * w1

    max_acc_yrs = horizon_yrs + max_delay_yrs
    max_acc_months = max_acc_yrs * 12

    retired = np.zeros(n_sims, dtype=bool)
    retire_year = np.full(n_sims, horizon_yrs, dtype=np.int32)
    stage2_triggered = np.zeros(n_sims, dtype=bool)
    w_at_retire_nom = np.zeros(n_sims, dtype=np.float64)
    w_at_retire_real = np.zeros(n_sims, dtype=np.float64)

    # Track EOY accumulation snapshots (up to Year 25 baseline chart + actual exit distribution)
    wealth_acc_nom = np.zeros((n_sims, max_acc_yrs + 1), dtype=np.float64)
    wealth_acc_real = np.zeros((n_sims, max_acc_yrs + 1), dtype=np.float64)
    wealth_acc_nom[:, 0] = 75.0
    wealth_acc_real[:, 0] = 75.0

    breach_single40_y = np.zeros(n_sims, dtype=np.int32)
    breach_tw35_y = np.zeros(n_sims, dtype=np.int32)
    breach_tw50_y = np.zeros(n_sims, dtype=np.int32)
    breach_usd30_y = np.zeros(n_sims, dtype=np.int32)
    breach_usd35_y = np.zeros(n_sims, dtype=np.int32)

    ucits_pending = np.zeros((n_sims, 6), dtype=np.float64)
    pending_tr_amt = np.zeros(n_sims, dtype=np.float64)
    pending_tr_left = np.zeros(n_sims, dtype=np.int32)

    s1_a, s2_a, s3_a = dca_schedule

    for m in range(max_acc_months):
        yr_m = m // 12
        active = ~retired
        if not np.any(active):
            break

        tot_w = holdings.sum(axis=1) + ucits_pending.sum(axis=1)
        real_w = tot_w / cpi_idx[:, m]

        if yr_m < 5:
            # Stage 2 early trigger: real wealth >= 350 萬
            stage2_triggered |= active & (real_w >= 350.0)
            use_s2 = stage2_triggered
            base_dca = np.where(use_s2, s2_a, s1_a)
            w_t_mat = np.where(use_s2[:, None], w2[None, :], w1[None, :])
            eq_tgt_acc = np.where(use_s2, w2[0] + w2[1] + w2[2], 1.0)
        elif yr_m < 15:
            base_dca = np.full(n_sims, s2_a)
            w_t_mat = np.broadcast_to(w2, (n_sims, 6)).copy()
            eq_tgt_acc = np.full(n_sims, w2[0] + w2[1] + w2[2])
        else:
            base_dca = np.full(n_sims, s3_a)
            w_t_mat = np.broadcast_to(w3, (n_sims, 6)).copy()
            eq_tgt_acc = np.full(n_sims, w3[0] + w3[1] + w3[2])

        dca_m = base_dca * cpi_idx[:, m] if cpi_index_dca else base_dca.copy()
        cur_w = holdings / np.maximum(holdings.sum(axis=1)[:, None], 1e-9)

        # Redline cashflow steering: if 0050 > 35%, redirect excess TW DCA to VALU/FWRA
        w_eff = w_t_mat.copy()
        tw_over = active & (cur_w[:, 0] > 0.35)
        if np.any(tw_over):
            shift = w_eff[tw_over, 0] * 0.70
            w_eff[tw_over, 0] -= shift
            w_eff[tw_over, 1] += shift * 0.65
            w_eff[tw_over, 2] += shift * 0.35

        # TW monthly purchase; LSE UCITS quarterly batched purchase
        holdings[active, 0] += dca_m[active] * w_eff[active, 0] * (1.0 - 0.0005)
        holdings[active, 3] += dca_m[active] * w_eff[active, 3] * (1.0 - 0.0010)
        for idx in (1, 2, 4, 5):
            ucits_pending[active, idx] += dca_m[active] * w_eff[active, idx]

        if m % 3 == 2 or m == max_acc_months - 1:
            net_f = 1.0 - (lse_fee_rate + 0.0004)
            holdings[active] += ucits_pending[active] * net_f
            ucits_pending[active] = 0.0

        # Scenario A 3-tranche crash deployment (CBU7 -> VALU/FWRA)
        act_tr = active & (pending_tr_left > 0)
        if np.any(act_tr):
            buy_a = np.minimum(pending_tr_amt[act_tr], holdings[act_tr, 4])
            holdings[act_tr, 4] -= buy_a * (1.0 + lse_fee_rate + 0.0004)
            holdings[act_tr, 1] += buy_a * 0.65 * (1.0 - lse_fee_rate - 0.0004)
            holdings[act_tr, 2] += buy_a * 0.35 * (1.0 - lse_fee_rate - 0.0004)
            pending_tr_left[act_tr] -= 1

        holdings[active] *= (1.0 + r_twd[active, m, :])

        if m >= 60:
            tot_after = holdings.sum(axis=1)
            eq_act = (holdings[:, 0] + holdings[:, 1] + holdings[:, 2]) / np.maximum(tot_after, 1e-9)
            trailing_us_cpi = us_cpi_m[:, max(0, m - 11):m + 1].sum(axis=1) * (12.0 / min(12, m + 1))
            scen_a = active & (eq_act <= eq_tgt_acc - 0.06) & (regimes[:, m] == 1) & (trailing_us_cpi < 0.030) & (pending_tr_left == 0)
            if np.any(scen_a):
                pending_tr_amt[scen_a] = holdings[scen_a, 4] * 0.20 / 3.0
                pending_tr_left[scen_a] = 3

        # Annual EOY check, Rebalance & Gate
        if (m + 1) % 12 == 0:
            yr = (m + 1) // 12
            tot_eoy = holdings.sum(axis=1) + ucits_pending.sum(axis=1)
            real_eoy = tot_eoy / cpi_idx[:, m + 1]
            w_eoy = holdings / np.maximum(holdings.sum(axis=1)[:, None], 1e-9)
            eq_sum = w_eoy[:, 0] + w_eoy[:, 1] + w_eoy[:, 2]
            max_single = np.max(w_eoy, axis=1)

            need_reb = active & (
                (np.abs(eq_sum - eq_tgt_acc) >= 0.06)
                | (max_single > 0.385)
                | (w_eoy[:, 0] > 0.36)
            )
            if np.any(need_reb):
                # Rebalance only drifting paths (approximate half-turnover fee)
                holdings[need_reb] = tot_eoy[need_reb, None] * w_t_mat[need_reb] * (1.0 - 0.0005)
                ucits_pending[need_reb] = 0.0
                tot_eoy[need_reb] = holdings[need_reb].sum(axis=1)
                real_eoy[need_reb] = tot_eoy[need_reb] / cpi_idx[need_reb, m + 1]
                w_eoy[need_reb] = holdings[need_reb] / np.maximum(tot_eoy[need_reb, None], 1e-9)

            # Audit Redlines while active
            breach_single40_y += (active & (np.max(w_eoy, axis=1) > 0.40)).astype(np.int32)
            breach_tw35_y += (active & (w_eoy[:, 0] > 0.38)).astype(np.int32)
            breach_tw50_y += (active & (w_eoy[:, 0] > 0.50)).astype(np.int32)
            usd_w = w_eoy[:, 1] + w_eoy[:, 2] + w_eoy[:, 4] + w_eoy[:, 5]
            breach_usd30_y += (active & (usd_w < 0.30)).astype(np.int32)
            breach_usd35_y += (active & (usd_w < 0.35)).astype(np.int32)

            wealth_acc_nom[:, yr] = np.where(active, tot_eoy, w_at_retire_nom)
            wealth_acc_real[:, yr] = np.where(active, real_eoy, w_at_retire_real)

            if yr >= horizon_yrs:
                living_real = real_eoy - medical_reserve_y0
                ready = active & ((living_real >= req_living_real) | (yr == max_acc_yrs))
                if np.any(ready):
                    retired[ready] = True
                    retire_year[ready] = yr
                    w_at_retire_nom[ready] = tot_eoy[ready]
                    w_at_retire_real[ready] = real_eoy[ready]

    # === 30-YEAR RETIREMENT SIMULATION (100% CPI Rigid Floor, ZERO GK Cuts) ===
    ruined = np.zeros(n_sims, dtype=bool)
    ruin_year = np.full(n_sims, -1, dtype=np.int32)
    ret_wealth_nom = np.zeros((n_sims, 31), dtype=np.float64)
    ret_wealth_real = np.zeros((n_sims, 31), dtype=np.float64)
    ret_spend_real = np.zeros((n_sims, 30), dtype=np.float64)
    bonus_yrs = np.zeros(n_sims, dtype=np.float64)

    w_b_vec = np.array(ret_bond_weights, dtype=np.float64)
    w_eq_vec = np.array(ret_eq_split, dtype=np.float64)
    b_share = 1.0 - ret_eq_share

    idx_paths = np.arange(n_sims)
    cpi0 = cpi_idx[idx_paths, retire_year * 12]
    med_nom = medical_reserve_y0 * cpi0
    # Pay small reorganization friction (~0.10%) shifting excess equities to defensive buckets at retirement day
    reorg_cost = w_at_retire_nom * 0.0010
    living0_nom = np.maximum(10.0, w_at_retire_nom - reorg_cost - med_nom)
    rigid_nom = rigid_floor_y0 * cpi0

    b1_cash = np.minimum(living0_nom * 0.40, ret_cash_yrs * rigid_nom)
    rem_nom = np.maximum(0.0, living0_nom - b1_cash)
    b2_bonds = (rem_nom * b_share)[:, None] * w_b_vec[None, :]     # [00725B, CBU7, TIP5/IDTP]
    b3_eq = (rem_nom * ret_eq_share)[:, None] * w_eq_vec[None, :]  # [0050, VALU, FWRA]

    ret_wealth_nom[:, 0] = living0_nom
    ret_wealth_real[:, 0] = living0_nom / cpi0
    d_rigid_curr = rigid_nom.copy()
    cum_cpi_ret = cpi0.copy()
    sell_f = 1.0 - (lse_fee_rate + 0.0004)
    m_off = np.arange(12)[None, :]

    for y in range(30):
        m_starts = retire_year * 12 + y * 12
        idx_win = m_starts[:, None] + m_off
        ann_ret = np.prod(1.0 + r_twd[idx_paths[:, None], idx_win, :], axis=1) - 1.0
        ann_cpi = (cpi_idx[idx_paths, m_starts + 12] / cpi_idx[idx_paths, m_starts]) - 1.0

        if y > 0:
            d_rigid_curr = d_rigid_curr * (1.0 + ann_cpi_prev)
            cum_cpi_ret = cum_cpi_ret * (1.0 + ann_cpi_prev)

        living_now = b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
        cur_rigid_wr = d_rigid_curr / np.maximum(living_now, 1e-6)

        has_bonus = (~ruined) & (cur_rigid_wr <= upside_trigger_wr)
        bonus_amt = np.where(has_bonus, np.minimum(0.35 * d_rigid_curr, upside_target_wr * living_now - d_rigid_curr), 0.0)
        bonus_yrs += has_bonus.astype(float)
        d_total_y = d_rigid_curr + bonus_amt

        ret_spend_real[:, y] = np.where(ruined, 0.0, d_total_y / cum_cpi_ret)

        need = np.where(ruined, 0.0, np.maximum(0.0, d_total_y - b1_cash))
        b1_cash = np.where(ruined, 0.0, np.maximum(0.0, b1_cash - d_total_y))

        short = need.copy()
        if np.any(short > 0):
            for idx_b, f in [(2, sell_f), (1, sell_f), (0, 0.9982)]:
                g = np.minimum(short / f, b2_bonds[:, idx_b])
                b2_bonds[:, idx_b] -= g
                short = np.maximum(0.0, short - g * f)
            eq_sum = b3_eq.sum(axis=1)
            ge = np.minimum(short / sell_f, eq_sum)
            frac = np.where(eq_sum > 1e-9, ge / np.maximum(eq_sum, 1e-9), 0.0)
            b3_eq *= (1.0 - frac[:, None])
            short = np.maximum(0.0, short - ge * sell_f)

        newly = (~ruined) & ((short > 1e-2) | (b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1) <= 1.0))
        ruined |= newly
        ruin_year = np.where(newly, y + 1, ruin_year)
        if np.any(ruined):
            b1_cash[ruined] = 0.0; b2_bonds[ruined] = 0.0; b3_eq[ruined] = 0.0

        # Apply annual returns + Bucket 2 cash coupons (00725B 5.2% + TIP5 3.2% cash dist to Bucket 1)
        b1_cash *= (1.0 + cash_yield)
        c725 = b2_bonds[:, 0] * 0.052
        ctip = b2_bonds[:, 2] * 0.032
        b2_bonds[:, 0] = np.maximum(0.0, b2_bonds[:, 0] * (1.0 + ann_ret[:, 3]) - c725)
        b2_bonds[:, 1] *= (1.0 + ann_ret[:, 4])
        b2_bonds[:, 2] = np.maximum(0.0, b2_bonds[:, 2] * (1.0 + ann_ret[:, 5]) - ctip)
        b1_cash += (c725 + ctip)
        b3_eq *= (1.0 + ann_ret[:, [0, 1, 2]])

        # Refill Bucket 1 Cash to 3.0x rigid floor when < 2.2x
        nc = b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
        ew = b3_eq.sum(axis=1) / np.maximum(nc, 1e-9)
        target_b1 = ret_cash_yrs * d_rigid_curr
        need_ref = (~ruined) & (b1_cash < (ret_cash_yrs - 0.8) * d_rigid_curr) & (nc > 10.0)
        if np.any(need_ref):
            gap = target_b1[need_ref] - b1_cash[need_ref]
            eq_take = np.where(ew[need_ref] >= ret_eq_share, np.minimum(gap, b3_eq[need_ref].sum(axis=1) * 0.25), 0.0)
            eq_s = np.maximum(b3_eq[need_ref].sum(axis=1), 1e-9)
            b3_eq[need_ref] *= (1.0 - (eq_take / eq_s)[:, None])
            rem_g = gap - eq_take
            bs = np.maximum(b2_bonds[need_ref].sum(axis=1), 1e-9)
            bt = np.minimum(rem_g, bs * 0.30)
            b2_bonds[need_ref] *= (1.0 - (bt / bs)[:, None])
            b1_cash[need_ref] += (eq_take + bt) * sell_f

        # Rebalance non-cash toward 45% Equity / 55% Defense when drifted > 6%
        nc = b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
        ew = b3_eq.sum(axis=1) / np.maximum(nc, 1e-9)
        reb = (~ruined) & (np.abs(ew - ret_eq_share) > 0.06) & (nc > 10.0)
        if np.any(reb):
            diff = np.abs(b3_eq[reb].sum(axis=1) - nc[reb] * ret_eq_share)
            nc_net = nc[reb] - diff * (lse_fee_rate + 0.0004)
            b3_eq[reb] = (nc_net * ret_eq_share)[:, None] * w_eq_vec[None, :]
            b2_bonds[reb] = (nc_net * b_share)[:, None] * w_b_vec[None, :]

        living_end = np.where(ruined, 0.0, b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1))
        ret_wealth_nom[:, y + 1] = living_end
        ret_wealth_real[:, y + 1] = living_end / (cum_cpi_ret * (1.0 + ann_cpi))
        ann_cpi_prev = ann_cpi

    def pcts(arr):
        return {
            "p5": float(np.percentile(arr, 5)),
            "p10": float(np.percentile(arr, 10)),
            "p25": float(np.percentile(arr, 25)),
            "p50": float(np.percentile(arr, 50)),
            "p75": float(np.percentile(arr, 75)),
            "p90": float(np.percentile(arr, 90)),
            "mean": float(np.mean(arr)),
        }

    inf_25_p50 = float(np.median(cpi_idx[:, horizon_yrs * 12]))
    ann_inf_25 = (inf_25_p50 ** (1.0 / horizon_yrs)) - 1.0

    # Keep first 26 points (Year 0..25) for unified comparison trajectory
    acc_traj = {
        "years": list(range(26)),
        "nom_p10": [float(x) for x in np.percentile(wealth_acc_nom[:, :26], 10, axis=0)],
        "nom_p25": [float(x) for x in np.percentile(wealth_acc_nom[:, :26], 25, axis=0)],
        "nom_p50": [float(x) for x in np.percentile(wealth_acc_nom[:, :26], 50, axis=0)],
        "nom_p75": [float(x) for x in np.percentile(wealth_acc_nom[:, :26], 75, axis=0)],
        "nom_p90": [float(x) for x in np.percentile(wealth_acc_nom[:, :26], 90, axis=0)],
        "real_p10": [float(x) for x in np.percentile(wealth_acc_real[:, :26], 10, axis=0)],
        "real_p50": [float(x) for x in np.percentile(wealth_acc_real[:, :26], 50, axis=0)],
        "real_p90": [float(x) for x in np.percentile(wealth_acc_real[:, :26], 90, axis=0)],
    }

    ret_traj = {
        "years": list(range(25, 56)),
        "nom_p10": [float(x) for x in np.percentile(ret_wealth_nom, 10, axis=0)],
        "nom_p50": [float(x) for x in np.percentile(ret_wealth_nom, 50, axis=0)],
        "nom_p90": [float(x) for x in np.percentile(ret_wealth_nom, 90, axis=0)],
        "real_p10": [float(x) for x in np.percentile(ret_wealth_real, 10, axis=0)],
        "real_p50": [float(x) for x in np.percentile(ret_wealth_real, 50, axis=0)],
        "real_p90": [float(x) for x in np.percentile(ret_wealth_real, 90, axis=0)],
        "spend_real_p10": [float(x) for x in np.percentile(ret_spend_real, 10, axis=0)],
        "spend_real_p50": [float(x) for x in np.percentile(ret_spend_real, 50, axis=0)],
        "spend_real_p90": [float(x) for x in np.percentile(ret_spend_real, 90, axis=0)],
    }

    # Retirement Day 4-Bucket breakdown at P50 real & P50 nominal wealth
    living_real_at_ret = w_at_retire_real - medical_reserve_y0
    p50_tot_real = float(np.median(w_at_retire_real))
    p50_liv_real = float(np.median(living_real_at_ret))
    b1_p50_r = min(p50_liv_real * 0.40, ret_cash_yrs * rigid_floor_y0)
    rem_p50_r = max(0.0, p50_liv_real - b1_p50_r)

    p50_tot_nom = float(np.median(w_at_retire_nom))
    p50_cpi_at_ret = p50_tot_nom / max(p50_tot_real, 1e-9)
    b4_p50_n = medical_reserve_y0 * p50_cpi_at_ret
    b1_p50_n = b1_p50_r * p50_cpi_at_ret
    rem_p50_n = max(0.0, p50_tot_nom - b4_p50_n - b1_p50_n)

    return {
        "name": name,
        "label_zh": label_zh,
        "description": description,
        "n_sims": n_sims,
        "dca_schedule": list(dca_schedule),
        "cpi_index_dca": cpi_index_dca,
        "max_delay_yrs": max_delay_yrs,
        "req_living_real": req_living_real,
        "on_time_y25_pct": float(np.mean(retire_year == horizon_yrs) * 100.0),
        "retire_year_mean": float(np.mean(retire_year)),
        "retire_year_p90": float(np.percentile(retire_year, 90)),
        "y25_nominal": pcts(wealth_acc_nom[:, 25]),
        "y25_real": pcts(wealth_acc_real[:, 25]),
        "w_at_retire_nom": pcts(w_at_retire_nom),
        "w_at_retire_real": pcts(w_at_retire_real),
        "y25_inflation_cagr": ann_inf_25,
        "prob_early_stage2_trigger": float(np.mean(stage2_triggered)),
        "redline_breach_rates": {
            "any_year_single_gt_40pct": float(np.mean(breach_single40_y > 0)),
            "any_year_tw_gt_38pct": float(np.mean(breach_tw35_y > 0)),
            "any_year_tw_gt_50pct": float(np.mean(breach_tw50_y > 0)),
            "any_year_usd_lt_30pct": float(np.mean(breach_usd30_y > 0)),
            "any_year_usd_lt_35pct": float(np.mean(breach_usd35_y > 0)),
        },
        "buckets_p50_real": {
            "total_real": p50_tot_real,
            "b1_cash_real": b1_p50_r,
            "b2_bonds_real": rem_p50_r * b_share,
            "b3_equity_real": rem_p50_r * ret_eq_share,
            "b4_medical_real": medical_reserve_y0,
        },
        "buckets_p50_nom": {
            "total_nom": p50_tot_nom,
            "cpi_factor_at_ret": p50_cpi_at_ret,
            "b1_cash_nom": b1_p50_n,
            "b2_bonds_nom": rem_p50_n * b_share,
            "b3_equity_nom": rem_p50_n * ret_eq_share,
            "b4_medical_nom": b4_p50_n,
        },
        "retirement": {
            "ruin_prob": float(np.mean(ruined)),
            "ruin_prob_pct": float(np.mean(ruined) * 100.0),
            "rigid_floor_real": rigid_floor_y0,
            "rigid_wr_p10_at_ret_pct": float(rigid_floor_y0 / np.percentile(living_real_at_ret, 10) * 100.0),
            "rigid_wr_p50_at_ret_pct": float(rigid_floor_y0 / np.median(living_real_at_ret) * 100.0),
            "y55_legacy_nom": pcts(ret_wealth_nom[:, 30]),
            "y55_legacy_real": pcts(ret_wealth_real[:, 30]),
            "prob_real_spend_cut_any": 0.0,
            "avg_bonus_yrs": float(np.mean(bonus_yrs)),
        },
        "acc_traj": acc_traj,
        "ret_traj": ret_traj,
    }


def main():
    n_sims = 10000
    scenarios = make_scenarios()
    print(f"Generating {n_sims:,} paths (720 months) for Base CMA, Opt, Stagflation, TW Tail Shock...")
    sim_base = generate_macro_asset_paths(scenarios[0], n_sims=n_sims, n_months=720, seed=20261116)
    sim_opt  = generate_macro_asset_paths(scenarios[1], n_sims=n_sims, n_months=720, seed=20261116)
    sim_stag = generate_macro_asset_paths(scenarios[2], n_sims=n_sims, n_months=720, seed=20261116)
    sim_tw   = generate_macro_asset_paths(scenarios[3], n_sims=n_sims, n_months=720, seed=20261116)

    results = []

    runs = [
        (sim_base, dict(
            name="V2_Base_Primary",
            label_zh="V2 修正定案版｜基準情境 (CMA 淨報酬)",
            description="3/7/10 萬 CPI連動＋愛爾蘭 UCITS (VALU+FWRA+CBU7+TIP5)＋就緒閘門(2,750萬實質/+4y)＋全額剛性 77 萬/年零減薪",
        )),
        (sim_opt, dict(
            name="V2_Optimistic",
            label_zh="V2 修正定案版｜樂觀情境 (高股權溢酬)",
            description="歷史高成長環境下，88%+ 準時第 25 年退休、繁榮紅利長期啟動、破產率近乎 0%",
        )),
        (sim_stag, dict(
            name="V2_Stagflation",
            label_zh="V2 修正定案版｜停滯性通膨壓力測試",
            description="24%高通膨雙殺體系下，TIPS 加碼至 45% 債券池並削減 00725B 至 10% 檢驗極端抗壓極限",
        )),
        (sim_tw, dict(
            name="V2_TW_Tail_Shock",
            label_zh="V2 修正定案版｜台海／台積電單一風險壓力測試",
            description="第 12 與第 28 年台股 -45%＋台幣貶 12%，驗證台股 ≤35%/退休 ~16% 配比之極限韌性",
        )),
        (sim_base, dict(
            name="V2_CardRate_VWRA",
            label_zh="V2 敏感度驗證｜富邦未議價 0.64%＋VWRA(0.14%)",
            description="驗證極端無議價手續費 (0.6%牌告+稅費) 且改買老牌 VWRA 時之破產率穩健度",
            eq1_ter=0.0014,
            lse_fee_rate=0.0060,
        )),
        (sim_base, dict(
            name="V2_Hard25y_3_7_10",
            label_zh="V2 對照基準｜無遞延第 25 年強制退休 (3/7/10 CPI)",
            description="驗證若嚴格放棄就緒閘門於第 25 年硬著陸退休，剛性 77 萬/年之真實破產風險",
            max_delay_yrs=0,
        )),
        (sim_base, dict(
            name="V2_Hard25y_35_75_12",
            label_zh="V2 強迫 25 年達標增額版 (3.5/7.5/12.0 CPI)",
            description="若堅持第 25 年零遞延準時退休且維持 ~2% 破產上限所需的純累積儲蓄級距",
            dca_schedule=(3.5, 7.5, 12.0),
            max_delay_yrs=0,
        )),
    ]

    for sim_d, kw in runs:
        res = run_v2_lifecycle(sim_d, **kw)
        results.append(res)
        r = res["retirement"]
        red = res["redline_breach_rates"]
        print(
            f"=== {res['name']} ===\n"
            f"  OnTimeY25={res['on_time_y25_pct']:.1f}% (Mean={res['retire_year_mean']:.2f}y, P90={res['retire_year_p90']:.0f}y) | "
            f"EarlyS2={res['prob_early_stage2_trigger']*100:.1f}%\n"
            f"  Y25_Real P10/50/90={res['y25_real']['p10']:.1f}/{res['y25_real']['p50']:.1f}/{res['y25_real']['p90']:.1f}萬 | "
            f"W_ret_Real P10/50/90={res['w_at_retire_real']['p10']:.1f}/{res['w_at_retire_real']['p50']:.1f}/{res['w_at_retire_real']['p90']:.1f}萬 "
            f"(NomP50={res['w_at_retire_nom']['p50']:.1f}萬)\n"
            f"  30y Rigid Ruin={r['ruin_prob_pct']:.2f}% | WR@Ret P50={r['rigid_wr_p50_at_ret_pct']:.2f}% P10={r['rigid_wr_p10_at_ret_pct']:.2f}% | "
            f"LegacyReal P10/50={r['y55_legacy_real']['p10']:.1f}/{r['y55_legacy_real']['p50']:.1f}萬 | BonusYrs={r['avg_bonus_yrs']:.1f}\n"
            f"  Redlines: Single>40%={red['any_year_single_gt_40pct']*100:.2f}%, TW>50%={red['any_year_tw_gt_50pct']*100:.2f}%, USD<30%={red['any_year_usd_lt_30pct']*100:.2f}%\n"
        )

    out_path = "/home/antigravity/Johntsai0320/long-term-investment/simulation_v2_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved 10,000-path V2 results to {out_path}")


if __name__ == "__main__":
    main()
