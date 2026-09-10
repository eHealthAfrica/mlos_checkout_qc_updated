"""Verdict, score and issue-row computation, relocated report/email builders.

This module is the Streamlit-free relocation target for the pure verdict/score/count logic that
today sits inline in ``app.py`` (F1/F6/F8's root cause: four independent presentation sites each
deriving their own answer), and — in later plans of this phase — for the report workbook and
email body/subject builders. One computation, built once from the five QC layers' checks and
detail frames, is read by every on-screen site, the downloaded report and the emailed summary.

Deliberately NOT imported by ``qc/__init__.py``: the facade (``qc/__init__.py``) imports every
layer submodule before defining ``sort_by_registry``, so a package-init edge from this module
back to the facade would be a cycle. ``app.py`` reaches this module the way it already reaches
``qc.columns`` — an explicit ``import qc.report``.
"""
