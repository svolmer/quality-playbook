"""Compat fork v1.6.0-maf.4 (CC-23, CC-24): the Phase 1 prompt must teach the forms the Phase 1 validator enforces.

A real model that followed the prompt to the letter was rejected by the validator twice in a live run: the prompt showed the candidate-bug
stage as a bare ``Stage: ...`` line while the validator only recognises the list item ``- Stage: ...``, and the prompt allowed a bulleted
Quality Risks list while the validator counts only numbered entries. The validator is the contract and stays strict; these tests pin that
the prompt's examples and wording agree with it, so the two cannot drift apart again unnoticed.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from bin import run_playbook, run_state_lib

_STAGE_EXAMPLE = re.compile(r"^\s+(- )?Stage:\s+\S", re.MULTILINE)


class Phase1PromptMatchesValidatorTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.prompt = run_playbook.phase1_prompt(True)

    def test_every_indented_stage_example_is_a_list_item_the_validator_matches(self) -> None:
        examples = [m.group(0) for m in _STAGE_EXAMPLE.finditer(self.prompt)]
        self.assertGreaterEqual(len(examples), 3, "the prompt should show the three stage examples")
        for line in examples:
            self.assertRegex(
                line, run_state_lib._CANDIDATE_STAGE_RE.pattern,
                f"prompt example {line!r} is not matched by the validator's stage regex")

    def test_the_prompt_names_the_leading_dash_and_warns_about_the_bare_form(self) -> None:
        self.assertIn("- Stage: open exploration", self.prompt)
        self.assertIn("bare `Stage: ...`", self.prompt)

    def test_the_candidate_bugs_section_instruction_uses_the_list_item_form(self) -> None:
        section = self.prompt.split("`## Candidate Bugs for Phase 2`", 1)[1].split("`## Gate Self-Check`", 1)[0]
        self.assertIn("`- Stage:`", section)
        self.assertNotRegex(section, r"(?<!- )`Stage: ")

    def test_quality_risks_must_be_numbered_not_numbered_or_bulleted(self) -> None:
        section = self.prompt.split("`## Quality Risks`", 1)[1].split("`## Pattern Applicability Matrix`", 1)[0]
        self.assertIn("numbered", section)
        self.assertNotIn("Numbered or\n   bulleted", section)
        self.assertIn("bulleted list is not counted", section)

    def test_a_document_written_exactly_as_the_prompt_teaches_passes_those_two_checks(self) -> None:
        """Behavioural pin: entries in the form the prompt teaches are counted by the validator's own parsers."""
        text = (
            "## Quality Risks\n\n"
            + "".join(f"{i}. Risk {i} in `a.py:{i}` fails for non-numeric input.\n" for i in range(1, 6))
            + "\n## Candidate Bugs for Phase 2\n\n"
            "1. One.\n   - Stage: open exploration\n"
            "2. Two.\n   - Stage: quality risks\n"
            "3. Three.\n   - Stage: pattern deep dive\n"
        )
        risks = run_state_lib._slice_numbered_entries(run_state_lib._slice_h2_section(text, "## Quality Risks"))
        self.assertEqual(len([e for e in risks if run_state_lib._FILE_LINE_CITATION_RE.search(e)]), 5)
        bugs = run_state_lib._slice_numbered_entries(run_state_lib._slice_h2_section(text, "## Candidate Bugs for Phase 2"))
        stages = [run_state_lib._CANDIDATE_STAGE_RE.search(e) for e in bugs]
        self.assertTrue(all(stages), "every candidate-bug entry in the taught form carries a recognised stage")

    def test_the_validator_stays_strict_about_the_bare_form(self) -> None:
        """The fix is in the prompt. A bare `Stage:` line must still count as no stage."""
        bare = "1. Bug.\nStage: open exploration\n"
        self.assertIsNone(run_state_lib._CANDIDATE_STAGE_RE.search(bare))
        bulleted = "- **R1 — Risk.** `a.py:1` is wrong.\n- **R2 — Risk.** `a.py:2` is wrong.\n"
        self.assertEqual(run_state_lib._slice_numbered_entries(bulleted), [])


if __name__ == "__main__":
    unittest.main()
