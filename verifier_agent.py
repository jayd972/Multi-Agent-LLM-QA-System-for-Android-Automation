# agents/verifier_agent.py

import difflib

class VerifierAgent:
    def __init__(self, use_llm=False, llm_client=None):
        """
        :param use_llm: If True, enables LLM-based fallback reasoning.
        :param llm_client: Optional OpenAI or Gemini client for natural language analysis.
        """
        self.use_llm = use_llm
        self.llm = llm_client

    def verify(self, subgoal, ui_elements):
        """
        Verifies whether the subgoal was successfully completed.

        :param subgoal: dict, one subgoal step (e.g., toggle Wi-Fi off)
        :param ui_elements: list of UI elements from the environment
        :return: dict with 'status', 'reason', 'should_replan'
        """
        action = subgoal.get("action")
        label = (subgoal.get("label") or "").lower()
        expected = subgoal.get("state") if action in ["toggle", "verify"] and "state" in subgoal else subgoal.get("exists", True)

        print(f"\n[Verifier] Verifying action: {action}, label: '{label}'")

        matched_elements = []
        for el in ui_elements:
            text = (el.text or "").lower()
            desc = (el.content_description or "").lower()
            class_name = (el.class_name or "").lower()
            value = getattr(el, "toggle_state", None)
            if label in text or label in desc or self._fuzzy_match(label, text) or self._fuzzy_match(label, desc):
                matched_elements.append((el, text, class_name, value))

        if action == "verify" and "state" in subgoal:
            result = self._verify_toggle_state(label, expected, matched_elements, ui_elements)
        elif action == "verify":
            result = self._verify_exists(label, expected, matched_elements)
        elif action == "toggle":
            result = self._verify_toggle_state(label, expected, matched_elements, ui_elements)
        else:
            result = {"status": "skip", "reason": f"No verification needed for action '{action}'", "should_replan": False}

        if result["status"] == "fail" and self.use_llm and self.llm:
            llm_feedback = self._llm_reasoning(subgoal, ui_elements)
            result["llm_feedback"] = llm_feedback

        print(f"[Verifier] Result: {result}")
        return result

    def _verify_exists(self, label, should_exist, matched_elements):
        found = len(matched_elements) > 0
        print(f"[Verifier] Expect exists={should_exist} → Found={found}")

        if found == should_exist:
            return {"status": "pass", "reason": "Label existence matched", "should_replan": False}
        else:
            return {"status": "fail", "reason": f"Label existence mismatch (expected: {should_exist})", "should_replan": True}

    def _verify_toggle_state(self, label, expected_state, matched_elements, ui_elements):
        expected_bool = str(expected_state).lower() == "on"
        actual = None
        for el, text, class_name, toggle_value in matched_elements:
            label_box = getattr(el, 'bbox_pixels', None)
            if label_box:
                label_ymin, label_ymax = label_box.y_min, label_box.y_max
                for sw in ui_elements:
                    if "switch" in getattr(sw, "class_name", "").lower():
                        sw_box = getattr(sw, 'bbox_pixels', None)
                        if sw_box and (sw_box.y_min < label_ymax) and (sw_box.y_max > label_ymin):
                            actual = getattr(sw, 'is_checked', None)
                            print(f"[Verifier] Using is_checked: {actual}")
                            break
                if actual is not None:
                    break
        if actual is None:
            print("[Verifier] Could not determine toggle state!")
            return {"status": "fail", "reason": "Toggle state not found or ambiguous", "should_replan": True}
        print(f"[Verifier] Toggle state: expected={expected_bool}, actual={actual}")
        if expected_bool == actual:
            return {"status": "pass", "reason": "Toggle state matched", "should_replan": False}
        else:
            return {"status": "fail", "reason": "Toggle state mismatch", "should_replan": True}

    def _fuzzy_match(self, a, b, threshold=0.8):
        return difflib.SequenceMatcher(None, a, b).ratio() > threshold

    def _llm_reasoning(self, subgoal, ui_elements):
        ui_snapshot = "\n".join(
            f"TEXT: {el.text}, DESC: {el.content_description}, CLASS: {el.class_name}"
            for el in ui_elements
        )
        prompt = f"""
You are a mobile QA verifier. The user asked to complete this subgoal:

{subgoal}

The following UI elements are visible:
{ui_snapshot}

The verification failed. Why might that be? Suggest what to check or change.
"""
        try:
            response = self.llm.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[LLM fallback failed: {e}]"
