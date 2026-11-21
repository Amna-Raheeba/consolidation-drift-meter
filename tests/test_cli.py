import json
import os

from consolidation_drift.cli import main


def test_cli_no_args_prints_help(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "consolidation" in out.lower()


def test_cli_demo(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "demo" in out.lower()
    assert "certainty_inflation" in out


def test_cli_audit(capsys):
    assert (
        main(["audit", "--policy", "anchor", "--facts", "20", "--cycles", "3"])
        == 0
    )
    out = capsys.readouterr().out
    assert "verbatim-anchor" in out


def test_cli_evaluate_writes_results(tmp_path):
    outdir = str(tmp_path / "results")
    assert (
        main(["evaluate", "--outdir", outdir, "--facts", "20", "--cycles", "3"])
        == 0
    )
    for name in (
        "evaluation.json",
        "evaluation.csv",
        "evaluation_summary.md",
        "HEADLINE.md",
    ):
        assert os.path.exists(os.path.join(outdir, name))
    with open(os.path.join(outdir, "evaluation.json")) as handle:
        evaluation = json.load(handle)
    assert "aggregates" in evaluation
