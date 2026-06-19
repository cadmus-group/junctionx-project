"""NTL detection walkthrough (jupytext-style script; keeps logic in modules).

Run as a script (``python notebooks/ntl_walkthrough.py``) or open in Jupyter via
jupytext. Every step delegates to the importable modules so nothing of substance
lives in the notebook itself.
"""

# %%
from gridtrace_ml.datasets import customer_time_split
from gridtrace_ml.datasets.splits import load_dataset
from gridtrace_ml.evaluation import evaluate
from gridtrace_ml.explainability import explain_customer, global_importances
from gridtrace_ml.features import build_feature_frame
from gridtrace_ml.inference import predict_frame
from gridtrace_ml.training import train_models

SEED = 42

# %% [markdown]
# ## 1. Deterministic synthetic dataset (owned by the worker)
ds = load_dataset(SEED)
print("showcase:", ds.showcase)

# %% [markdown]
# ## 2. Leakage-safe split (disjoint customers + earlier train as_of)
split = customer_time_split(SEED)
split.assert_no_overlap()
split.assert_no_temporal_leakage()
print("train/test rows:", len(split.train), len(split.test))

# %% [markdown]
# ## 3. Train GBM classifier + IsolationForest
bundle = train_models(split.train, SEED)
print("algorithm:", bundle.algorithm)

# %% [markdown]
# ## 4. Evaluate with PR-AUC and precision@K (not accuracy)
scored = predict_frame(bundle, split.test)
report = evaluate(scored["label_is_ntl"].to_numpy(), scored["risk_score"].to_numpy())
print(report.to_dict())

# %% [markdown]
# ## 5. Explain the showcase customer
full = build_feature_frame(ds)
print("global importances:", global_importances(bundle, full))
print("explanations:", explain_customer(bundle, full, ds.showcase["customer_external_ref"]))
