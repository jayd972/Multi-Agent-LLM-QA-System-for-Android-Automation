# Multi-Agent LLM QA System for Android Automation

A full-stack, modular, multi-agent system for **LLM-powered Mobile QA Automation** on Android.  

## 🚀 Project Overview

This project extends the [`Agent-s`](https://github.com/simular-ai/Agent-S) architecture and integrates [`android_world`](https://github.com/google-research/android_world) for a robust, end-to-end QA pipeline.  
It simulates how a team of QA agents (Planner, Executor, Verifier, Supervisor) can collaboratively solve natural-language mobile automation tasks, with LLM-driven reasoning and dynamic replanning.

---

## 🧠 Architecture

**Agents:**
- **Planner Agent:** Decomposes high-level goals into stepwise, actionable subgoals using LLMs.
- **Executor Agent:** Executes UI actions in the Android environment (touch, scroll, toggle).
- **Verifier Agent:** Checks each step’s outcome, detects failures, and triggers replanning if needed.
- **Supervisor Agent:** Analyzes logs and visual traces, proposes improvements, and summarizes test coverage.

---

## 📁 Code Structure

```bash
├── main.py                 # Pipeline entry point: runs a full QA task
├── agents/
│   ├── planner\_agent.py    # PlannerAgent: LLM-driven goal decomposition
│   ├── executor\_agent.py   # ExecutorAgent: UI action executor
│   ├── verifier\_agent.py   # VerifierAgent: stepwise result verification
│   └── supervisor\_agent.py # SupervisorAgent: review and reporting
├── logs/                   # Stores run logs and visual traces
├── requirements.txt        # Python dependencies
└── README.md
````

---

## 🏗️ Setup & Installation

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/your-repo/multi-agent-android-qa.git
cd multi-agent-android-qa
pip install -r requirements.txt
````

### 2. Environment Setup

* **Android Emulator:** Install and set up Android emulator with [android\_world](https://github.com/google-research/android_world).

* **Environment Variables:** Create a `.env` file with your API keys and ADB path:

  ```ini
  OPENAI_API_KEY=your-openai-key
  GEMINI_API_KEY=your-gemini-key
  ADB_PATH=/path/to/adb
  ```

* **Other Requirements:** See `requirements.txt`.

---

## ⚡ Usage Example

Run an end-to-end mobile QA task, e.g., turning Wi-Fi off and on:

```bash
python main.py
```

You can change the default task by editing the last line in `main.py`:

```python
if __name__ == "__main__":
    main("Turn the wifi off and on")
```

---

## 🧩 Agent Descriptions

### 1. Planner Agent (`planner_agent.py`)

* Input: High-level QA goal (natural language)
* Output: JSON list of actionable subgoals (open app, tap, toggle, verify)
* Powered by OpenAI LLM

### 2. Executor Agent (`executor_agent.py`)

* Receives each subgoal, inspects UI, selects actions (touch, scroll, etc.)
* Uses `adb` and `android_world.env` for grounded control

### 3. Verifier Agent (`verifier_agent.py`)

* Checks if the expected UI state is reached
* Pass/fail + functional bug detection
* Can leverage LLM reasoning for ambiguous cases

### 4. Supervisor Agent (`supervisor_agent.py`)

* Reviews complete logs and visual traces (screenshots)
* Summarizes bug detection, recovery, and test coverage
* Optionally uses Gemini LLM for expert suggestions

---

## 📝 Output & Logs

* **QA Logs:** `logs/test_log.json` (per-agent actions, failures, replans)
* **Visual Trace:** `logs/visual_trace.npy` (frame-by-frame UI screenshots)
* **Supervisor Report:** Printed to console, includes Gemini feedback

---

## 💡 Extensions

* Integrate the [`android_in_the_wild`](https://github.com/google-research/android_in_the_wild) dataset for real-world robustness.
* Expand Supervisor reporting and auto-evaluation.
* Add more flexible Planner/Verifier LLM prompts for broader tasks.

---

## 🛠️ Troubleshooting

* Ensure emulator is running and accessible.
* Verify all API keys and `ADB_PATH` are set correctly in `.env`.
* See printed logs for agent-by-agent debugging.

---

## 📄 License

MIT License

---

## 🎥 Demo

Check out the working demo below!

![Demo](demo.gif)
