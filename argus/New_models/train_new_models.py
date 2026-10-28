from __future__ import annotations

import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_SAMPLES = 150_000
SEEDS = [42, 7, 2024]
LABEL_COL = "target_fraud"
TIME_SPAN_DAYS = 365.0
SPLIT_FRACS = (0.55, 0.15, 0.15, 0.15)
BANNER = "=" * 80

M1_FEATURE_COLS = [
    "customer_age",
    "income_lakhs",
    "account_type_risk",
    "velocity_1h",
    "velocity_24h",
]
GRAPH_COLS = [
    "shared_phone_degree",
    "shared_device_degree",
    "shared_both_degree",
    "linked_accounts",
    "component_size",
]
M2_FEATURE_COLS = M1_FEATURE_COLS + GRAPH_COLS
KYC_COLS = [
    "ocr_contradiction",
    "id_checksum_valid",
    "tampering_ela_score",
    "face_cosine_dist",
    "is_doc_missing",
    "is_selfie_missing",
]
M3_FEATURE_COLS = ["m1_prob", "m2_prob", "m0_rule_score"] + KYC_COLS + ["is_graph_isolated"]
M3_NO_KYC_COLS = ["m1_prob", "m2_prob", "m0_rule_score", "is_graph_isolated"]

LGB_PARAMS = dict(
    objective="binary",
    metric="average_precision",
    learning_rate=0.03,
    num_leaves=31,
    min_data_in_leaf=50,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=1,
    lambda_l2=1.0,
    verbose=-1,
)

SCENARIOS = [
    ("Clean Baseline", {}),
    ("10% Edge Deletion", {"edge": 0.10}),
    ("20% Edge Deletion", {"edge": 0.20}),
    ("30% Edge Deletion", {"edge": 0.30}),
    ("Ring Camouflage 50%", {"camo": 0.50}),
    ("Ring Camouflage 90%", {"camo": 0.90}),
    ("KYC Evasion 50%", {"kyc": 0.50}),
    ("Camo 90% + KYC Evasion 50%", {"camo": 0.90, "kyc": 0.50}),
]


def header(title: str) -> None:
    print(f"\n{'-' * 80}\n>>> {title}\n{'-' * 80}")


def rule_score(df: pd.DataFrame) -> np.ndarray:
    ela = df["tampering_ela_score"].fillna(0.2)
    face = df["face_cosine_dist"].fillna(0.18)
    s = (
        0.35 * df["ocr_contradiction"].astype(float)
        + 0.25 * (1.0 - df["id_checksum_valid"].astype(float))
        + 0.25 * (ela > 0.45).astype(float)
        + 0.20 * (face > 0.40).astype(float)
        + 0.10 * df["is_doc_missing"].astype(float)
        + 0.10 * df["is_selfie_missing"].astype(float)
        + 0.15 * (df["velocity_1h"] >= 3).astype(float)
    )
    return np.clip(s.to_numpy(dtype=float), 0.0, 1.0)


def component_sizes(phone_ids: np.ndarray, device_ids: np.ndarray) -> np.ndarray:
    pc, _ = pd.factorize(phone_ids)
    dc, _ = pd.factorize(device_ids)
    dc = dc + (int(pc.max()) + 1)
    pc = pc.tolist()
    dc = dc.tolist()
    total = max(dc) + 1
    parent = list(range(total))
    cnt = [0] * total
    out = np.zeros(len(pc), dtype=np.int64)
    for i in range(len(pc)):
        a = pc[i]
        b = dc[i]
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        while parent[b] != b:
            parent[b] = parent[parent[b]]
            b = parent[b]
        if a != b:
            parent[b] = a
            cnt[a] += cnt[b]
        out[i] = cnt[a]
        cnt[a] += 1
    return out


def build_graph_features(phone_id: np.ndarray, device_id: np.ndarray) -> pd.DataFrame:
    p = pd.Series(phone_id)
    d = pd.Series(device_id)
    phone_deg = p.groupby(p).cumcount().to_numpy()
    device_deg = d.groupby(d).cumcount().to_numpy()
    both = pd.DataFrame({"p": phone_id, "d": device_id}).groupby(["p", "d"]).cumcount().to_numpy()
    return pd.DataFrame(
        {
            "shared_phone_degree": phone_deg,
            "shared_device_degree": device_deg,
            "shared_both_degree": both,
            "linked_accounts": phone_deg + device_deg - both,
            "component_size": component_sizes(phone_id, device_id),
        }
    )


def generate_dataset(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    t = rng.uniform(0, TIME_SPAN_DAYS, n)
    p_fraud = 0.015 + 0.010 * (t / TIME_SPAN_DAYS)
    is_fraud = rng.random(n) < p_fraud

    ftype = np.zeros(n, dtype=int)
    fidx = np.flatnonzero(is_fraud)
    ftype[fidx] = rng.choice([1, 2, 3], size=len(fidx), p=[0.45, 0.35, 0.20])

    ring_rows = np.flatnonzero(ftype == 1)
    n_rings = max(1, len(ring_rows) // 6)
    ring_of = rng.integers(0, n_rings, len(ring_rows))
    ring_start = rng.uniform(0, TIME_SPAN_DAYS, n_rings)
    t[ring_rows] = np.clip(
        ring_start[ring_of] + rng.exponential(12.0, len(ring_rows)), 0, TIME_SPAN_DAYS
    )

    phone_id = np.arange(n, dtype=np.int64)
    device_id = np.arange(n, dtype=np.int64)

    legit_idx = np.flatnonzero(ftype == 0)
    hh = legit_idx[rng.random(len(legit_idx)) < 0.07]
    hh_id = rng.integers(0, max(1, len(hh) // 3), len(hh))
    share_p = rng.random(len(hh)) < 0.70
    share_d = rng.random(len(hh)) < 0.50
    phone_id[hh[share_p]] = n + hh_id[share_p]
    device_id[hh[share_d]] = n + hh_id[share_d]

    cafe = legit_idx[rng.random(len(legit_idx)) < 0.015]
    device_id[cafe] = 5 * n + rng.integers(0, 30, len(cafe))

    use_rp = rng.random(len(ring_rows)) < 0.75
    use_rd = rng.random(len(ring_rows)) < 0.75
    phone_id[ring_rows[use_rp]] = 2 * n + 2 * ring_of[use_rp] + rng.integers(0, 2, int(use_rp.sum()))
    device_id[ring_rows[use_rd]] = 2 * n + 3 * ring_of[use_rd] + rng.integers(0, 3, int(use_rd.sum()))

    syn = np.flatnonzero(ftype == 2)
    farm = syn[rng.random(len(syn)) < 0.30]
    device_id[farm] = 4 * n + rng.integers(0, 200, len(farm))

    age = np.clip(
        rng.normal(np.array([38.0, 33.0, 32.0, 38.0])[ftype], np.array([12.0, 10.0, 10.0, 12.0])[ftype]),
        18,
        80,
    ).round()
    income = np.exp(
        rng.normal(
            np.log(np.array([6.0, 5.5, 8.0, 6.0])[ftype]),
            np.array([0.7, 0.9, 0.8, 0.7])[ftype],
        )
    ).round(2)

    risk_levels = np.array([0.1, 0.3, 0.6, 0.9])
    risk_p = np.array(
        [
            [0.45, 0.30, 0.18, 0.07],
            [0.25, 0.30, 0.25, 0.20],
            [0.25, 0.30, 0.25, 0.20],
            [0.45, 0.30, 0.18, 0.07],
        ]
    )
    cum = risk_p.cumsum(axis=1)[ftype]
    risk_idx = np.minimum((rng.random(n)[:, None] > cum).sum(axis=1), 3)
    account_type_risk = risk_levels[risk_idx]

    v1 = rng.poisson(np.array([0.6, 1.1, 1.0, 0.6])[ftype])
    v24 = v1 + rng.poisson(np.array([2.0, 3.0, 2.8, 2.0])[ftype])

    ocr = (rng.random(n) < np.array([0.05, 0.15, 0.30, 0.06])[ftype]).astype(int)
    checksum = (rng.random(n) < np.array([0.985, 0.93, 0.85, 0.985])[ftype]).astype(int)
    ela = rng.beta(np.array([2.0, 3.0, 4.0, 2.0])[ftype], np.array([8.0, 7.0, 5.0, 8.0])[ftype])
    face = rng.beta(np.array([2.0, 3.0, 4.0, 2.0])[ftype], np.array([9.0, 8.0, 7.0, 9.0])[ftype])
    doc_missing = (rng.random(n) < np.where(ftype > 0, 0.06, 0.03)).astype(int)
    selfie_missing = (rng.random(n) < np.where(ftype > 0, 0.07, 0.04)).astype(int)
    ela = np.where(doc_missing == 1, np.nan, ela)
    face = np.where(selfie_missing == 1, np.nan, face)

    label = (ftype > 0).astype(int)
    flip_legit = (ftype == 0) & (rng.random(n) < 0.002)
    miss_fraud = (ftype > 0) & (rng.random(n) < 0.03)
    label = np.where(flip_legit, 1, np.where(miss_fraud, 0, label))

    df = pd.DataFrame(
        {
            "timestamp_days": t,
            "customer_age": age,
            "income_lakhs": income,
            "account_type_risk": account_type_risk,
            "velocity_1h": v1,
            "velocity_24h": v24,
            "ocr_contradiction": ocr,
            "id_checksum_valid": checksum,
            "tampering_ela_score": ela,
            "face_cosine_dist": face,
            "is_doc_missing": doc_missing,
            "is_selfie_missing": selfie_missing,
            "phone_id": phone_id,
            "device_id": device_id,
            "fraud_type": ftype,
            LABEL_COL: label,
        }
    )
    df = df.sort_values("timestamp_days", kind="stable").reset_index(drop=True)
    df.insert(0, "customer_id", np.arange(len(df)))
    gf = build_graph_features(df["phone_id"].to_numpy(), df["device_id"].to_numpy())
    df = pd.concat([df, gf], axis=1)
    df["m0_rule_score"] = rule_score(df)
    return df


def temporal_split(df: pd.DataFrame):
    n = len(df)
    b = np.cumsum([int(n * f) for f in SPLIT_FRACS[:-1]])
    return df.iloc[: b[0]], df.iloc[b[0] : b[1]], df.iloc[b[1] : b[2]], df.iloc[b[2] :]


def fit_booster(Xtr, ytr, Xva, yva, seed: int) -> lgb.Booster:
    dtr = lgb.Dataset(Xtr, label=ytr)
    dva = lgb.Dataset(Xva, label=yva, reference=dtr)
    return lgb.train(
        {**LGB_PARAMS, "seed": seed},
        dtr,
        num_boost_round=3000,
        valid_sets=[dva],
        callbacks=[lgb.early_stopping(100, verbose=False)],
    )


def oof_predict(X: pd.DataFrame, y: np.ndarray, rounds: int, seed: int, n_splits: int = 5) -> np.ndarray:
    oof = np.zeros(len(X))
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    for tr_idx, te_idx in skf.split(X, y):
        booster = lgb.train(
            {**LGB_PARAMS, "seed": seed},
            lgb.Dataset(X.iloc[tr_idx], label=y[tr_idx]),
            num_boost_round=rounds,
        )
        oof[te_idx] = booster.predict(X.iloc[te_idx])
    return oof


def fusion_frame(df: pd.DataFrame, p1: np.ndarray, p2: np.ndarray) -> pd.DataFrame:
    data = {
        "m1_prob": p1,
        "m2_prob": p2,
        "m0_rule_score": df["m0_rule_score"].to_numpy(),
    }
    for c in KYC_COLS:
        data[c] = df[c].to_numpy()
    data["is_graph_isolated"] = (df["linked_accounts"].to_numpy() == 0).astype(int)
    return pd.DataFrame(data)


def fit_fusion(Ftr, ytr, Fva, yva, Fcal, ycal, cols, seed):
    booster = fit_booster(Ftr[cols], ytr, Fva[cols], yva, seed)
    iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    iso.fit(booster.predict(Fcal[cols]), ycal)
    return booster, iso


def fusion_scores(booster, iso, F, cols):
    raw = booster.predict(F[cols])
    return raw, iso.predict(raw)


def ranking_metrics(y: np.ndarray, s: np.ndarray) -> dict:
    fpr, tpr, _ = roc_curve(y, s)
    return {
        "pr_auc": float(average_precision_score(y, s)),
        "roc_auc": float(roc_auc_score(y, s)),
        "recall_at_5pct_fpr": float(tpr[fpr <= 0.05].max()),
        "recall_at_1pct_fpr": float(tpr[fpr <= 0.01].max()),
    }


def ece_score(y: np.ndarray, p: np.ndarray, bins: int = 20) -> float:
    order = np.argsort(p, kind="stable")
    chunks = np.array_split(order, bins)
    return float(sum(len(c) / len(y) * abs(y[c].mean() - p[c].mean()) for c in chunks if len(c)))


def bootstrap_pr(y: np.ndarray, s: np.ndarray, n_boot: int = 200, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y))
        if y[i].sum() == 0:
            continue
        vals.append(average_precision_score(y[i], s[i]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def pick_thresholds(y: np.ndarray, p: np.ndarray, approve_recall: float = 0.95, reject_precision: float = 0.90):
    prec, rec, thr = precision_recall_curve(y, p)
    prec, rec = prec[:-1], rec[:-1]
    ok = thr[rec >= approve_recall]
    approve = float(ok.max()) if len(ok) else float(thr.min())
    ok = thr[prec >= reject_precision]
    reject = float(ok.min()) if len(ok) else float(thr.max())
    return approve, max(reject, approve)


def confusion_at(y: np.ndarray, p: np.ndarray, thresh: float) -> dict:
    pred = (p >= thresh).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    return {
        "threshold": round(float(thresh), 4),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "fpr": round(float(fp / max(fp + tn, 1)), 4),
        "f1": round(float(2 * prec * rec / max(prec + rec, 1e-9)), 4),
    }


def single_feature_auc(df: pd.DataFrame, cols: list[str], y: np.ndarray) -> list[tuple[str, float]]:
    rows = []
    for c in cols:
        x = df[c].astype(float)
        x = x.fillna(x.median())
        a = roc_auc_score(y, x)
        rows.append((c, round(float(max(a, 1 - a)), 4)))
    return sorted(rows, key=lambda r: -r[1])


def apply_attack(df: pd.DataFrame, test_start: int, cfg: dict, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    d = df.copy()
    n_all = len(d)
    test_pos = np.arange(test_start, n_all)
    y = d[LABEL_COL].to_numpy()
    phone = d["phone_id"].to_numpy().copy()
    device = d["device_id"].to_numpy().copy()

    q = cfg.get("edge", 0.0)
    if q > 0:
        mp = test_pos[rng.random(len(test_pos)) < q]
        md = test_pos[rng.random(len(test_pos)) < q]
        phone[mp] = 10 * n_all + mp
        device[md] = 10 * n_all + md

    q = cfg.get("camo", 0.0)
    if q > 0:
        fm = test_pos[(y[test_pos] == 1) & (rng.random(len(test_pos)) < q)]
        phone[fm] = 10 * n_all + fm
        device[fm] = 10 * n_all + fm

    d["phone_id"] = phone
    d["device_id"] = device

    q = cfg.get("kyc", 0.0)
    if q > 0:
        fm = test_pos[(y[test_pos] == 1) & (rng.random(len(test_pos)) < q)]
        pool = test_pos[y[test_pos] == 0]
        src = rng.choice(pool, len(fm))
        for c in KYC_COLS:
            col = d[c].to_numpy().copy()
            col[fm] = col[src]
            d[c] = col
        d["m0_rule_score"] = rule_score(d)

    gf = build_graph_features(d["phone_id"].to_numpy(), d["device_id"].to_numpy())
    for c in GRAPH_COLS:
        d[c] = gf[c].to_numpy()
    return d.iloc[test_start:]


def score_all(df: pd.DataFrame, models: dict) -> dict:
    p1 = models["m1"].predict(df[M1_FEATURE_COLS])
    p2 = models["m2"].predict(df[M2_FEATURE_COLS])
    F = fusion_frame(df, p1, p2)
    raw3, _ = fusion_scores(models["m3"], models["iso3"], F, M3_FEATURE_COLS)
    return {
        "M0 (Rules)": df["m0_rule_score"].to_numpy(),
        "M1 (Tabular)": p1,
        "M2 (Graph)": p2,
        "M3 (ARGUS)": raw3,
    }


def run_seed(seed: int) -> dict:
    df = generate_dataset(N_SAMPLES, seed)
    tr, va, cal, te = temporal_split(df)
    half = len(cal) // 2
    cal_a, cal_b = cal.iloc[:half], cal.iloc[half:]

    assert tr["timestamp_days"].max() <= va["timestamp_days"].min()
    assert va["timestamp_days"].max() <= cal["timestamp_days"].min()
    assert cal["timestamp_days"].max() <= te["timestamp_days"].min()
    assert df["customer_id"].is_unique

    ytr = tr[LABEL_COL].to_numpy()
    yva = va[LABEL_COL].to_numpy()
    yca = cal_a[LABEL_COL].to_numpy()
    ycb = cal_b[LABEL_COL].to_numpy()
    yte = te[LABEL_COL].to_numpy()

    b1 = fit_booster(tr[M1_FEATURE_COLS], ytr, va[M1_FEATURE_COLS], yva, seed)
    r1 = max(b1.best_iteration, 50)
    oof1 = oof_predict(tr[M1_FEATURE_COLS], ytr, r1, seed)

    b2 = fit_booster(tr[M2_FEATURE_COLS], ytr, va[M2_FEATURE_COLS], yva, seed)
    r2 = max(b2.best_iteration, 50)
    oof2 = oof_predict(tr[M2_FEATURE_COLS], ytr, r2, seed)

    def base_preds(frame):
        return b1.predict(frame[M1_FEATURE_COLS]), b2.predict(frame[M2_FEATURE_COLS])

    Ftr = fusion_frame(tr, oof1, oof2)
    Fva = fusion_frame(va, *base_preds(va))
    Fca = fusion_frame(cal_a, *base_preds(cal_a))
    Fcb = fusion_frame(cal_b, *base_preds(cal_b))
    p1_te, p2_te = base_preds(te)
    Fte = fusion_frame(te, p1_te, p2_te)

    b3, iso3 = fit_fusion(Ftr, ytr, Fva, yva, Fca, yca, M3_FEATURE_COLS, seed)
    b3n, iso3n = fit_fusion(Ftr, ytr, Fva, yva, Fca, yca, M3_NO_KYC_COLS, seed)

    raw3, cal3 = fusion_scores(b3, iso3, Fte, M3_FEATURE_COLS)
    raw3n, cal3n = fusion_scores(b3n, iso3n, Fte, M3_NO_KYC_COLS)
    _, cal3_b = fusion_scores(b3, iso3, Fcb, M3_FEATURE_COLS)
    approve, reject = pick_thresholds(ycb, cal3_b)

    m0_te = te["m0_rule_score"].to_numpy()
    scores = {"m0": m0_te, "m1": p1_te, "m2": p2_te, "m3": raw3, "m3_nokyc": raw3n}
    calibrated = {"m1": p1_te, "m2": p2_te, "m3": cal3, "m3_nokyc": cal3n}

    metrics = {}
    ci = {}
    for k, s in scores.items():
        metrics[k] = ranking_metrics(yte, s)
        ci[k] = bootstrap_pr(yte, s, seed=seed)
        if k in calibrated:
            metrics[k]["brier"] = float(brier_score_loss(yte, calibrated[k]))
            metrics[k]["ece"] = ece_score(yte, calibrated[k])

    prevalence = float(yte.mean())
    masks = {
        "APPROVE": cal3 < approve,
        "FLAG_REVIEW": (cal3 >= approve) & (cal3 < reject),
        "REJECT": cal3 >= reject,
    }
    tiers = {}
    for name, m in masks.items():
        cnt = int(m.sum())
        tiers[name] = {
            "count": cnt,
            "pct": round(cnt / len(yte) * 100, 2),
            "fraud_rate_pct": round(float(yte[m].mean() * 100), 2) if cnt else 0.0,
            "fraud_n": int(yte[m].sum()),
        }
    total_fraud = int(yte.sum())
    leakage = tiers["APPROVE"]["fraud_n"] / max(total_fraud, 1)

    sweep = [confusion_at(yte, cal3, t) for t in np.arange(0.05, 0.96, 0.05)]
    conf = {
        "review_gate": confusion_at(yte, cal3, approve),
        "reject_gate": confusion_at(yte, cal3, reject),
    }

    feat_cols = M2_FEATURE_COLS + KYC_COLS + ["m0_rule_score"]
    single_auc = single_feature_auc(te, feat_cols, yte)

    rng = np.random.default_rng(seed + 1)
    perm_tr = rng.permutation(ytr)
    perm_va = rng.permutation(yva)
    bs = fit_booster(tr[M2_FEATURE_COLS], perm_tr, va[M2_FEATURE_COLS], perm_va, seed)
    shuffled_auc = float(roc_auc_score(yte, bs.predict(te[M2_FEATURE_COLS])))

    imp = {}
    for name, booster, cols in [("m2", b2, M2_FEATURE_COLS), ("m3", b3, M3_FEATURE_COLS)]:
        gain = booster.feature_importance(importance_type="gain")
        total = gain.sum() if gain.sum() > 0 else 1.0
        imp[name] = sorted(
            [(c, round(float(g / total), 4)) for c, g in zip(cols, gain)], key=lambda r: -r[1]
        )

    models = {"m1": b1, "m2": b2, "m3": b3, "iso3": iso3}
    test_start = len(df) - len(te)
    attack = []
    for i, (name, cfg) in enumerate(SCENARIOS):
        d_att = apply_attack(df, test_start, cfg, seed * 100 + i)
        sc = score_all(d_att, models)
        row = {"Scenario": name}
        for k, s in sc.items():
            row[k] = round(float(average_precision_score(yte, s)), 4)
        attack.append(row)

    return {
        "seed": seed,
        "df": df,
        "n": len(df),
        "prevalence_all_pct": round(float(df[LABEL_COL].mean() * 100), 2),
        "prevalence_test": prevalence,
        "split": {"train": len(tr), "val": len(va), "cal": len(cal), "test": len(te)},
        "fraud_counts": {
            "train": int(ytr.sum()),
            "val": int(yva.sum()),
            "cal": int(yca.sum() + ycb.sum()),
            "test": total_fraud,
        },
        "metrics": metrics,
        "ci": ci,
        "lifts": {
            "graph_over_tabular": metrics["m2"]["pr_auc"] - metrics["m1"]["pr_auc"],
            "fusion_over_graph": metrics["m3"]["pr_auc"] - metrics["m2"]["pr_auc"],
            "total_over_tabular": metrics["m3"]["pr_auc"] - metrics["m1"]["pr_auc"],
            "kyc_contribution": metrics["m3"]["pr_auc"] - metrics["m3_nokyc"]["pr_auc"],
        },
        "thresholds": {"approve": approve, "reject": reject},
        "tiers": tiers,
        "leakage": leakage,
        "confusion": conf,
        "sweep": sweep,
        "single_auc": single_auc,
        "shuffled_auc": shuffled_auc,
        "importance": imp,
        "attack": attack,
        "models": {"m1": b1, "m2": b2, "m3": b3, "iso3": iso3, "m3_nokyc": b3n, "iso3n": iso3n},
        "rounds": {"m1": r1, "m2": r2},
        "test_start": test_start,
    }


def check(label: str, ok: bool, detail: str) -> None:
    print(f"    [{'v' if ok else 'x'}] {'PASS' if ok else 'FAIL'}  {label:<52} {detail}")


def save_payload(stem: str, payload: dict) -> None:
    jp = OUTPUT_DIR / f"{stem}.joblib"
    joblib.dump(payload, jp)
    print(f"  [OK] {jp.name:<26} ({jp.stat().st_size / 1024:.1f} KB)")
    try:
        import torch

        pp = OUTPUT_DIR / f"{stem}.pt"
        torch.save(payload, pp)
        print(f"  [OK] {pp.name:<26} ({pp.stat().st_size / 1024:.1f} KB)  load with weights_only=False")
    except Exception:
        pass


def main() -> None:
    t0 = time.time()
    print(BANNER)
    print("  PROJECT ARGUS -- Indian e-KYC Benchmark (leak-free, multi-seed)")
    print(f"  Samples per seed: {N_SAMPLES:,}  |  Seeds: {SEEDS}")
    print(f"  Output: {OUTPUT_DIR}")
    print(BANNER)

    results = []
    for s in SEEDS:
        print(f"  running seed {s} ...", flush=True)
        results.append(run_seed(s))
    P = results[0]

    header(f"[Phase 0] Dataset (seed {P['seed']})")
    print(f"  Rows             : {P['n']:,}")
    print(f"  Fraud prevalence : {P['prevalence_all_pct']:.2f}%")
    print(f"  Split            : {P['split']}")
    print(f"  Fraud per split  : {P['fraud_counts']}")
    print(f"  Rounds (M1/M2)   : {P['rounds']}")

    header("[Phase 1] Leakage Diagnostics")
    print("  Single-feature test AUC (top 8):")
    for c, a in P["single_auc"][:8]:
        print(f"    {c:<24} {a:.4f}")
    print(f"\n  Shuffled-label AUC (should be ~0.5): {P['shuffled_auc']:.4f}")

    header("[Phase 2] Model Comparison (seed %d, test set)" % P["seed"])
    names = [("m0", "M0 Rules"), ("m1", "M1 Tabular"), ("m2", "M2 Graph"), ("m3_nokyc", "M3 no raw KYC"), ("m3", "M3 Fusion")]
    rows = []
    for k, label in names:
        m = P["metrics"][k]
        lo, hi = P["ci"][k]
        rows.append(
            {
                "Model": label,
                "PR-AUC": round(m["pr_auc"], 4),
                "PR-AUC 95% CI": f"[{lo:.3f}, {hi:.3f}]",
                "ROC-AUC": round(m["roc_auc"], 4),
                "Rec@5%FPR": round(m["recall_at_5pct_fpr"], 4),
                "Rec@1%FPR": round(m["recall_at_1pct_fpr"], 4),
                "Brier": round(m["brier"], 4) if "brier" in m else "",
                "ECE": round(m["ece"], 4) if "ece" in m else "",
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  Baseline Brier (constant prevalence): {P['prevalence_test'] * (1 - P['prevalence_test']):.4f}")
    for k, v in P["lifts"].items():
        print(f"  {k:<22} {v:+.4f}")

    header("[Phase 3] Multi-Seed Stability (mean +/- std)")
    agg = []
    for k, label in names:
        pr = np.array([r["metrics"][k]["pr_auc"] for r in results])
        roc = np.array([r["metrics"][k]["roc_auc"] for r in results])
        r5 = np.array([r["metrics"][k]["recall_at_5pct_fpr"] for r in results])
        agg.append(
            {
                "Model": label,
                "PR-AUC": f"{pr.mean():.4f} +/- {pr.std():.4f}",
                "ROC-AUC": f"{roc.mean():.4f} +/- {roc.std():.4f}",
                "Rec@5%FPR": f"{r5.mean():.4f} +/- {r5.std():.4f}",
            }
        )
    print(pd.DataFrame(agg).to_string(index=False))
    lift_rows = {}
    for key in ["graph_over_tabular", "fusion_over_graph", "total_over_tabular", "kyc_contribution"]:
        arr = np.array([r["lifts"][key] for r in results])
        lift_rows[key] = (float(arr.mean()), float(arr.std()))
        print(f"  {key:<22} {arr.mean():+.4f} +/- {arr.std():.4f}")

    header("[Phase 4] Feature Importance (gain share, seed %d)" % P["seed"])
    for name in ["m2", "m3"]:
        print(f"  {name.upper()}:")
        for c, g in P["importance"][name][:8]:
            print(f"    {c:<24} {g:.4f}")

    header("[Phase 5] Tuned Thresholds and Risk Tiers (M3 calibrated, test set)")
    print(f"  Approve below {P['thresholds']['approve']:.4f}  |  Reject at or above {P['thresholds']['reject']:.4f}")
    print("  (chosen on held-out calibration half B: recall>=0.95 for approve, precision>=0.90 for reject)")
    trows = [{"Tier": k, **v} for k, v in P["tiers"].items()]
    print(pd.DataFrame(trows).to_string(index=False))
    tf = P["fraud_counts"]["test"]
    print(f"\n  Auto-approved fraud leakage: {P['leakage'] * 100:.1f}% of {tf} fraud cases")

    header("[Phase 6] Confusion Matrices at Tuned Thresholds")
    for k, v in P["confusion"].items():
        print(f"  {k}: {v}")

    header("[Phase 7] M3 Threshold Sweep")
    print(pd.DataFrame(P["sweep"]).to_string(index=False))

    header("[Phase 8] Adversarial Robustness -- PR-AUC (mean over seeds, graph rebuilt after attack)")
    atk = pd.concat([pd.DataFrame(r["attack"]) for r in results]).groupby("Scenario", sort=False).mean().reset_index()
    print(atk.round(4).to_string(index=False))
    clean = atk.iloc[0]
    print("\n  PR-AUC change vs clean baseline:")
    for _, r in atk.iloc[1:].iterrows():
        print(
            f"    {r['Scenario']:<30} M0 {r['M0 (Rules)'] - clean['M0 (Rules)']:+.4f}"
            f"  M1 {r['M1 (Tabular)'] - clean['M1 (Tabular)']:+.4f}"
            f"  M2 {r['M2 (Graph)'] - clean['M2 (Graph)']:+.4f}"
            f"  M3 {r['M3 (ARGUS)'] - clean['M3 (ARGUS)']:+.4f}"
        )

    header("[Phase 9] Sanity and Compliance Checks")
    max_auc = P["single_auc"][0][1]
    check("No single feature has test AUC >= 0.90", max_auc < 0.90, f"max={max_auc:.4f} ({P['single_auc'][0][0]})")
    check("Shuffled-label AUC within 0.5 +/- 0.03", abs(P["shuffled_auc"] - 0.5) < 0.03, f"actual={P['shuffled_auc']:.4f}")
    base_brier = P["prevalence_test"] * (1 - P["prevalence_test"])
    check("M3 Brier below constant-prevalence baseline", P["metrics"]["m3"]["brier"] < base_brier, f"{P['metrics']['m3']['brier']:.4f} < {base_brier:.4f}")
    check("M3 ECE <= 0.010", P["metrics"]["m3"]["ece"] <= 0.010, f"actual={P['metrics']['m3']['ece']:.4f}")
    check("Mean graph lift (M2-M1) > 0 across seeds", lift_rows["graph_over_tabular"][0] > 0, f"{lift_rows['graph_over_tabular'][0]:+.4f}")
    check("Mean fusion lift (M3-M2) > 0 across seeds", lift_rows["fusion_over_graph"][0] > 0, f"{lift_rows['fusion_over_graph'][0]:+.4f}")
    check("Auto-approve fraud leakage <= 8%", P["leakage"] <= 0.08, f"actual={P['leakage'] * 100:.1f}%")
    check("Temporal split ordered, customer ids unique", True, "asserted in every seed")

    header("[Phase 10] Serializing Models, Dataset and Report")
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    mdl = P["models"]
    save_payload(
        "m1_tabular",
        {"name": "m1_tabular", "model": mdl["m1"], "features": M1_FEATURE_COLS, "metrics": P["metrics"]["m1"], "timestamp": ts},
    )
    save_payload(
        "m2_graph",
        {"name": "m2_graph", "model": mdl["m2"], "features": M2_FEATURE_COLS, "metrics": P["metrics"]["m2"], "timestamp": ts},
    )
    save_payload(
        "m3_fusion",
        {
            "name": "m3_fusion",
            "model": mdl["m3"],
            "calibrator": mdl["iso3"],
            "features": M3_FEATURE_COLS,
            "thresholds": P["thresholds"],
            "calibration": "isotonic (held-out temporal calibration set)",
            "metrics": P["metrics"]["m3"],
            "timestamp": ts,
        },
    )

    full = P["df"].copy()
    split_col = np.empty(len(full), dtype=object)
    b = np.cumsum([int(len(full) * f) for f in SPLIT_FRACS[:-1]])
    split_col[: b[0]] = "train"
    split_col[b[0] : b[1]] = "val"
    split_col[b[1] : b[2]] = "calibration"
    split_col[b[2] :] = "test"
    full["split"] = split_col
    dp = OUTPUT_DIR / "synthetic_kyc_dataset.csv.gz"
    full.to_csv(dp, index=False, compression="gzip")
    print(f"  [OK] {dp.name:<26} ({dp.stat().st_size / 1024:.1f} KB, {len(full):,} rows)")

    report = {
        "generated_at": ts,
        "config": {"n_samples": N_SAMPLES, "seeds": SEEDS, "split_fracs": SPLIT_FRACS, "lgb_params": LGB_PARAMS},
        "primary_seed": P["seed"],
        "prevalence_pct": P["prevalence_all_pct"],
        "split": P["split"],
        "fraud_counts": P["fraud_counts"],
        "metrics_primary": P["metrics"],
        "pr_auc_ci_primary": {k: list(v) for k, v in P["ci"].items()},
        "per_seed": [
            {"seed": r["seed"], "metrics": r["metrics"], "lifts": r["lifts"], "leakage": r["leakage"]}
            for r in results
        ],
        "lift_mean_std": {k: list(v) for k, v in lift_rows.items()},
        "thresholds": P["thresholds"],
        "risk_tiers": P["tiers"],
        "confusion": P["confusion"],
        "threshold_sweep_m3": P["sweep"],
        "adversarial_matrix_mean": atk.to_dict(orient="records"),
        "single_feature_auc": P["single_auc"],
        "shuffled_label_auc": P["shuffled_auc"],
        "feature_importance": P["importance"],
        "feature_names": {"m1": M1_FEATURE_COLS, "m2": M2_FEATURE_COLS, "m3": M3_FEATURE_COLS},
    }
    rp = OUTPUT_DIR / "benchmark_report.json"
    with open(rp, "w") as f:
        json.dump(report, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(f"  [OK] {rp.name}")

    print(f"\n{BANNER}")
    print(f"  COMPLETE -- {time.time() - t0:.1f}s  |  Output: {OUTPUT_DIR}")
    print(BANNER)


if __name__ == "__main__":
    main()