import os
import json
from openai import OpenAI

class PlannerAgent:
    def __init__(self, task_prompt: str, model: str = "gpt-3.5-turbo"):
        self.task_prompt = task_prompt
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def generate_subgoals(self):
        prompt = f"""
You are a mobile QA planner.

Your job is to convert a high-level natural language goal into a **sequence of JSON subgoals** for automated testing on Android.

Supported subgoal types:
- {{ "action": "open_app_drawer" }}
- {{ "action": "open_app", "name": "<app_name>" }}
- {{ "action": "tap", "label": "<label>" }}
- {{ "action": "toggle", "label": "<label>", "state": "on/off" }}
- {{ "action": "verify", "label": "<label>", "state": "on/off" }}

⚠️ Guidelines:
- Use the **exact visible UI label** as seen on Android.

✅ Example:
Goal: "Turn Wi-Fi off"

Subgoals:
[
  {{ "action": "open_app_drawer" }},
  {{ "action": "open_app", "name": "Settings" }},
  {{ "action": "tap", "label": "Network & internet" }},
  {{ "action": "tap", "label": "Internet" }},
  {{ "action": "toggle", "label": "Wi-Fi", "state": "off" }},
  {{ "action": "verify", "label": "Wi-Fi", "state": "off" }}
]

Now generate subgoals for:
"{self.task_prompt}"
Only return a valid JSON array.
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            message = response.choices[0].message.content
            subgoals = json.loads(message)
            return subgoals

        except Exception as e:
            print(f"[Planner Error] {e}")
            return [{"action": "noop"}]
