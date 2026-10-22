"""v1.6.0 Feature H slice 4 (instruction 016) — Guard 3 multi-persona merge.

Covers §8b Verification 7: union of grounded moves; conflict SURFACED not
resolved (per shape); exactly ONE terminal renumber (reusing the instr-007
renumber) yielding sequential IDs; defer excluded; provenance preserved.
"""

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = (
    REPO_ROOT / "plugins" / "quality-playbook" / "skills" / "quality-playbook" / "scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

import persona_merge as pm  # noqa: E402
import requirements_render  # noqa: E402


def _base():
    return {"records": [
        {"id": "REQ-001", "functional_section": "Routing", "title": "A",
         "conditions_of_satisfaction": "a"},
        {"id": "REQ-002", "functional_section": "Routing", "title": "B",
         "conditions_of_satisfaction": "b"},
        {"id": "REQ-003", "functional_section": "Errors", "title": "C",
         "conditions_of_satisfaction": "c"},
    ]}


def _cit():
    return {"document": "reference_docs/spec.txt", "citation_excerpt": "x"}


class UnionTests(unittest.TestCase):
    def test_non_overlapping_grounded_moves_all_land(self):
        grounded = [
            {"persona_id": "domain-expert", "moves": [
                {"move": "add", "section": "Routing", "title": "regexp params",
                 "conditions_of_satisfaction": "params support {name:pattern}",
                 "citation": _cit()}]},
            {"persona_id": "security-reviewer", "moves": [
                {"move": "add", "section": "Errors", "title": "no stack leak",
                 "conditions_of_satisfaction": "errors do not leak traces",
                 "citation": _cit()}]},
        ]
        r = pm.merge_personas(grounded, _base())
        titles = [rec["title"] for rec in r.manifest["records"]]
        self.assertIn("regexp params", titles)
        self.assertIn("no stack leak", titles)
        self.assertEqual(r.conflicts, [])
        self.assertEqual(len(r.applied), 2)

    def test_two_identical_corrects_are_agreement_applied_once(self):
        grounded = [
            {"persona_id": "a", "moves": [
                {"move": "correct", "req_id": "REQ-001",
                 "conditions_of_satisfaction": "same fix", "citation": _cit()}]},
            {"persona_id": "b", "moves": [
                {"move": "correct", "req_id": "REQ-001",
                 "conditions_of_satisfaction": "same fix", "citation": _cit()}]},
        ]
        r = pm.merge_personas(grounded, _base())
        self.assertEqual(r.conflicts, [])
        self.assertEqual(len(r.applied), 1)  # agreement -> applied once

    def test_two_identical_adds_from_blind_personas_apply_once(self):
        # self-Council Panelist C: two blind personas independently proposing the
        # SAME missing requirement is agreement — ONE record, not a duplicate.
        add = {"move": "add", "section": "Routing", "title": "regexp params",
               "conditions_of_satisfaction": "params support {name:pattern}",
               "citation": _cit()}
        grounded = [
            {"persona_id": "domain-expert", "moves": [dict(add)]},
            {"persona_id": "security-reviewer", "moves": [dict(add)]},
        ]
        r = pm.merge_personas(grounded, _base())
        titles = [rec.get("title") for rec in r.manifest["records"]]
        self.assertEqual(titles.count("regexp params"), 1, "identical add double-applied")
        self.assertEqual(r.conflicts, [])
        self.assertEqual(len(r.applied), 1)

    def test_different_adds_to_same_section_both_land(self):
        grounded = [
            {"persona_id": "a", "moves": [
                {"move": "add", "section": "Routing", "title": "one",
                 "conditions_of_satisfaction": "x", "citation": _cit()}]},
            {"persona_id": "b", "moves": [
                {"move": "add", "section": "Routing", "title": "two",
                 "conditions_of_satisfaction": "y", "citation": _cit()}]},
        ]
        r = pm.merge_personas(grounded, _base())
        titles = [rec.get("title") for rec in r.manifest["records"]]
        self.assertIn("one", titles)
        self.assertIn("two", titles)


class ConflictSurfacingTests(unittest.TestCase):
    def _conflict(self, moves_a, moves_b):
        grounded = [
            {"persona_id": "domain-expert", "moves": moves_a},
            {"persona_id": "security-reviewer", "moves": moves_b},
        ]
        return pm.merge_personas(grounded, _base())

    def test_confirm_vs_drop_is_surfaced_not_resolved(self):
        r = self._conflict(
            [{"move": "confirm", "req_id": "REQ-001", "reason": "looks right"}],
            [{"move": "drop", "req_id": "REQ-001", "reason": "obsolete", "citation": _cit()}],
        )
        self.assertEqual(len(r.conflicts), 1)
        c = r.conflicts[0]
        self.assertEqual(c.target, "REQ-001")
        self.assertEqual(sorted(c.personas), ["domain-expert", "security-reviewer"])
        self.assertEqual(len(c.moves), 2)  # BOTH moves carried
        # Neither is applied: REQ-001 still present (not dropped), not confirmed-away.
        self.assertIn("REQ-001", [rec["id"] for rec in r.manifest["records"]])
        self.assertEqual(len(r.held_out), 2)

    def test_divergent_corrects_are_surfaced(self):
        r = self._conflict(
            [{"move": "correct", "req_id": "REQ-002",
              "conditions_of_satisfaction": "fix one way", "citation": _cit()}],
            [{"move": "correct", "req_id": "REQ-002",
              "conditions_of_satisfaction": "fix a different way", "citation": _cit()}],
        )
        self.assertEqual(len(r.conflicts), 1)
        self.assertIn("divergent correct", r.conflicts[0].reason)
        # REQ-002 keeps its ORIGINAL content — neither correction silently won.
        req2 = next(rec for rec in r.manifest["records"]
                    if rec.get("title") == "B")
        self.assertEqual(req2["conditions_of_satisfaction"], "b")

    def test_add_vs_drop_on_same_target_is_surfaced(self):
        # An add proposing to replace REQ-003 vs a drop of REQ-003.
        r = self._conflict(
            [{"move": "add", "target_req": "REQ-003", "section": "Errors",
              "title": "replacement", "conditions_of_satisfaction": "new",
              "citation": _cit()}],
            [{"move": "drop", "req_id": "REQ-003", "citation": _cit()}],
        )
        self.assertEqual(len(r.conflicts), 1)
        # Neither applied: REQ-003 still there, replacement not added.
        self.assertIn("REQ-003", [rec["id"] for rec in r.manifest["records"]])
        self.assertNotIn("replacement", [rec.get("title") for rec in r.manifest["records"]])


class SingleRenumberTests(unittest.TestCase):
    def test_exactly_one_terminal_renumber_reusing_007(self):
        grounded = [
            {"persona_id": "a", "moves": [
                {"move": "add", "section": "Routing", "title": "new-early",
                 "conditions_of_satisfaction": "x", "citation": _cit()}]},
        ]
        with mock.patch.object(
            requirements_render, "renumber_to_document_order",
            wraps=requirements_render.renumber_to_document_order,
        ) as spy:
            # persona_merge composes requirements_render via its own reference;
            # patch that reference too.
            with mock.patch.object(pm.requirements_render, "renumber_to_document_order",
                                   spy):
                r = pm.merge_personas(grounded, _base())
        self.assertEqual(spy.call_count, 1)  # ONCE, not per-persona
        self.assertEqual(r.renumber_calls, 1)
        ids = [rec["id"] for rec in r.manifest["records"]]
        self.assertEqual(ids, [f"REQ-{i:03d}" for i in range(1, len(ids) + 1)])

    def test_renumber_is_document_order_over_the_merged_set(self):
        # An add into an early section renumbers so IDs are sequential in doc order.
        grounded = [
            {"persona_id": "a", "moves": [
                {"move": "add", "section": "Routing", "title": "inserted",
                 "conditions_of_satisfaction": "x", "citation": _cit()}]},
        ]
        r = pm.merge_personas(grounded, _base())
        ids = [rec["id"] for rec in r.manifest["records"]]
        self.assertEqual(ids, ["REQ-001", "REQ-002", "REQ-003", "REQ-004"])
        # The Routing section (3 records now) precedes Errors in document order.
        sections = [rec["functional_section"] for rec in r.manifest["records"]]
        self.assertEqual(sections, ["Routing", "Routing", "Routing", "Errors"])


class ExclusionAndProvenanceTests(unittest.TestCase):
    def test_defer_never_participates(self):
        grounded = [{"persona_id": "a", "moves": [
            {"move": "defer", "req_id": "REQ-001"},
            {"move": "add", "section": "Routing", "title": "kept",
             "conditions_of_satisfaction": "x", "citation": _cit()},
        ]}]
        r = pm.merge_personas(grounded, _base())
        self.assertEqual(len(r.applied), 1)
        self.assertIn("kept", [rec.get("title") for rec in r.manifest["records"]])

    def test_applied_moves_retain_agent_validation_provenance(self):
        grounded = [{"persona_id": "a", "moves": [
            {"move": "add", "section": "Routing", "title": "grounded add",
             "conditions_of_satisfaction": "x", "citation": _cit()},
            {"move": "correct", "req_id": "REQ-001",
             "conditions_of_satisfaction": "corrected", "citation": _cit()},
        ]}]
        r = pm.merge_personas(grounded, _base())
        added = next(rec for rec in r.manifest["records"] if rec.get("title") == "grounded add")
        self.assertEqual(added["source_type"], "agent-validation")
        self.assertEqual(added["citation"], _cit())
        corrected = next(rec for rec in r.manifest["records"]
                         if rec.get("conditions_of_satisfaction") == "corrected")
        self.assertEqual(corrected["source_type"], "agent-validation")

    def test_no_scope_leak_no_review_summary_or_revert(self):
        # This slice produces manifest + conflicts only — no review summary,
        # off-switch, or revert (those are slice 5).
        self.assertFalse(hasattr(pm, "build_review_summary"))
        self.assertFalse(hasattr(pm, "revert"))
        self.assertFalse(hasattr(pm, "off_switch"))



def _passage_cit(excerpt="Result.Failure carries the supplied error.", document="reference_docs/spec.txt"):
    return {"document": document, "citation_excerpt": excerpt}


def _add(persona, title, conditions, section="Routing", citation=None):
    return {"persona_id": persona, "moves": [
        {"move": "add", "section": section, "title": title,
         "conditions_of_satisfaction": conditions, "citation": citation or _passage_cit()}]}


class SamePassageDuplicateTests(unittest.TestCase):
    """Compatibility fork CC-27: reviewers that read the same documentation each add the requirement one sentence implies."""

    def test_same_title_same_passage_same_section_lands_once_and_is_reported(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "Failure(e) reports IsSuccess false and Error is e"),
            _add("b", "Failure carries the error", "A failed result exposes the supplied error instance"),
        ], _base())
        self.assertEqual([rec["title"] for rec in r.manifest["records"]].count("Failure carries the error"), 1)
        self.assertEqual(len(r.applied), 1)
        self.assertEqual(len(r.merged_duplicates), 1)
        m = r.merged_duplicates[0]
        self.assertEqual((m["kept_persona"], m["merged_persona"]), ("a", "b"))
        self.assertEqual(r.conflicts, [])

    def test_different_titles_with_overlapping_wording_on_one_passage_are_one_requirement(self):
        r = pm.merge_personas([
            _add("a", "Success factory reports success and carries no error",
                 "Result.Success and Result.Success<TValue,TError>(v) return IsSuccess true and a null Error"),
            _add("b", "Success factory never carries an error",
                 "Result.Success for both result types reports IsSuccess true and a null Error"),
        ], _base())
        self.assertEqual(len(r.merged_duplicates), 1)
        self.assertEqual(len([x for x in r.manifest["records"] if str(x.get("title", "")).startswith("Success")]), 1)

    def test_three_proposals_keep_the_first_and_report_two(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "Failure(e) has IsSuccess false and Error is e"),
            _add("b", "Failure carries the error", "x1"),
            _add("c", "Failure carries the error", "x2"),
        ], _base())
        self.assertEqual(len(r.merged_duplicates), 2)
        self.assertEqual({m["kept_persona"] for m in r.merged_duplicates}, {"a"})

    def test_different_requirements_citing_one_sentence_both_land(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "Failure(e) reports IsSuccess false and Error is e"),
            _add("b", "Cancellation token is honoured", "A cancelled token aborts the call before any output is written"),
        ], _base())
        self.assertEqual(r.merged_duplicates, [])
        titles = [rec.get("title") for rec in r.manifest["records"]]
        self.assertIn("Failure carries the error", titles)
        self.assertIn("Cancellation token is honoured", titles)

    def test_same_title_on_a_different_passage_is_not_merged(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "c1", citation=_passage_cit("Sentence one.")),
            _add("b", "Failure carries the error", "c2", citation=_passage_cit("Sentence two.")),
        ], _base())
        self.assertEqual(r.merged_duplicates, [])
        self.assertEqual([rec.get("title") for rec in r.manifest["records"]].count("Failure carries the error"), 2)

    def test_same_title_and_passage_in_a_different_section_is_not_merged(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "c1", section="Routing"),
            _add("b", "Failure carries the error", "c2", section="Errors"),
        ], _base())
        self.assertEqual(r.merged_duplicates, [])

    def test_same_title_and_passage_in_a_different_document_is_not_merged(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "c1", citation=_passage_cit(document="reference_docs/a.txt")),
            _add("b", "Failure carries the error", "c2", citation=_passage_cit(document="reference_docs/b.txt")),
        ], _base())
        self.assertEqual(r.merged_duplicates, [])

    def test_whitespace_in_the_excerpt_does_not_hide_a_duplicate(self):
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "c1", citation=_passage_cit("Result.Failure carries\nthe supplied  error.")),
            _add("b", "Failure carries the error", "c2", citation=_passage_cit("Result.Failure carries the supplied error.")),
        ], _base())
        self.assertEqual(len(r.merged_duplicates), 1)

    def test_adds_without_a_citation_are_left_to_the_exact_content_rule(self):
        grounded = [
            {"persona_id": "a", "moves": [{"move": "add", "section": "Routing", "title": "T", "conditions_of_satisfaction": "same words here"}]},
            {"persona_id": "b", "moves": [{"move": "add", "section": "Routing", "title": "T", "conditions_of_satisfaction": "other words there"}]},
        ]
        r = pm.merge_personas(grounded, _base())
        self.assertEqual(r.merged_duplicates, [])

    def test_summary_lists_the_folded_suggestions_and_the_disclosure_says_so(self):
        import persona_apply as pa
        r = pm.merge_personas([
            _add("a", "Failure carries the error", "c1"),
            _add("b", "Failure carries the error", "c2"),
        ], _base())
        s = pa.build_review_summary(r)
        self.assertEqual(s["merged_duplicate_count"], 1)
        self.assertEqual(s["merged_duplicates"][0]["merged_persona"], "b")
        self.assertIn("same passage", pa.persona_review_disclosure(s))
        quiet = pa.build_review_summary(pm.merge_personas([_add("a", "Only", "c")], _base()))
        self.assertEqual(quiet["merged_duplicate_count"], 0)
        self.assertNotIn("same passage", pa.persona_review_disclosure(quiet) or "")


class CorrectTierTests(unittest.TestCase):
    """Compatibility fork CC-26: a grounded correct carries the cited document's tier onto the record."""

    def _base_tier3(self):
        b = _base()
        b["records"][0]["tier"] = 3
        return b

    def test_correct_with_a_citation_takes_the_cited_documents_tier(self):
        g = [{"persona_id": "a", "moves": [
            {"move": "correct", "req_id": "REQ-001", "tier": 1,
             "conditions_of_satisfaction": "fixed", "citation": _cit()}]}]
        r = pm.merge_personas(g, self._base_tier3())
        rec = next(x for x in r.manifest["records"] if x.get("conditions_of_satisfaction") == "fixed")
        self.assertEqual(rec["tier"], 1)
        self.assertEqual(rec["source_type"], "agent-validation")

    def test_correct_without_a_tier_leaves_the_record_tier_alone(self):
        g = [{"persona_id": "a", "moves": [
            {"move": "correct", "req_id": "REQ-001",
             "conditions_of_satisfaction": "fixed", "citation": _cit()}]}]
        r = pm.merge_personas(g, self._base_tier3())
        rec = next(x for x in r.manifest["records"] if x.get("conditions_of_satisfaction") == "fixed")
        self.assertEqual(rec["tier"], 3)

    def test_correct_does_not_touch_the_tier_of_other_records(self):
        g = [{"persona_id": "a", "moves": [
            {"move": "correct", "req_id": "REQ-001", "tier": 2,
             "conditions_of_satisfaction": "fixed", "citation": _cit()}]}]
        b = self._base_tier3()
        b["records"][1]["tier"] = 3
        r = pm.merge_personas(g, b)
        other = next(x for x in r.manifest["records"] if x.get("title") == "B")
        self.assertEqual(other["tier"], 3)


if __name__ == "__main__":
    unittest.main()
