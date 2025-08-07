import os
import sys
import json
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

# Adjust path to import main from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import main as run_agent  # Now you can run your pipeline from here

# Paths (relative to project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTERNAL_DIR = os.path.join(PROJECT_ROOT, "external_validation")
GT_TRACES_DIR = os.path.join(EXTERNAL_DIR, "gt_traces")
PROMPT_FILE = os.path.join(EXTERNAL_DIR, "gt_prompts.json")
RESULTS_DIR = os.path.join(EXTERNAL_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

def load_gt_trace(trace_path):
    """
    Loads ground truth trace as npy or directory of images.
    """
    if trace_path.endswith(".npy"):
        return np.load(trace_path, allow_pickle=True)
    elif os.path.isdir(trace_path):
        imgs = []
        for fname in sorted(os.listdir(trace_path)):
            if fname.endswith('.png'):
                imgs.append(np.array(Image.open(os.path.join(trace_path, fname))))
        return imgs
    else:
        raise ValueError("Unsupported ground truth trace format.")

def compare_traces(gt_frames, agent_frames):
    """
    Compares ground truth frames to agent frames using SSIM (structural similarity).
    Returns average similarity and step counts.
    """
    min_len = min(len(gt_frames), len(agent_frames))
    step_similarity = []
    for i in range(min_len):
        gt = np.array(Image.fromarray(gt_frames[i]).convert('L').resize((320, 320)))
        ag = np.array(Image.fromarray(agent_frames[i]).convert('L').resize((320, 320)))
        sim, _ = ssim(gt, ag, full=True)
        step_similarity.append(sim)
    avg_ssim = float(np.mean(step_similarity)) if step_similarity else 0.0
    return {
        "steps_gt": len(gt_frames),
        "steps_agent": len(agent_frames),
        "avg_ssim": avg_ssim,
        "frame_similarities": step_similarity,
    }

def external_validation():
    # Load prompt mapping
    with open(PROMPT_FILE, 'r') as f:
        prompts = json.load(f)  # [{"trace_file": "...", "prompt": "..."}]

    summary = []

    for i, entry in enumerate(prompts):
        trace_file = entry["trace_file"]
        prompt = entry["prompt"]
        print(f"\n=== [Validation #{i+1}] User prompt: {prompt}")

        # Load ground truth frames
        gt_frames = load_gt_trace(os.path.join(GT_TRACES_DIR, trace_file))

        # Run agent pipeline on prompt (generates logs/visual_trace.npy)
        run_agent(prompt)  # This should overwrite logs/visual_trace.npy
        agent_frames = np.load(os.path.join(PROJECT_ROOT, "logs", "visual_trace.npy"), allow_pickle=True)

        # Compare traces
        result = compare_traces(gt_frames, agent_frames)
        print(f"  Steps in ground truth: {result['steps_gt']}")
        print(f"  Steps by agent: {result['steps_agent']}")
        print(f"  Avg frame SSIM: {result['avg_ssim']:.2f}")

        # Save per-task result
        result_out = {
            "prompt": prompt,
            "trace_file": trace_file,
            "steps_gt": result["steps_gt"],
            "steps_agent": result["steps_agent"],
            "avg_ssim": result["avg_ssim"],
        }
        with open(os.path.join(RESULTS_DIR, f"result_{i+1}.json"), "w") as f:
            json.dump(result_out, f, indent=2)
        summary.append(result_out)

    # Save all results
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nAll external validation tasks completed.")

if __name__ == "__main__":
    external_validation()
