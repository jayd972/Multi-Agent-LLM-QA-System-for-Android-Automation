import os
import json
import time
from android_world.env.env_launcher import load_and_setup_env
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.verifier_agent import VerifierAgent
from agents.supervisor_agent import SupervisorAgent

from dotenv import load_dotenv
load_dotenv()

MAX_REPLANS = 2

def main(task_prompt):
    env = load_and_setup_env(
        console_port=5554,
        grpc_port=8554,
        emulator_setup=False,
        adb_path=os.getenv("ADB_PATH"),
        render_mode='rgb_array'
    )
    state = env.reset()
    ui_elements = state.ui_elements

    planner = PlannerAgent(task_prompt)
    executor = ExecutorAgent(env)
    verifier = VerifierAgent()
    supervisor = SupervisorAgent()

    subgoals = planner.generate_subgoals()
    logs = []
    visual_trace = []
    i = 0
    replans = 0

    while i < len(subgoals):
        step = subgoals[i]
        print(f"\n[DEBUG] Step {i} — Current subgoal: {json.dumps(step)}")
        print(f"[DEBUG] Number of UI elements: {len(ui_elements)}")
        for el in ui_elements:
            print(f"    [UI] TEXT='{el.text}' | CLASS='{el.class_name}' | BBOX={getattr(el, 'bbox_pixels', None)}")

        if step["action"] == "verify":
            result = verifier.verify(step, ui_elements)
            logs.append({"agent": "verifier", "action": step, "status": result["status"], "reason": result["reason"]})

            if result["status"] == "fail" and result.get("should_replan"):
                replans += 1
                print(f"[Main] Replanning triggered by verifier... (attempt {replans}/{MAX_REPLANS})")
                if replans > MAX_REPLANS:
                    print("[Main] Maximum replans reached. Exiting main loop!")
                    break
                print("[Main] Returning to home before replanning...")
                executor.go_home()
                state = env.reset()
                ui_elements = state.ui_elements
                subgoals = planner.generate_subgoals()
                i = 0
                continue
            elif result["status"] == "fail":
                print("[ERROR] Verification failed, stopping execution.")
                break
        else:
            result = executor.execute(step, ui_elements)
            logs.append({"agent": "executor", "action": step, "status": result['status'], "reason": result.get("reason", "")})

            if result["status"] == "fail":
                replans += 1
                print(f"[Main] Executor failed. Triggering replanning... (attempt {replans}/{MAX_REPLANS})")
                if replans > MAX_REPLANS:
                    print("[Main] Maximum replans reached. Exiting main loop!")
                    print("[Main] Emergency: resetting environment for debug info.")
                    state = env.reset()
                    ui_elements = state.ui_elements
                    print("[ERROR] UI Dump on ultimate fail:")
                    for el in ui_elements:
                        print(f"   [UI] TEXT='{el.text}' | CLASS='{el.class_name}' | BBOX={getattr(el, 'bbox_pixels', None)}")
                    break
                print("[Main] Returning to home before replanning...")
                executor.go_home()
                state = env.get_state(wait_to_stabilize=True)
                ui_elements = state.ui_elements
                subgoals = planner.generate_subgoals()
                i = 0
                continue

            ui_elements = result.get("state", env.get_state()).ui_elements

        frame = env.render()
        if frame is not None:
            print(f"[Trace] Captured frame at step {i}, shape: {frame.shape}")
            visual_trace.append(frame)
        else:
            print(f"[Trace] No frame captured at step {i} (env.render() returned None)")

        i += 1

    # Save logs and trace
    if not os.path.exists("logs"):
        os.makedirs("logs")
    with open("logs/test_log.json", "w") as f:
        json.dump(logs, f, indent=2)

    print(f"[Trace] Saving {len(visual_trace)} frames to logs/visual_trace.npy")
    print(f"[Trace] Current working directory: {os.getcwd()}")
    import numpy as np
    np.save("logs/visual_trace.npy", visual_trace)
    print(f"[Trace] Trace saved! Check logs/visual_trace.npy")

    supervisor.review()
    env.close()

if __name__ == "__main__":
    main("Turn the wifi off and on")
