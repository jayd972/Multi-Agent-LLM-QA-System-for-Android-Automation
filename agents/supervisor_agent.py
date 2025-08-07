import os
import json
import numpy as np
from PIL import Image
import google.generativeai as genai
import threading

class SupervisorAgent:
    def __init__(
        self,
        log_path="logs/test_log.json",
        trace_path="logs/visual_trace.npy",
        img_dir="logs/frames",
        gemini_api_key=None
    ):
        self.log_path = log_path
        self.trace_path = trace_path
        self.img_dir = img_dir
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not self.gemini_api_key:
            print("[Supervisor] WARNING: No GEMINI_API_KEY provided. LLM feedback will be skipped.")
        else:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel("gemini-2.5-pro") 

    def review(self):
        # Load logs
        if not os.path.exists(self.log_path):
            print("[Supervisor] No log file found.")
            return
        with open(self.log_path) as f:
            logs = json.load(f)

        # Load visual traces
        if os.path.exists(self.trace_path):
            visual_trace = np.load(self.trace_path, allow_pickle=True)
            print(f"[Supervisor] Loaded {len(visual_trace)} frames from {self.trace_path}")
        else:
            print(f"[Supervisor] No visual trace file found at {self.trace_path}")
            visual_trace = []

        # Save trace as images for review
        self._save_frames(visual_trace)
        self._report_metrics(logs)
        if self.gemini_api_key:
            self._llm_feedback(logs)
        else:
            print("[Supervisor] Skipping Gemini feedback (no API key).")

    def _save_frames(self, visual_trace):
        if not os.path.exists(self.img_dir):
            os.makedirs(self.img_dir)
        for i, frame in enumerate(visual_trace):
            if isinstance(frame, np.ndarray):
                img = Image.fromarray(frame.astype("uint8"))
                img.save(os.path.join(self.img_dir, f"frame_{i:03d}.png"))

    def _report_metrics(self, logs):
        total = len(logs)
        fails = [l for l in logs if l["status"] == "fail"]
        passes = [l for l in logs if l["status"] == "pass"]
        recov = sum(1 for l in logs if l["status"] == "fail" and "replan" in l.get("reason", "").lower())
        accuracy = len(passes) / total if total else 0
        recovery_rate = recov / (len(fails) or 1)
        feedback_effectiveness = 1.0 if recov > 0 else 0.0
        print(f"\n[Supervisor] Metrics:")
        print(f" - Bug detection accuracy: {accuracy:.2f}")
        print(f" - Agent recovery rate: {recovery_rate:.2f}")
        print(f" - Supervisor feedback effectiveness: {feedback_effectiveness:.2f}")
        print(f" - Steps tested: {total}")

    def _llm_feedback(self, logs):
        frames_to_attach = []
        n_frames = len(os.listdir(self.img_dir)) if os.path.exists(self.img_dir) else 0
        if n_frames > 0:
            all_imgs = sorted([f for f in os.listdir(self.img_dir) if f.endswith(".png")])
            # Select up to 3 frames: first, middle, last (if available)
            idxs = [0, len(all_imgs)//2, -1] if len(all_imgs) >= 3 else list(range(len(all_imgs)))
            for idx in idxs:
                frame_path = os.path.join(self.img_dir, all_imgs[idx])
                if os.path.exists(frame_path):
                    img = Image.open(frame_path)
                    img = img.resize((480, 270))  # smaller images to speed up LLM
                    frames_to_attach.append(img)

        prompt = (
            "You are an expert QA supervisor agent. "
            "Review the following automated test execution logs for Android UI automation. "
            "For each failure, identify likely causes and suggest improvements. "
            "Recommend extra test coverage or edge cases. "
            "Summarize recovery effectiveness. "
            "Screenshots are attached as reference (from before/after major steps).\n\n"
            f"Test logs:\n{json.dumps(logs, indent=2)}\n"
        )

        def llm_call():
            try:
                gemini_inputs = [prompt] + frames_to_attach
                print(f"\n[Supervisor] Requesting Gemini 2.5 feedback with {len(frames_to_attach)} images...")
                response = self.model.generate_content(gemini_inputs)
                print("\n[Supervisor Gemini feedback]:\n")
                print(response.text)
            except Exception as e:
                print(f"[Supervisor] Gemini feedback error: {e}")

        # Run Gemini in a thread with timeout
        thread = threading.Thread(target=llm_call)
        thread.start()
        thread.join(timeout=45)  # seconds
        if thread.is_alive():
            print("[Supervisor] Gemini feedback timed out. Skipping LLM report.")
