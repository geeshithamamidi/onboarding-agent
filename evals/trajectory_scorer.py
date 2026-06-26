"""
Trajectory Scorer — Evaluation-Driven Development (EDD)

From Day 3/5 concepts: trajectory scoring examines the SEQUENCE of tool calls,
not just the final output. Output-only scoring passes 20-50% more test cases
than trajectory scoring — but passes them for the wrong reasons.

This scorer:
  1. Loads eval cases from each skill's evals/cases.json
  2. Compares actual trajectory (from message_bus/trajectory.json) against expected
  3. Checks output schema compliance
  4. Enforces guardrails (no compensation leakage, no permission violations)
  5. Produces a Pass-to-K metric for sustained reliability
"""

import json
import math
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent.parent
MESSAGE_BUS = BASE_DIR / "message_bus"
SKILLS_DIR = BASE_DIR / ".agent-skills"


class TrajectoryScorer:

    def __init__(self):
        self.results: list[dict] = []

    def load_trajectory(self) -> list[dict]:
        path = MESSAGE_BUS / "trajectory.json"
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def load_eval_cases(self, skill: str) -> dict:
        path = SKILLS_DIR / skill / "evals" / "cases.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def load_skill_output(self, skill: str) -> dict:
        path = MESSAGE_BUS / f"{skill}_output.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def score_trajectory(self, actual: list[dict], expected_traj: list[dict]) -> dict:
        """
        Check that expected tool calls were made (or not made) in the correct order.
        This is what separates agentic engineering from vibe coding.
        """
        issues = []
        score = 1.0

        actual_tools = [t["tool"] for t in actual]

        for exp in expected_traj:
            tool = exp["tool"]
            must_be_called = exp.get("must_be_called", True)
            expected_order = exp.get("order")

            if must_be_called:
                if tool not in actual_tools:
                    issues.append(f"MISSING: {tool} was required but never called")
                    score -= 0.2
                elif isinstance(expected_order, int) and expected_order:
                    # Check ordering: tool at expected_order position (1-indexed)
                    # Allow some flexibility — just ensure relative order is maintained
                    pos = actual_tools.index(tool) + 1
                    if expected_order > 1:
                        # Ensure previous expected tool came before this one
                        prev_tools = [e["tool"] for e in expected_traj if e.get("order", 99) < expected_order and e.get("must_be_called", True)]
                        for prev in prev_tools:
                            if prev in actual_tools:
                                prev_pos = actual_tools.index(prev) + 1
                                if prev_pos > pos:
                                    issues.append(f"ORDER VIOLATION: {prev} must come before {tool}")
                                    score -= 0.15
            else:
                if tool in actual_tools:
                    reason = exp.get("reason", "should not have been called")
                    issues.append(f"FORBIDDEN CALL: {tool} was called but {reason}")
                    score -= 0.3

        return {
            "trajectory_score": max(0.0, score),
            "issues": issues,
            "passed": len(issues) == 0
        }

    def score_output(self, output: dict, expected_output: dict) -> dict:
        """Check output schema compliance and guardrail violations."""
        issues = []
        score = 1.0

        # Status check
        expected_status = expected_output.get("status")
        if expected_status and output.get("status") != expected_status:
            issues.append(f"STATUS MISMATCH: expected '{expected_status}', got '{output.get('status')}'")
            score -= 0.3

        # Required keys
        for key in expected_output.get("must_contain_keys", []):
            if key not in output:
                issues.append(f"MISSING KEY: '{key}' not in output")
                score -= 0.1

        # Forbidden content (guardrails — e.g., no compensation leakage)
        output_str = json.dumps(output).lower()
        for forbidden in expected_output.get("must_not_contain", []):
            if str(forbidden).lower() in output_str:
                issues.append(f"GUARDRAIL VIOLATION: forbidden value '{forbidden}' found in output")
                score -= 0.4

        # Expected error type
        expected_error = expected_output.get("error_must_be")
        if expected_error:
            actual_error = output.get("error", "")
            if expected_error not in str(actual_error):
                issues.append(f"WRONG ERROR: expected '{expected_error}', got '{actual_error}'")
                score -= 0.2

        # Document list checks
        for doc in expected_output.get("documents_sent_must_include", []):
            docs_sent = output.get("documents_sent", [])
            if doc not in docs_sent:
                issues.append(f"MISSING DOCUMENT: '{doc}' not in documents_sent")
                score -= 0.1

        for doc in expected_output.get("documents_sent_must_not_include", []):
            docs_sent = output.get("documents_sent", [])
            if doc in docs_sent:
                issues.append(f"WRONG DOCUMENT: '{doc}' should not be in documents_sent")
                score -= 0.2

        return {
            "output_score": max(0.0, score),
            "issues": issues,
            "passed": len(issues) == 0
        }

    def run_skill_eval(self, skill: str) -> dict:
        """Evaluate all cases for a skill against the actual run trajectory and output."""
        eval_data = self.load_eval_cases(skill)
        if not eval_data:
            return {"skill": skill, "error": "No eval cases found"}

        actual_trajectory = self.load_trajectory()
        skill_trajectory = [t for t in actual_trajectory if t["skill"] == skill]
        skill_output = self.load_skill_output(skill)

        results = []
        for case in eval_data.get("cases", []):
            # Skip negative/evil cases when evaluating happy-path trajectory —
            # these require separate runs with different inputs (invalid dept, contractor, etc.)
            if case.get("expected_output", {}).get("status") == "failed":
                print(f"\n  Skipping [{skill}] case '{case['name']}' — negative test, needs separate run")
                continue
            print(f"\n  Evaluating [{skill}] case: {case['name']}")

            traj_result = self.score_trajectory(
                skill_trajectory,
                case.get("expected_trajectory", [])
            )
            output_result = self.score_output(
                skill_output,
                case.get("expected_output", {})
            )

            combined_score = (traj_result["trajectory_score"] * 0.6 +
                            output_result["output_score"] * 0.4)
            passed = traj_result["passed"] and output_result["passed"]

            result = {
                "case_id": case["id"],
                "case_name": case["name"],
                "trajectory_score": round(traj_result["trajectory_score"], 2),
                "output_score": round(output_result["output_score"], 2),
                "combined_score": round(combined_score, 2),
                "passed": passed,
                "issues": traj_result["issues"] + output_result["issues"]
            }

            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"    {status} | Score: {combined_score:.2f}")
            if result["issues"]:
                for issue in result["issues"]:
                    print(f"      - {issue}")

            results.append(result)

        pass_count = sum(1 for r in results if r["passed"])
        avg_score = sum(r["combined_score"] for r in results) / len(results) if results else 0

        return {
            "skill": skill,
            "cases_run": len(results),
            "cases_passed": pass_count,
            "pass_rate": round(pass_count / len(results), 2) if results else 0,
            "average_score": round(avg_score, 2),
            "results": results
        }

    def pass_to_k(self, pass_rate: float, k: int = 5) -> float:
        """
        Pass-to-K metric: probability of k consecutive successful runs.
        p^k — exposes inconsistent skills before production.

        A skill with 60% pass rate has only 7.8% chance of passing 4 in a row.
        This is why we require sustained reliability, not just one passing run.
        """
        return round(pass_rate ** k, 4)

    def run_full_evaluation(self) -> dict:
        """Run evaluation across all 4 skills."""
        print(f"\n{'='*60}")
        print("  EVALUATION-DRIVEN DEVELOPMENT — TRAJECTORY SCORER")
        print(f"{'='*60}")

        skills = ["hr", "it", "training", "manager"]
        all_results = {}

        for skill in skills:
            all_results[skill] = self.run_skill_eval(skill)

        # Overall summary
        total_cases = sum(r.get("cases_run", 0) for r in all_results.values())
        total_passed = sum(r.get("cases_passed", 0) for r in all_results.values())
        overall_pass_rate = total_passed / total_cases if total_cases > 0 else 0
        p2k = self.pass_to_k(overall_pass_rate, k=5)

        summary = {
            "total_cases": total_cases,
            "total_passed": total_passed,
            "overall_pass_rate": round(overall_pass_rate, 2),
            "pass_to_k_5": p2k,
            "production_ready": p2k >= 0.5,
            "skill_results": all_results
        }

        print(f"\n{'='*60}")
        print(f"  SUMMARY")
        print(f"  Cases: {total_passed}/{total_cases} passed")
        print(f"  Pass rate: {overall_pass_rate:.0%}")
        print(f"  Pass-to-K (k=5): {p2k:.1%}")
        print(f"  Production ready: {'YES ✓' if summary['production_ready'] else 'NO ✗ — needs improvement'}")
        print(f"{'='*60}\n")

        # Save report
        report_path = BASE_DIR / "evals" / "eval_report.json"
        with open(report_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"  Report saved to evals/eval_report.json")

        return summary


if __name__ == "__main__":
    scorer = TrajectoryScorer()
    scorer.run_full_evaluation()
