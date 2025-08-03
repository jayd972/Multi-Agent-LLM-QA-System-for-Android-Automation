import time
import os
import subprocess
from android_world.env import json_action

class ExecutorAgent:
    def __init__(self, env, retries=3, delay=1.2):
        self.env = env
        self.adb_path = os.getenv("ADB_PATH")
        self.retries = retries
        self.delay = delay

    def execute(self, subgoal, ui_elements):
        action = subgoal.get("action")
        print(f"\n[Executor] Executing: {subgoal}")

        if action == "open_app_drawer":
            return self._open_app_drawer()
        elif action == "scroll":
            return self._scroll()
        elif action == "tap":
            return self._tap_by_label(subgoal, ui_elements)
        elif action == "open_app":
            return self._open_app(subgoal, ui_elements)
        elif action == "toggle":
            return self._tap_by_label(subgoal, ui_elements)
        return {"status": "fail", "reason": f"Unknown action: {action}"}

    def go_home(self, retries=3):
        print("[Executor] Going HOME using ADB keyevent.")
        if self.adb_path:
            for i in range(retries):
                try:
                    subprocess.run([self.adb_path, "shell", "input", "keyevent", "3"], check=True)
                    time.sleep(1)
                except Exception as e:
                    print(f"[Executor] Failed to go home: {e}")
        else:
            print("[Executor] No ADB path set—cannot go home.")

    def _is_home_screen(self, ui_elements):
        for el in ui_elements:
            if (el.text and el.text.lower() in ["settings", "chrome", "phone", "contacts", "messages"]) and el.bbox_pixels:
                return True
        not_home_keywords = ["search settings", "battery", "display", "network & internet", "notifications"]
        for el in ui_elements:
            if el.text and any(k in el.text.lower() for k in not_home_keywords):
                return False
        return False

    def _is_app_drawer_open(self, ui_elements):
        app_icon_count = 0
        for el in ui_elements:
            if el.text and el.bbox_pixels and len(el.text) >= 2:
                label = el.text.lower()
                if label not in [
                    "settings", "search", "search settings", "wallpaper",
                    "network & internet", "apps", "notifications", "display"
                ] and not any(x in label for x in ["&", ":", " "]):
                    app_icon_count += 1
        print(f"[Executor] Detected {app_icon_count} app-like icons on screen.")
        return app_icon_count >= 6

    def _open_app_drawer(self):
        for attempt in range(3):
            print(f"[Executor] Attempting to open app drawer (attempt {attempt + 1})")
            state = self.env.get_state(wait_to_stabilize=True)
            ui_elements = state.ui_elements

            if self._is_app_drawer_open(ui_elements):
                print("[Executor] 🟢 App drawer is already open!")
                return {"status": "success", "state": state}

            if not self._is_home_screen(ui_elements):
                print("[Executor] 🚫 Not on home screen — attempting to go home again.")
                self.go_home()
                time.sleep(1)
                continue

            print("[Executor] Performing swipe to open app drawer...")
            self._mid_screen_scroll()
            time.sleep(2)

            state = self.env.get_state(wait_to_stabilize=True)
            ui_elements = state.ui_elements

            if self._is_app_drawer_open(ui_elements):
                print("[Executor] ✅ App drawer opened after swipe.")
                return {"status": "success", "state": state}

        print("[Executor] ❌ App drawer failed to open after 3 attempts! Dumping UI for debug:")
        for el in ui_elements:
            print(f"   [UI] TEXT='{el.text}', CLASS='{el.class_name}', BBOX={getattr(el, 'bbox_pixels', None)}")
        return {"status": "fail", "reason": "App drawer failed to open"}

    def _open_app(self, subgoal, ui_elements):
        app_name = subgoal.get("name", "").lower()
        for scroll_attempt in range(3):
            for el in ui_elements:
                if app_name in (el.text or "").lower() and el.bbox_pixels:
                    print(f"[Executor] Found app visually: {el.text}")
                    return self._tap(el)
            print(f"[Executor] App '{app_name}' not found, scrolling (attempt {scroll_attempt + 1})")
            self._mid_screen_scroll()
            ui_elements = self.env.get_state(wait_to_stabilize=True).ui_elements
        pkg = subgoal.get("package_name")
        if pkg and self.adb_path:
            try:
                print(f"[Executor] Using ADB fallback to launch package: {pkg}")
                subprocess.run([
                    self.adb_path, "shell", "monkey",
                    "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"
                ], check=True)
                time.sleep(2)
                return {"status": "success"}
            except Exception as e:
                print(f"[Executor] ADB fallback failed: {e}")
                return {"status": "fail", "reason": f"ADB fallback failed: {e}"}
        else:
            return {"status": "fail", "reason": f"App '{app_name}' not found and no fallback provided"}

    def _mid_screen_scroll(self):
        if self.adb_path:
            try:
                print("[Executor] Performing ADB mid-screen swipe (540,1300) → (540,700)")
                subprocess.run([
                    self.adb_path, "shell", "input", "swipe", "540", "1300", "540", "700"
                ], check=True)
            except Exception as e:
                print(f"[Executor] ADB swipe failed: {e}")
        else:
            print("[Executor] No ADB path set — cannot perform swipe")

    def _scroll(self):
        current_ui = self.env.get_state(wait_to_stabilize=True).ui_elements
        visible_texts = [el.text.lower() for el in current_ui if el.text]
        print(f"[Executor] Visible text elements before scroll: {visible_texts}")
        if any(term in txt for term in ["wifi", "wi-fi", "network", "internet"] for txt in visible_texts):
            print("[Executor] Scroll skipped — relevant label already visible")
            return {"status": "skipped", "state": self.env.get_state(wait_to_stabilize=True)}
        self._mid_screen_scroll()
        return {"status": "success", "state": self.env.get_state(wait_to_stabilize=True)}

    def _tap_by_label(self, subgoal, ui_elements):
        label = subgoal.get("label", "").lower()
        print(f"[Executor] Looking for label match: '{label}'")
        alias_map = {
            "wi-fi": ["wifi", "wi-fi"],
            "wifi": ["wi-fi", "wifi"],
            "bluetooth": ["bluetooth"],
            "airplane mode": ["airplane mode"],
        }
        search_terms = [label] + alias_map.get(label, [])

        # Find all label elements
        label_els = [el for el in ui_elements if any(term in (el.text or '').lower() for term in search_terms)]
        if not label_els:
            print(f"[Executor] ❌ No elements with label '{label}' found!")
            return {"status": "fail", "reason": f"No label match for '{label}'"}

        # For toggles, look for Switches that are spatially close to the label
        if subgoal.get("action") == "toggle":
            for lbl in label_els:
                # Find Switches in same row (y-center within 60px, and close in x)
                y_center = (lbl.bbox_pixels.y_min + lbl.bbox_pixels.y_max) // 2
                candidates = [
                    el for el in ui_elements
                    if "switch" in (el.class_name or '').lower() and el.bbox_pixels
                    and abs(((el.bbox_pixels.y_min + el.bbox_pixels.y_max) // 2) - y_center) < 60
                ]
                # Pick the Switch with highest x (usually rightmost in the row)
                if candidates:
                    switch_el = max(candidates, key=lambda el: el.bbox_pixels.x_min)
                    print(f"[Executor] ✅ Found switch for label '{label}' at y={y_center}: {switch_el}")
                    return self._tap(switch_el)

            print(f"[Executor] ❌ No matching Switch found in row with label '{label}'! Falling back to label tap.")

        # If not toggle or failed above, tap the label itself
        # Use the first match
        el = label_els[0]
        print(f"[Executor] ✅ Matched label/desc for '{label}': {el.text or el.content_description}")
        return self._tap(el)


    def _tap(self, el):
        bbox = el.bbox_pixels
        x = (bbox.x_min + bbox.x_max) // 2
        y = (bbox.y_min + bbox.y_max) // 2
        print(f"[Executor] Tapping at ({x}, {y}) on '{el.text}'")
        tap = json_action.JSONAction(action_type="click", x=x, y=y)
        self.env.execute_action(tap)
        time.sleep(1.5)
        return {"status": "success", "state": self.env.get_state(wait_to_stabilize=True)}
