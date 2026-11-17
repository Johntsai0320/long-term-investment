"""
25-Year Accelerated Master IPS — Feasibility Audit & Markov Regime-Switching Monte Carlo Simulator
==================================================================================================
Simulates 55 years (300 monthly accumulation steps + 30 annual retirement steps) across 10,000
correlated, fat-tailed (Student-t), 3-regime Markov-switching paths in TWD (nominal & CPI-real).

Assets modeled (all mapped to TWD total returns net of TER, dividend withholding, & trading friction):
  0: 0050     - Taiwan Top 50 ETF / Feeder Fund (Accumulating in Stage 2+)
  1: VT       - Vanguard Total World Stock ETF (USD, 30% US div WHT)
  2: QQQM     - Invesco Nasdaq-100 ETF (USD, 30% US div WHT)
  3: 00725B   - Cathay 10+ Yr BBB USD Corp Bond ETF (TWD-listed, unhedged USD, eff. dur ~11.86y)
  4: VGIT     - Vanguard Intermediate-Term Treasury ETF (USD, QI QII refund ~95%)
  5: VTIP     - Vanguard Short-Term Inflation-Protected Securities ETF (USD, dur ~2.5y, CPI-linked)
"""

from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np


ASSET_NAMES = ["0050", "VT", "QQQM", "00725B", "VGIT", "VTIP"]


@dataclass
class ScenarioConfig:
    name: str
    label_zh: str
    description: str
    # Transition matrix rows: [Normal(0), Recession(1), Stagflation(2)] monthly probs
    trans_matrix: np.ndarray
    # Expected annual *nominal USD/local* total returns before tax/fees per regime (6 assets)
    mu_ann: np.ndarray  # shape (3, 6)
    # Annual volatilities per regime (6 assets)
    vol_ann: np.ndarray  # shape (3, 6)
    # Annual FX (USD/TWD) drift & vol per regime (+ means USD appreciates vs TWD)
    fx_mu_ann: np.ndarray  # shape (3,)
    fx_vol_ann: np.ndarray  # shape (3,)
    # Annual Taiwan CPI drift & vol per regime
    tw_cpi_mu: np.ndarray  # shape (3,)
    tw_cpi_vol: np.ndarray  # shape (3,)
    # Annual US CPI drift & vol per regime
    us_cpi_mu: np.ndarray  # shape (3,)
    us_cpi_vol: np.ndarray  # shape (3,)
    # Correlation matrices per regime: shape (3, 8, 8) -> [6 assets, FX, TW_CPI]
    corr_mats: np.ndarray
    # Student-t degrees of freedom (fat tails)
    df_t: float = 7.0
    # Whether to inject a deterministic/stochastic Taiwan tail shock
    tw_tail_shock: bool = False
    # Retirement spending mode: "variable_ips" (4.25% of W25) or "fixed_real"
    retire_spend_mode: str = "variable_ips"
    fixed_real_spend_y0: float = 77.0  # in 萬元 (Year-0 real TWD)
    # Whether to disable GK cuts (to measure pure spending shortfall) or keep GK
    apply_gk: bool = True
    # Use improved allocation (fixes Stage 1 >40% VT, Year-16 VT breach, reduces 00725B duration)
    improved_portfolio: bool = False


def build_corr_matrices(stagflation_tight: bool = False) -> np.ndarray:
    """
    8x8 correlation matrices per regime:
    Order: [0050, VT, QQQM, 00725B, VGIT, VTIP, USD/TWD, TW_CPI]
    Note: 00725B/VT/QQQM/VGIT/VTIP local returns; FX is correlated with global risk-off (USD rises
    when equities crash!) and 0050 falls more when TWD weakens on capital outflows.
    """
    # Regime 0: Normal Expansion (negative stock-Treasury corr, mild credit corr)
    c0 = np.array([
        [ 1.00,  0.65,  0.60,  0.15, -0.10, -0.05, -0.25,  0.05],  # 0050
        [ 0.65,  1.00,  0.90,  0.25, -0.15, -0.05, -0.20,  0.05],  # VT
        [ 0.60,  0.90,  1.00,  0.20, -0.15, -0.05, -0.18,  0.05],  # QQQM
        [ 0.15,  0.25,  0.20,  1.00,  0.65,  0.35,  0.05, -0.10],  # 00725B
        [-0.10, -0.15, -0.15,  0.65,  1.00,  0.55,  0.10, -0.15],  # VGIT
        [-0.05, -0.05, -0.05,  0.35,  0.55,  1.00,  0.05,  0.25],  # VTIP
        [-0.25, -0.20, -0.18,  0.05,  0.10,  0.05,  1.00,  0.15],  # FX (USD/TWD)
        [ 0.05,  0.05,  0.05, -0.10, -0.15,  0.25,  0.15,  1.00],  # TW_CPI
    ])

    # Regime 1: Recession / Deflationary Crash (Scenario A: VGIT rallies strongly rho ~ -0.45,
    # 00725B credit spreads widen so weakly pos/zero corr with equities, USD spikes as safe haven)
    c1 = np.array([
        [ 1.00,  0.75,  0.72,  0.25, -0.40, -0.15, -0.45, -0.15],
        [ 0.75,  1.00,  0.92,  0.30, -0.45, -0.15, -0.40, -0.15],
        [ 0.72,  0.92,  1.00,  0.25, -0.42, -0.15, -0.35, -0.15],
        [ 0.25,  0.30,  0.25,  1.00,  0.35,  0.20, -0.10, -0.10],
        [-0.40, -0.45, -0.42,  0.35,  1.00,  0.55,  0.25, -0.10],
        [-0.15, -0.15, -0.15,  0.20,  0.55,  1.00,  0.10,  0.20],
        [-0.45, -0.40, -0.35, -0.10,  0.25,  0.10,  1.00,  0.10],
        [-0.15, -0.15, -0.15, -0.10, -0.10,  0.20,  0.10,  1.00],
    ])

    # Regime 2: Stagflation / Rate-Hike Shock (Scenario B: Stock-Bond rho >= 0.50!
    # VTIP decouples positively with inflation, 00725B & VGIT fall with stocks)
    r_sb = 0.62 if stagflation_tight else 0.55
    c2 = np.array([
        [ 1.00,  0.72,  0.68,  r_sb,  0.48,  0.05, -0.30, -0.25],
        [ 0.72,  1.00,  0.92,  r_sb,  0.55,  0.05, -0.25, -0.25],
        [ 0.68,  0.92,  1.00,  0.52,  0.50,  0.05, -0.20, -0.25],
        [ r_sb,  r_sb,  0.52,  1.00,  0.82,  0.20, -0.10, -0.40],
        [ 0.48,  0.55,  0.50,  0.82,  1.00,  0.30,  0.05, -0.40],
        [ 0.05,  0.05,  0.05,  0.20,  0.30,  1.00,  0.10,  0.45],
        [-0.30, -0.25, -0.20, -0.10,  0.05,  0.10,  1.00,  0.25],
        [-0.25, -0.25, -0.25, -0.40, -0.40,  0.45,  0.25,  1.00],
    ])

    mats = np.stack([c0, c1, c2], axis=0)
    # Ensure exact positive definiteness via eigenvalue floor
    for k in range(3):
        eigvals, eigvecs = np.linalg.eigh(mats[k])
        eigvals = np.maximum(eigvals, 1e-4)
        m = eigvecs @ np.diag(eigvals) @ eigvecs.T
        d = np.sqrt(np.diag(m))
        mats[k] = m / np.outer(d, d)
    return mats


def make_scenarios() -> List[ScenarioConfig]:
    # Stationary dist of baseline transition: ~76% Normal, ~13% Recession, ~11% Stagflation
    trans_base = np.array([
        [0.975, 0.015, 0.010],
        [0.105, 0.880, 0.015],
        [0.080, 0.020, 0.900],
    ])

    # Transition matrix with higher stagflation persistence (~24% stationary stagflation)
    trans_stag = np.array([
        [0.960, 0.015, 0.025],
        [0.095, 0.875, 0.030],
        [0.065, 0.020, 0.915],
    ])

    # Baseline Institutional Forward CMA (Net of ETF TER & WHT handled explicitly in simulator!)
    # Here mu_ann is GROSS local-currency total return (before 30% US div WHT & TER).
    # Stationary blended nominal gross returns under trans_base:
    #   0050: 0.76*0.105 + 0.13*(-0.18) + 0.11*(-0.05) = ~5.1%? Wait -> arithmetic mean vs geometric!
    # Careful: in log-normal / GBM, E[R] arithmetic must account for -0.5*sigma^2 drag!
    # Let's calibrate mu_ann (arithmetic annual drift) so geometric net TWD CAGR matches institutional CMA:
    # Target net geometric CAGRs (Institutional CMA):
    #   0050: ~7.3% nominal TWD (gross ~7.5%, after 0.16% TER & Stage 1 div tax)
    #   VT:   ~7.2% gross USD -> after 0.06% TER + 0.54% (30% of 1.8% div) = ~6.6% net USD
    #   QQQM: ~8.0% gross USD -> after 0.15% TER + 0.21% (30% of 0.7% div) = ~7.6% net USD
    #   00725B: ~4.9% net USD/TWD (high coupon ~5.5% minus credit loss/roll ~0.3% minus 0.35% TER)
    #   VGIT: ~4.1% gross USD -> ~4.0% net USD (after QI refund)
    #   VTIP: ~3.7% gross USD -> ~3.6% net USD
    # Remember: geo ≈ arith - 0.5*vol^2! For vol=18%, 0.5*0.18^2 = 1.62%!
    # So for 0050 to have ~7.5% gross geometric CAGR, arith blended needs ~9.1%.
    mu_cma = np.array([
        # [0050,   VT,    QQQM,  00725B, VGIT,  VTIP]
        [ 0.125,  0.115,  0.135,  0.062,  0.042,  0.035],  # Regime 0: Expansion
        [-0.140, -0.140, -0.180,  0.005,  0.075,  0.030],  # Regime 1: Recession (00725B spread widens!)
        [-0.030, -0.040, -0.080, -0.045, -0.025,  0.052],  # Regime 2: Stagflation (long dur bond hurt!)
    ])

    vol_base = np.array([
        [0.165, 0.140, 0.195, 0.095, 0.050, 0.030],  # Regime 0
        [0.290, 0.260, 0.330, 0.155, 0.075, 0.045],  # Regime 1
        [0.240, 0.210, 0.280, 0.145, 0.070, 0.042],  # Regime 2
    ])

    # IPS Optimistic Calibration (higher equity risk premium + lower drag ~ historical 2010-2025 US/TW boom)
    mu_opt = np.array([
        [ 0.142,  0.132,  0.158,  0.068,  0.045,  0.036],
        [-0.120, -0.120, -0.150,  0.015,  0.080,  0.035],
        [-0.015, -0.020, -0.055, -0.035, -0.020,  0.055],
    ])

    # Stagflation Stress (lower expansion returns, severe stagflation inflation & rate shocks)
    mu_stag = np.array([
        [ 0.112,  0.105,  0.120,  0.058,  0.040,  0.035],
        [-0.160, -0.160, -0.210, -0.010,  0.070,  0.028],
        [-0.060, -0.070, -0.115, -0.075, -0.045,  0.062],
    ])

    fx_mu = np.array([-0.002, 0.035, 0.015])  # USD appreciates in recessions & stagflation
    fx_vol = np.array([0.048, 0.075, 0.065])

    tw_cpi_mu_base = np.array([0.018, 0.008, 0.045])
    tw_cpi_vol_base = np.array([0.009, 0.012, 0.018])
    us_cpi_mu_base = np.array([0.022, 0.010, 0.055])
    us_cpi_vol_base = np.array([0.010, 0.014, 0.020])

    tw_cpi_mu_stag = np.array([0.024, 0.015, 0.056])
    us_cpi_mu_stag = np.array([0.028, 0.018, 0.065])

    corr_base = build_corr_matrices(stagflation_tight=False)
    corr_stag = build_corr_matrices(stagflation_tight=True)

    return [
        ScenarioConfig(
            name="B_CMA_Base",
            label_zh="基準情境（機構前瞻 CMA 淨報酬）",
            description="2026+ 機構前瞻資本市場假設，含 30% 美股股利預扣稅、複委託摩擦與三體系肥尾衝擊",
            trans_matrix=trans_base,
            mu_ann=mu_cma,
            vol_ann=vol_base,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=tw_cpi_mu_base,
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
        ),
        ScenarioConfig(
            name="A_IPS_Optimistic",
            label_zh="樂觀情境（貼近 IPS 歷史假設校準）",
            description="反推與驗證 IPS 宣稱之「第 25 年 P50 達 3,120.5 萬、破產率 0.21%」所需報酬結構",
            trans_matrix=trans_base,
            mu_ann=mu_opt,
            vol_ann=vol_base * 0.95,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=np.array([0.016, 0.006, 0.040]),
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
        ),
        ScenarioConfig(
            name="C_Stagflation",
            label_zh="停滯性通膨壓力測試（高 Regime 2 機率）",
            description="高通膨黏性（均值 ~3.2%）＋股債正相關雙殺，重創長天期 00725B",
            trans_matrix=trans_stag,
            mu_ann=mu_stag,
            vol_ann=vol_base * 1.05,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol * 1.1,
            tw_cpi_mu=tw_cpi_mu_stag,
            tw_cpi_vol=tw_cpi_vol_base * 1.2,
            us_cpi_mu=us_cpi_mu_stag,
            us_cpi_vol=us_cpi_vol_base * 1.2,
            corr_mats=corr_stag,
        ),
        ScenarioConfig(
            name="D_TW_Tail_Shock",
            label_zh="台海／台積電單一風險壓力測試",
            description="基準 CMA 加上第 12 年與第 28 年台股結構性重挫（0050 -45%＋台幣貶 12%）檢驗美元避險底線",
            trans_matrix=trans_base,
            mu_ann=mu_cma,
            vol_ann=vol_base,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=tw_cpi_mu_base,
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
            tw_tail_shock=True,
        ),
        ScenarioConfig(
            name="E_Fixed_Real_Goal",
            label_zh="固定實質目標＋GK護欄（今日 6.4 萬/月起跳）",
            description="基準 CMA 下，第 25 年固定要求今日 77 萬/年購買力（不隨累積結果打折），仍允許 GK 減薪護欄保護本金",
            trans_matrix=trans_base,
            mu_ann=mu_cma,
            vol_ann=vol_base,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=tw_cpi_mu_base,
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
            retire_spend_mode="fixed_real",
            fixed_real_spend_y0=77.0,
        ),
        ScenarioConfig(
            name="E2_Rigid_77_NoGK",
            label_zh="純剛性生活費壓力測試（今日 6.4 萬/月，無法減薪）",
            description="基準 CMA 下，假設 77 萬/年實質支出為剛性基本生活費（無法啟動 GK 降薪 10%），揭露未砍生活費前的真實破產率",
            trans_matrix=trans_base,
            mu_ann=mu_cma,
            vol_ann=vol_base,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=tw_cpi_mu_base,
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
            retire_spend_mode="fixed_real",
            fixed_real_spend_y0=77.0,
            apply_gk=False,
        ),
        ScenarioConfig(
            name="F_Improved_IPS",
            label_zh="修正版 IPS（解決紅線衝突與長債存續期過長）",
            description="修正單一標的 ≤40%、分散台股集中度、縮短信用債存續期並調升投資級/國債均衡防禦力",
            trans_matrix=trans_base,
            mu_ann=mu_cma,
            vol_ann=vol_base,
            fx_mu_ann=fx_mu,
            fx_vol_ann=fx_vol,
            tw_cpi_mu=tw_cpi_mu_base,
            tw_cpi_vol=tw_cpi_vol_base,
            us_cpi_mu=us_cpi_mu_base,
            us_cpi_vol=us_cpi_vol_base,
            corr_mats=corr_base,
            improved_portfolio=True,
        ),
    ]


def generate_macro_asset_paths(
    cfg: ScenarioConfig, n_sims: int, n_months: int = 660, seed: int = 20261116
) -> Dict[str, np.ndarray]:
    """
    Vectorized 55-year (660 months) Markov Regime-Switching simulation with Student-t shocks.
    Uses common random seed across scenarios for low-variance comparison.
    Returns monthly gross TWD net-of-TER/WHT total returns for all 6 assets, plus FX & CPI paths.
    """
    rng = np.random.default_rng(seed)

    # Stationary initial regime distribution
    pi0 = np.linalg.matrix_power(cfg.trans_matrix, 1000)[0]
    pi0 = np.maximum(pi0, 0.0)
    pi0 /= pi0.sum()

    # Precompute Cholesky factors of 8x8 correlation matrices
    chol = np.stack([np.linalg.cholesky(cfg.corr_mats[r]) for r in range(3)], axis=0)

    # ETF annual TER + dividend tax drag (approximate monthly geometric drag)
    # 0050: Stage 1 ETF ~0.16% TER + ~0.5% net div tax drag if >=20% bracket (or 0 if <20%);
    #       Stage 2+ 0050 Feeder (Accumulating): ~0.18% TER, 0 dividend tax!
    # VT:   0.06% TER + 30% * 1.8% div = 0.60% annual drag
    # QQQM: 0.15% TER + 30% * 0.7% div = 0.36% annual drag
    # 00725B: 0.35% TER, 0 US WHT (Taiwan ETF portfolio interest exempt), 0 NHI
    # VGIT: 0.04% TER + ~5% residual non-QII leakage on ~4.0% yield = 0.24% annual drag
    # VTIP: 0.04% TER + ~5% residual leakage on ~3.5% yield = 0.22% annual drag
    ann_drag_s1 = np.array([0.0020, 0.0060, 0.0036, 0.0035, 0.0024, 0.0022])
    ann_drag_s2p = np.array([0.0018, 0.0060, 0.0036, 0.0035, 0.0024, 0.0022])

    regimes = np.zeros((n_sims, n_months), dtype=np.int8)
    r_curr = rng.choice(3, size=n_sims, p=pi0)

    asset_ret_twd = np.zeros((n_sims, n_months, 6), dtype=np.float64)
    fx_ret = np.zeros((n_sims, n_months), dtype=np.float64)
    tw_cpi_m = np.zeros((n_sims, n_months), dtype=np.float64)
    us_cpi_m = np.zeros((n_sims, n_months), dtype=np.float64)

    dt = 1.0 / 12.0
    sqrt_dt = np.sqrt(dt)
    # Scale Student-t so variance = 1: std(t_df) = sqrt(df / (df - 2))
    t_scale = np.sqrt((cfg.df_t - 2.0) / cfg.df_t)
    cum_trans = np.cumsum(cfg.trans_matrix, axis=1)

    for m in range(n_months):
        regimes[:, m] = r_curr

        # Correlated Student-t shocks: Z ~ N(0, I), Chi2 scaling per path for tail co-crash!
        z = rng.standard_normal((n_sims, 8))
        chi2 = rng.chisquare(cfg.df_t, size=(n_sims, 1))
        t_factor = np.sqrt(cfg.df_t / chi2) * t_scale

        shocks = np.empty((n_sims, 8), dtype=np.float64)
        for r in range(3):
            mask = (r_curr == r)
            if np.any(mask):
                shocks[mask] = (z[mask] @ chol[r].T) * t_factor[mask]

        # Extract regime params per simulation path
        mu_a = cfg.mu_ann[r_curr]          # (n_sims, 6)
        vol_a = cfg.vol_ann[r_curr]        # (n_sims, 6)
        f_mu = cfg.fx_mu_ann[r_curr]       # (n_sims,)
        f_vol = cfg.fx_vol_ann[r_curr]     # (n_sims,)
        c_mu = cfg.tw_cpi_mu[r_curr]       # (n_sims,)
        c_vol = cfg.tw_cpi_vol[r_curr]     # (n_sims,)
        uc_mu = cfg.us_cpi_mu[r_curr]      # (n_sims,)

        # Monthly log returns for assets (local currency), FX, and CPI
        drag = ann_drag_s1 if m < 60 else ann_drag_s2p
        # Arithmetic mean mu_a -> log drift = mu_a - 0.5*vol_a^2 - drag
        log_ret_local = (mu_a - 0.5 * (vol_a ** 2) - drag) * dt + vol_a * sqrt_dt * shocks[:, :6]
        log_fx = (f_mu - 0.5 * (f_vol ** 2)) * dt + f_vol * sqrt_dt * shocks[:, 6]
        cpi_tw = np.maximum(-0.005, c_mu * dt + c_vol * sqrt_dt * shocks[:, 7])
        cpi_us = np.maximum(-0.005, uc_mu * dt + cfg.us_cpi_vol[r_curr] * sqrt_dt * shocks[:, 7])

        # VTIP gets extra real-time US CPI pass-through relative to expected inflation
        # (since VTIP principal adjusts with actual US CPI)
        unexpected_us_cpi = cpi_us - uc_mu * dt
        log_ret_local[:, 5] += 0.65 * unexpected_us_cpi

        # Convert USD-exposure assets (VT=1, QQQM=2, 00725B=3, VGIT=4, VTIP=5) to TWD!
        # Note: 00725B is TWD-traded but holds unhedged USD corporate bonds!
        r_local = np.expm1(log_ret_local)
        r_fx = np.expm1(log_fx)
        r_twd = r_local.copy()
        r_twd[:, 1:] = (1.0 + r_local[:, 1:]) * (1.0 + r_fx[:, None]) - 1.0

        # Taiwan Geopolitical / TSMC Concentration Tail Shock (Scenario D)
        # Inject acute 6-month structural shock in Year 12 (m=132..137) and Year 28 (m=324..329)
        if cfg.tw_tail_shock:
            if 132 <= m <= 137 or 324 <= m <= 329:
                # 0050 drops ~-45% cumulative over 6 months, TWD weakens (USD/TWD +12% cumulative)
                r_twd[:, 0] = (1.0 + r_twd[:, 0]) * (0.55 ** (1.0 / 6.0)) - 1.0
                fx_shock = (1.12 ** (1.0 / 6.0)) - 1.0
                r_twd[:, 1:] = (1.0 + r_twd[:, 1:]) * (1.0 + fx_shock) - 1.0
                r_fx = (1.0 + r_fx) * (1.0 + fx_shock) - 1.0

        asset_ret_twd[:, m, :] = r_twd
        fx_ret[:, m] = r_fx
        tw_cpi_m[:, m] = cpi_tw
        us_cpi_m[:, m] = cpi_us

        # Transition regimes for next month
        u = rng.random(n_sims)
        cprobs = cum_trans[r_curr]
        r_curr = (u[:, None] > cprobs).sum(axis=1).astype(np.int8)

    return {
        "asset_ret_twd": asset_ret_twd,
        "fx_ret": fx_ret,
        "tw_cpi_m": tw_cpi_m,
        "us_cpi_m": us_cpi_m,
        "regimes": regimes,
    }


def run_ips_lifecycle(cfg: ScenarioConfig, sim_data: Dict[str, np.ndarray]) -> Dict:
    """
    Executes the exact 25-year Accumulation (Module A + Module R checks)
    followed by 30-year Retirement (Module B 4-Bucket + 3-Phase CPI + GK Guardrails).
    All monetary values are in 萬元 (10,000 TWD).
    """
    r_twd = sim_data["asset_ret_twd"]   # (N, 660, 6)
    tw_cpi_m = sim_data["tw_cpi_m"]     # (N, 660)
    us_cpi_m = sim_data["us_cpi_m"]     # (N, 660)
    regimes = sim_data["regimes"]       # (N, 660)

    n_sims = r_twd.shape[0]
    # Cumulative Taiwan CPI index (base 1.0 at t=0)
    cpi_idx = np.ones((n_sims, 661), dtype=np.float64)
    for m in range(660):
        cpi_idx[:, m + 1] = cpi_idx[:, m] * (1.0 + tw_cpi_m[:, m])

    # Portfolio holdings across 6 assets in 萬元
    holdings = np.zeros((n_sims, 6), dtype=np.float64)

    # Initial 75萬 at t=0
    if not cfg.improved_portfolio:
        w0 = np.array([0.40, 0.45, 0.15, 0.0, 0.0, 0.0])
    else:
        # Improved Stage 1: keeps single asset <= 40%, trims TW to 35%, adds 10% VGIT defense
        w0 = np.array([0.35, 0.40, 0.15, 0.0, 0.10, 0.0])
    holdings[:] = 75.0 * w0

    # Target weights per stage
    if not cfg.improved_portfolio:
        w_s1 = np.array([0.40, 0.45, 0.15, 0.0, 0.0, 0.0])
        w_s2 = np.array([0.40, 0.317, 0.133, 0.075, 0.050, 0.025])
        w_s3 = np.array([0.35, 0.35, 0.0, 0.15, 0.105, 0.045])
    else:
        # Improved IPS: single ETF <= 40%, reduced credit duration risk, keeps risk budget realistic
        w_s1 = np.array([0.35, 0.40, 0.15, 0.0, 0.10, 0.0])
        w_s2 = np.array([0.35, 0.33, 0.12, 0.05, 0.10, 0.05])
        w_s3 = np.array([0.30, 0.35, 0.0, 0.10, 0.175, 0.075])

    # Track diagnostics during accumulation
    wealth_acc_nom = np.zeros((n_sims, 26), dtype=np.float64)
    wealth_acc_real = np.zeros((n_sims, 26), dtype=np.float64)
    wealth_acc_nom[:, 0] = 75.0
    wealth_acc_real[:, 0] = 75.0

    breach_single40_m = np.zeros(n_sims, dtype=np.int32)
    breach_tw50_m = np.zeros(n_sims, dtype=np.int32)
    breach_usd30_m = np.zeros(n_sims, dtype=np.int32)
    # Track pending 3-tranche VGIT -> Equity buys from Scenario A decision tree
    pending_tranche_amt = np.zeros(n_sims, dtype=np.float64)
    pending_tranche_left = np.zeros(n_sims, dtype=np.int32)
    stage2_triggered = np.zeros(n_sims, dtype=bool)
    qqqm_swap_gain_y16 = np.zeros(n_sims, dtype=np.float64)
    qqqm_cost_basis = np.full(n_sims, 75.0 * 0.15, dtype=np.float64)

    # Cathay US DCA fee: $0.1 USD ≈ 0.00032 萬元 per US ETF line item per month
    us_dca_fee_per_line = 0.00032

    for m in range(300):
        # 1. Start of Month 181 (Year 16): Sell all QQQM -> VT (0.08% sell + 0.08% buy)
        if m == 180:
            q_val = holdings[:, 2].copy()
            qqqm_swap_gain_y16 = np.maximum(0.0, q_val - qqqm_cost_basis)
            net_proceeds = q_val * (1.0 - 0.0008 - 0.0008)
            holdings[:, 2] = 0.0
            holdings[:, 1] += net_proceeds
            if cfg.improved_portfolio:
                # Rebalance excess VT above 38% into VGIT/00725B/VTIP to keep single ETF <= 40%
                tot = holdings.sum(axis=1)
                vt_w = holdings[:, 1] / np.maximum(tot, 1e-9)
                excess = np.maximum(0.0, holdings[:, 1] - 0.38 * tot)
                if np.any(excess > 0):
                    holdings[:, 1] -= excess
                    holdings[:, 4] += excess * 0.60 * (1.0 - 0.0016)
                    holdings[:, 5] += excess * 0.25 * (1.0 - 0.0016)
                    holdings[:, 3] += excess * 0.15 * (1.0 - 0.0016)

        # 2. Determine contribution stage & amount
        tot_w = holdings.sum(axis=1)
        if m < 60:
            # Stage 2 trigger: Year >= 6 OR Wealth >= 350萬
            stage2_triggered |= (tot_w >= 350.0)
            in_s2 = stage2_triggered
            dca_amt = np.where(in_s2, 4.0, 2.0)  # 4萬 vs 2萬
            w_target = np.where(in_s2[:, None], w_s2[None, :], w_s1[None, :])
            # Track QQQM cost basis
            qqqm_cost_basis += dca_amt * w_target[:, 2]
        elif m < 180:
            dca_amt = np.full(n_sims, 4.0)
            w_target = np.broadcast_to(w_s2, (n_sims, 6)).copy()
            qqqm_cost_basis += dca_amt * w_target[:, 2]
        else:
            dca_amt = np.full(n_sims, 5.5)
            w_target = np.broadcast_to(w_s3, (n_sims, 6)).copy()

        # 3. Module R Redline Steering for new monthly DCA:
        #    If 0050 > 50% or single asset > 40%, steer 0050 DCA into VT (or VGIT in improved)
        cur_weights = holdings / np.maximum(tot_w[:, None], 1e-9)
        tw_over = cur_weights[:, 0] > 0.48
        if np.any(tw_over):
            shift = w_target[tw_over, 0] * 0.5
            w_target[tw_over, 0] -= shift
            w_target[tw_over, 1] += shift

        # Execute monthly DCA purchase minus Cathay $0.1 USD fees on active US lines
        n_us_lines = (w_target[:, 1] > 0).astype(int) + (w_target[:, 2] > 0).astype(int) + \
                     (w_target[:, 4] > 0).astype(int) + (w_target[:, 5] > 0).astype(int)
        net_dca = np.maximum(0.0, dca_amt - n_us_lines * us_dca_fee_per_line)
        holdings += net_dca[:, None] * w_target

        # 4. Execute pending Scenario-A 3-tranche VGIT -> Equity deployments
        active_tr = pending_tranche_left > 0
        if np.any(active_tr):
            buy_amt = np.minimum(pending_tranche_amt[active_tr], holdings[active_tr, 4])
            # Buy VT (or VT/QQQM proportional if in Stage 2)
            holdings[active_tr, 4] -= buy_amt * (1.0 + 0.0008)
            holdings[active_tr, 1] += buy_amt * (1.0 - 0.0008)
            pending_tranche_left[active_tr] -= 1

        # 5. Apply monthly asset returns
        holdings *= (1.0 + r_twd[:, m, :])

        # 6. Check Module A Decision Tree (Scenario A vs B) when equity drift >= 5% in Stage 2/3
        if m >= 60:
            tot_after = holdings.sum(axis=1)
            eq_actual = holdings[:, :3].sum(axis=1) / np.maximum(tot_after, 1e-9)
            eq_target = 0.85 if m < 180 else (0.70 if not cfg.improved_portfolio else 0.65)
            # Trigger Scenario A if equity underweight by >= 5% AND in Recession regime (rho < 0.2, US CPI < 3%)
            # Trailing 12m US CPI approximation
            trailing_us_cpi = us_cpi_m[:, max(0, m - 11):m + 1].sum(axis=1) * (12.0 / min(12, m + 1))
            scen_a = (eq_actual <= eq_target - 0.05) & (regimes[:, m] == 1) & (trailing_us_cpi < 0.030) & (pending_tranche_left == 0)
            if np.any(scen_a):
                # Sell 20% of VGIT over 3 tranches
                vgit_20 = holdings[scen_a, 4] * 0.20
                pending_tranche_amt[scen_a] = vgit_20 / 3.0
                pending_tranche_left[scen_a] = 3

        # 7. Annual Year-End Redline Check (Months 11, 23, ..., 299)
        if (m + 1) % 12 == 0:
            yr = (m + 1) // 12
            tot_eoy = holdings.sum(axis=1)
            wealth_acc_nom[:, yr] = tot_eoy
            wealth_acc_real[:, yr] = tot_eoy / cpi_idx[:, m + 1]

            w_eoy = holdings / np.maximum(tot_eoy[:, None], 1e-9)
            if cfg.improved_portfolio:
                # Rebalance any single asset > 38.5% or TW > 45% back within redlines (no cascade overflow)
                max_w = np.max(w_eoy, axis=1)
                need_rebal = (max_w > 0.385) | (w_eoy[:, 0] > 0.45)
                if np.any(need_rebal):
                    idx_r = np.where(need_rebal)[0]
                    for i in idx_r:
                        for _pass in range(2):
                            tot_i = holdings[i].sum()
                            w_i = holdings[i] / max(tot_i, 1e-9)
                            for c_idx in range(6):
                                cap = 0.37
                                if w_i[c_idx] > cap:
                                    trim = holdings[i, c_idx] - cap * tot_i
                                    holdings[i, c_idx] -= trim
                                    # Prefer VT only if VT < 0.33, else route to VGIT/VTIP/00725B
                                    if c_idx != 1 and w_i[1] < 0.33:
                                        holdings[i, 1] += trim * 0.9980
                                    else:
                                        holdings[i, 4] += trim * 0.65 * 0.9984
                                        holdings[i, 5] += trim * 0.35 * 0.9984
                    tot_eoy = holdings.sum(axis=1)
                    w_eoy = holdings / np.maximum(tot_eoy[:, None], 1e-9)
                    wealth_acc_nom[idx_r, yr] = tot_eoy[idx_r]
                    wealth_acc_real[idx_r, yr] = tot_eoy[idx_r] / cpi_idx[idx_r, m + 1]

            breach_tw50_m += (w_eoy[:, 0] > 0.50).astype(np.int32)
            breach_single40_m += (np.max(w_eoy, axis=1) > 0.40).astype(np.int32)
            usd_w = w_eoy[:, 1] + w_eoy[:, 2] + w_eoy[:, 4] + w_eoy[:, 5]
            breach_usd30_m += (usd_w < 0.30).astype(np.int32)

    # End of Year 25 diagnostics
    w25_nom = wealth_acc_nom[:, 25].copy()
    w25_real = wealth_acc_real[:, 25].copy()
    w_eoy25 = holdings / np.maximum(w25_nom[:, None], 1e-9)

    # =========================================================================
    # MODULE B: RETIREMENT PHASE (30 YEARS = Months 300..659)
    # =========================================================================
    # Reorganize at Retirement Day (end of Year 25) into Four Buckets:
    #   Bucket 1 (Cash):    9.614% (300 / 3120.5)
    #   Bucket 2 (Bonds):  32.046% (1000 / 3120.5) -> 50% 00725B, 35% VGIT, 15% VTIP
    #   Bucket 3 (Equity): 53.668% (1674.7 / 3120.5) -> 50% 0050 Feeder, 50% VT
    #   Bucket 4 (Medical): 4.672% (145.8 / 3120.5) -> strictly isolated!
    reorg_cost = w25_nom * 0.0004
    w25_net = w25_nom - reorg_cost

    b1_cash = w25_net * (300.0 / 3120.5)
    if not cfg.improved_portfolio:
        b2_bonds = (w25_net * (1000.0 / 3120.5))[:, None] * np.array([[0.50, 0.35, 0.15]])  # [00725B, VGIT, VTIP]
    else:
        # Improved Bond Bucket: 25% 00725B (halves long credit duration risk), 50% VGIT, 25% VTIP
        b2_bonds = (w25_net * (1000.0 / 3120.5))[:, None] * np.array([[0.25, 0.50, 0.25]])
    b3_eq = (w25_net * (1674.7 / 3120.5))[:, None] * np.array([[0.50, 0.50]])  # [0050, VT]

    # Annual withdrawal budget D_1 (Year 26)
    if cfg.retire_spend_mode == "variable_ips":
        # IPS literally specifies: 4.25% of total W25 (including medical bucket in denominator!)
        d_curr = 0.0425 * w25_nom
    else:
        # Fixed real purchasing power target in Year-0 TWD, indexed to Year-25 CPI
        d_curr = cfg.fixed_real_spend_y0 * cpi_idx[:, 300]

    initial_d1_real = d_curr / cpi_idx[:, 300]

    ret_wealth_nom = np.zeros((n_sims, 31), dtype=np.float64)
    ret_wealth_real = np.zeros((n_sims, 31), dtype=np.float64)
    ret_spend_real = np.zeros((n_sims, 30), dtype=np.float64)

    # Living portfolio = Bucket 1 + Bucket 2 + Bucket 3
    living_w0 = b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
    ret_wealth_nom[:, 0] = living_w0
    ret_wealth_real[:, 0] = living_w0 / cpi_idx[:, 300]

    ruined = np.zeros(n_sims, dtype=bool)
    ruin_year = np.full(n_sims, -1, dtype=np.int32)
    gk_freeze_count = np.zeros(n_sims, dtype=np.int32)
    gk_cut_count = np.zeros(n_sims, dtype=np.int32)
    gk_raise_count = np.zeros(n_sims, dtype=np.int32)
    severe_cut_20 = np.zeros(n_sims, dtype=bool)
    severe_cut_30 = np.zeros(n_sims, dtype=bool)

    prev_port_ret = np.zeros(n_sims, dtype=np.float64)
    bond_yield_vec = np.array([0.052, 0.040, 0.034])  # 00725B, VGIT (after QII), VTIP
    cash_yield = 0.015

    for y in range(30):
        m0 = 300 + y * 12
        m1 = m0 + 12

        ann_cpi_tw = (cpi_idx[:, m1] / cpi_idx[:, m0]) - 1.0

        if y > 0:
            if cfg.retire_spend_mode == "variable_ips" or cfg.apply_gk:
                if y < 10:
                    inf_adj = np.minimum(ann_cpi_tw_prev, 0.060)
                elif y < 20:
                    inf_adj = np.minimum(np.maximum(0.0, ann_cpi_tw_prev - 0.010), 0.060)
                else:
                    inf_adj = np.minimum(np.maximum(0.0, ann_cpi_tw_prev - 0.020), 0.060)

                freeze = (prev_port_ret < 0.0) & (~ruined)
                inf_adj = np.where(freeze, 0.0, inf_adj)
                gk_freeze_count += freeze.astype(np.int32)

                d_next = d_curr * (1.0 + inf_adj)
                living_now = b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
                wr_now = d_next / np.maximum(living_now, 1e-6)

                if cfg.apply_gk:
                    cut_mask = (wr_now > 0.0510) & (~ruined)
                    raise_mask = (wr_now < 0.0340) & (~ruined)
                    d_next = np.where(cut_mask, d_next * 0.90, d_next)
                    d_next = np.where(raise_mask, d_next * 1.10, d_next)
                    gk_cut_count += cut_mask.astype(np.int32)
                    gk_raise_count += raise_mask.astype(np.int32)
                d_curr = d_next
            else:
                d_curr = d_curr * (1.0 + ann_cpi_tw_prev)

        spend_real_y = d_curr / cpi_idx[:, m0]
        ret_spend_real[:, y] = np.where(ruined, 0.0, spend_real_y)
        if y > 0:
            severe_cut_20 |= (~ruined) & (spend_real_y < 0.80 * initial_d1_real)
            severe_cut_30 |= (~ruined) & (spend_real_y < 0.70 * initial_d1_real)

        # Withdraw annual living expenses from Bucket 1 (replenish via SOP Step 4 if short)
        living_start = b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
        need_from_assets = np.where(ruined, 0.0, np.maximum(0.0, d_curr - b1_cash))
        b1_cash = np.where(ruined, 0.0, np.maximum(0.0, b1_cash - d_curr))

        short = need_from_assets.copy()
        if np.any(short > 0):
            # Gross-up sale amount for trading fees so net cash covers `short` exactly
            # 1. Trim VTIP (0.08% sell fee)
            gross_vtip = np.minimum(short / 0.9992, b2_bonds[:, 2])
            b2_bonds[:, 2] -= gross_vtip
            short = np.maximum(0.0, short - gross_vtip * 0.9992)
            # 2. Trim VGIT (0.08% sell fee)
            gross_vgit = np.minimum(short / 0.9992, b2_bonds[:, 1])
            b2_bonds[:, 1] -= gross_vgit
            short = np.maximum(0.0, short - gross_vgit * 0.9992)
            # 3. Trim 00725B (0.18% sell fee/tax)
            gross_725 = np.minimum(short / 0.9982, b2_bonds[:, 0])
            b2_bonds[:, 0] -= gross_725
            short = np.maximum(0.0, short - gross_725 * 0.9982)
            # 4. Trim Equities proportionally
            eq_sum = b3_eq.sum(axis=1)
            gross_eq = np.minimum(short / 0.9992, eq_sum)
            ratio = np.where(eq_sum > 1e-9, gross_eq / np.maximum(eq_sum, 1e-9), 0.0)
            b3_eq *= (1.0 - ratio[:, None])
            short = np.maximum(0.0, short - gross_eq * 0.9992)

        newly_ruined = (~ruined) & ((short > 1e-3) | (b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1) <= 1.0))
        ruined |= newly_ruined
        ruin_year = np.where(newly_ruined, y + 1, ruin_year)
        if np.any(ruined):
            b1_cash[ruined] = 0.0
            b2_bonds[ruined] = 0.0
            b3_eq[ruined] = 0.0

        ann_ret_6 = np.prod(1.0 + r_twd[:, m0:m1, :], axis=1) - 1.0

        b1_cash *= (1.0 + cash_yield)
        b2_tot_ret = ann_ret_6[:, [3, 4, 5]]
        b2_coupon = b2_bonds * bond_yield_vec[None, :]
        b2_after = np.maximum(0.0, b2_bonds * (1.0 + b2_tot_ret) - b2_coupon)
        b1_cash += b2_coupon.sum(axis=1)
        b2_bonds = b2_after
        b3_eq *= (1.0 + ann_ret_6[:, [0, 1]])

        living_end = b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1)
        target_b1 = 2.3 * d_curr
        base_end = np.maximum(living_start - d_curr, 1e-6)
        port_ret_y = np.where(ruined, 0.0, (living_end / base_end) - 1.0)
        prev_port_ret = port_ret_y
        ann_cpi_tw_prev = ann_cpi_tw

        refill_mask = (~ruined) & (b1_cash < 1.5 * d_curr) & (port_ret_y > 0.02)
        if np.any(refill_mask):
            gap = np.minimum(target_b1[refill_mask] - b1_cash[refill_mask], b3_eq[refill_mask].sum(axis=1) * 0.25)
            eq_s = b3_eq[refill_mask].sum(axis=1)
            take_frac = np.where(eq_s > 1e-9, gap / np.maximum(eq_s, 1e-9), 0.0)
            b3_eq[refill_mask] *= (1.0 - take_frac[:, None])
            b1_cash[refill_mask] += gap * 0.9992

        living_end = np.where(ruined, 0.0, b1_cash + b2_bonds.sum(axis=1) + b3_eq.sum(axis=1))
        ret_wealth_nom[:, y + 1] = living_end
        ret_wealth_real[:, y + 1] = living_end / cpi_idx[:, m1]

    # Summarize results
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

    # Cumulative 25-yr inflation factor
    inf_25_p50 = float(np.median(cpi_idx[:, 300]))
    ann_inf_25 = (inf_25_p50 ** (1.0 / 25.0)) - 1.0

    # Trajectory percentiles (every year 0..25 acc, 26..55 ret)
    acc_traj = {
        "years": list(range(26)),
        "nom_p10": [float(x) for x in np.percentile(wealth_acc_nom, 10, axis=0)],
        "nom_p25": [float(x) for x in np.percentile(wealth_acc_nom, 25, axis=0)],
        "nom_p50": [float(x) for x in np.percentile(wealth_acc_nom, 50, axis=0)],
        "nom_p75": [float(x) for x in np.percentile(wealth_acc_nom, 75, axis=0)],
        "nom_p90": [float(x) for x in np.percentile(wealth_acc_nom, 90, axis=0)],
        "real_p10": [float(x) for x in np.percentile(wealth_acc_real, 10, axis=0)],
        "real_p50": [float(x) for x in np.percentile(wealth_acc_real, 50, axis=0)],
        "real_p90": [float(x) for x in np.percentile(wealth_acc_real, 90, axis=0)],
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

    return {
        "name": cfg.name,
        "label_zh": cfg.label_zh,
        "description": cfg.description,
        "n_sims": n_sims,
        "y25_nominal": pcts(w25_nom),
        "y25_real": pcts(w25_real),
        "y25_inflation_cagr": ann_inf_25,
        "y25_weights_p50": {ASSET_NAMES[i]: float(np.median(w_eoy25[:, i])) for i in range(6)},
        "prob_reach_3120": float(np.mean(w25_nom >= 3120.5)),
        "prob_early_stage2_trigger": float(np.mean(stage2_triggered)),
        "redline_breach_rates": {
            "any_year_single_gt_40pct": float(np.mean(breach_single40_m > 0)),
            "avg_years_single_gt_40pct": float(np.mean(breach_single40_m)),
            "any_year_tw_gt_50pct": float(np.mean(breach_tw50_m > 0)),
            "any_year_usd_lt_30pct": float(np.mean(breach_usd30_m > 0)),
        },
        "qqqm_y16_swap_gain_p50": float(np.median(qqqm_swap_gain_y16)),
        "qqqm_y16_swap_gain_p90": float(np.percentile(qqqm_swap_gain_y16, 90)),
        "retirement": {
            "ruin_prob": float(np.mean(ruined)),
            "ruin_prob_pct": float(np.mean(ruined) * 100.0),
            "y1_spend_real_p10": float(np.percentile(initial_d1_real, 10)),
            "y1_spend_real_p50": float(np.percentile(initial_d1_real, 50)),
            "y1_spend_real_p90": float(np.percentile(initial_d1_real, 90)),
            "y55_legacy_nom": pcts(ret_wealth_nom[:, 30]),
            "y55_legacy_real": pcts(ret_wealth_real[:, 30]),
            "prob_real_spend_cut_20pct": float(np.mean(severe_cut_20)),
            "prob_real_spend_cut_30pct": float(np.mean(severe_cut_30)),
            "avg_gk_freezes": float(np.mean(gk_freeze_count)),
            "avg_gk_cuts": float(np.mean(gk_cut_count)),
            "avg_gk_raises": float(np.mean(gk_raise_count)),
        },
        "acc_traj": acc_traj,
        "ret_traj": ret_traj,
    }


def main():
    n_sims = 10000
    scenarios = make_scenarios()
    all_results = []
    for cfg in scenarios:
        sim_data = generate_macro_asset_paths(cfg, n_sims=n_sims, n_months=660, seed=20261116)
        res = run_ips_lifecycle(cfg, sim_data)
        all_results.append(res)
        print(f"=== {cfg.name}: {cfg.label_zh} ===")
        print(
            f"  Y25 Nom P10/P50/P90: {res['y25_nominal']['p10']:.1f} / "
            f"{res['y25_nominal']['p50']:.1f} / {res['y25_nominal']['p90']:.1f} 萬 "
            f"(Prob >= 3120.5萬: {res['prob_reach_3120']*100:.1f}%)"
        )
        print(
            f"  Y25 Real P10/P50/P90: {res['y25_real']['p10']:.1f} / "
            f"{res['y25_real']['p50']:.1f} / {res['y25_real']['p90']:.1f} 萬 "
            f"(Y1 Real Spend P50: {res['retirement']['y1_spend_real_p50']:.1f} 萬/yr = {res['retirement']['y1_spend_real_p50']/12:.2f} 萬/mo)"
        )
        print(
            f"  Redlines breached (>=1 yr): Single>40%={res['redline_breach_rates']['any_year_single_gt_40pct']*100:.1f}%, "
            f"TW>50%={res['redline_breach_rates']['any_year_tw_gt_50pct']*100:.1f}%, "
            f"USD<30%={res['redline_breach_rates']['any_year_usd_lt_30pct']*100:.1f}%"
        )
        print(
            f"  Retire 30y Ruin: {res['retirement']['ruin_prob_pct']:.2f}% | "
            f"Real Spend Cut>=20%: {res['retirement']['prob_real_spend_cut_20pct']*100:.1f}% | "
            f"Legacy Real P50: {res['retirement']['y55_legacy_real']['p50']:.1f} 萬"
        )
        print()

    out_path = "/home/antigravity/Johntsai0320/long-term-investment/simulation_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Saved full simulation results to {out_path}")


if __name__ == "__main__":
    main()
