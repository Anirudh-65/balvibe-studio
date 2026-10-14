from __future__ import annotations

import io
import math
import os
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .storage import StorageBackend


def get_playful_font(size: int = 28, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        r"C:\Windows\Fonts\comicbd.ttf" if bold else r"C:\Windows\Fonts\comic.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def get_ui_font(size: int = 24, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    paths = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def get_indic_font(size: int = 24) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\Nirmala.ttc",
        r"C:\Windows\Fonts\mangal.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return get_ui_font(size=size, bold=True)


def ease_out_bounce(t: float) -> float:
    t = max(0.0, min(1.0, t))
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


class Particle:
    def __init__(self, x: float, y: float, size: float, speed: float, phase: float, color: tuple[int, int, int, int]):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed
        self.phase = phase
        self.color = color


class MotionKeyframeEngine:
    """2D Character-Puppet & Animated-Cursor Explainer Engine.

    Renders high-cadence keyframes (80-120 frames @ 3-5 fps) matching the animated
    explainer aesthetic of Intro.mp4:
    - 2D Mascot Puppet with expressive states (swinging on vine, talking with lip-flaps,
      natural blinks, thinking/scratching head, reading, and unicycle celebration).
    - Clean, high-contrast, distraction-free white studio background.
    - Live cognitive experiment paradigm (fixation cross '+', flashing letter stimuli,
      mask retention '# # #', spatial probe cue '_').
    - Animated mouse cursor gliding across the screen to click the correct response button.
    - Gamified boat and island story progression with smooth cross-dissolves.
    """

    def __init__(self, sample_assets_dir: Path):
        self.sample_assets_dir = sample_assets_dir.resolve()
        self.sprites_dir = Path(__file__).resolve().parent / "assets" / "sprites"
        self.sprites: dict[str, Image.Image] = {}
        self.base_images: dict[int, Image.Image] = {}
        self._load_sprites()
        self._load_base_assets()

        # Seed celebration confetti
        rng = random.Random(42)
        self.confetti_particles = [
            Particle(
                x=rng.uniform(100, 1180),
                y=rng.uniform(-200, 0),
                size=rng.uniform(7.0, 14.0),
                speed=rng.uniform(80.0, 150.0),
                phase=rng.uniform(0, math.pi * 2),
                color=rng.choice([
                    (251, 191, 36, 255),   # Amber gold
                    (239, 68, 68, 255),    # Crimson red
                    (59, 130, 246, 255),   # Vibrant blue
                    (16, 185, 129, 255),   # Emerald green
                    (168, 85, 247, 255),   # Royal violet
                    (244, 114, 182, 255),  # Playful pink
                ]),
            )
            for _ in range(45)
        ]

    def _load_sprites(self) -> None:
        """Loads transparent PNG character sprites and story illustration assets."""
        if not self.sprites_dir.exists():
            return

        for f in self.sprites_dir.glob("*.*"):
            stem = f.stem
            try:
                if f.suffix.lower() == ".png":
                    self.sprites[stem] = Image.open(f).convert("RGBA")
                else:
                    self.sprites[stem] = Image.open(f).convert("RGB")
            except Exception:
                pass

    def _load_base_assets(self) -> None:
        files = sorted(list(self.sample_assets_dir.glob("*.jpg")))
        for idx, f in enumerate(files, start=1):
            try:
                img = Image.open(f).convert("RGB")
                self.base_images[idx] = img
            except Exception:
                pass

    def generate_keyframes_for_run(
        self,
        run_id: str,
        scenes: list[dict[str, Any]],
        storage: StorageBackend,
        keyframe_fps: int = 4,
        width: int = 1280,
        height: int = 720,
    ) -> list[dict[str, Any]]:
        """Generates 80 to 120 keyframe image files with consistent character poses,
        animated objects, and smooth transitions.
        """
        if not scenes:
            raise ValueError("No scenes provided for keyframe generation.")

        total_duration_ms = max(int(scenes[-1].get("endTimeMs", 0)), 1000)
        total_duration_sec = total_duration_ms / 1000.0
        total_keyframes = max(80, min(120, int(round(total_duration_sec * keyframe_fps))))
        actual_kf_fps = total_keyframes / max(total_duration_sec, 0.1)

        font_title = get_playful_font(size=44, bold=True)
        font_body = get_playful_font(size=28, bold=False)
        font_letters = get_ui_font(size=36, bold=True)
        font_badge = get_ui_font(size=22, bold=True)
        font_indic = get_indic_font(size=28)

        keyframe_records: list[dict[str, Any]] = []

        for kf_idx in range(total_keyframes):
            time_sec = kf_idx / float(actual_kf_fps)
            time_ms = time_sec * 1000.0

            # 1. Identify active scene and relative scene progress
            active_scene_idx = 0
            for idx, sc in enumerate(scenes):
                if sc["startTimeMs"] <= time_ms <= sc["endTimeMs"]:
                    active_scene_idx = idx
                    break
                elif time_ms > sc["endTimeMs"]:
                    active_scene_idx = idx

            active_scene = scenes[active_scene_idx]
            scene_order = active_scene["sceneOrder"]
            scene_start_sec = active_scene["startTimeMs"] / 1000.0
            scene_end_sec = active_scene["endTimeMs"] / 1000.0
            scene_duration = max(scene_end_sec - scene_start_sec, 0.5)
            scene_rel_sec = time_sec - scene_start_sec
            scene_progress = max(0.0, min(1.0, scene_rel_sec / scene_duration))

            # 2. Render primary scene frame
            frame_img = self._render_explainer_scene(
                scene_order=scene_order,
                total_scenes=len(scenes),
                scene=active_scene,
                scene_rel_sec=scene_rel_sec,
                scene_progress=scene_progress,
                global_time_sec=time_sec,
                width=width,
                height=height,
                font_title=font_title,
                font_body=font_body,
                font_letters=font_letters,
                font_badge=font_badge,
                font_indic=font_indic,
            )

            # 3. Check for scene boundary transition (cross-dissolve over ~0.5s)
            transition_window_sec = 0.5
            time_to_next_scene = scene_end_sec - time_sec
            if 0.0 < time_to_next_scene <= transition_window_sec and active_scene_idx + 1 < len(scenes):
                next_scene = scenes[active_scene_idx + 1]
                next_order = next_scene["sceneOrder"]
                next_frame_img = self._render_explainer_scene(
                    scene_order=next_order,
                    total_scenes=len(scenes),
                    scene=next_scene,
                    scene_rel_sec=0.0,
                    scene_progress=0.0,
                    global_time_sec=time_sec,
                    width=width,
                    height=height,
                    font_title=font_title,
                    font_body=font_body,
                    font_letters=font_letters,
                    font_badge=font_badge,
                    font_indic=font_indic,
                )
                alpha = 1.0 - (time_to_next_scene / transition_window_sec)
                frame_img = Image.blend(frame_img, next_frame_img, alpha=alpha)

            # 4. Save keyframe image to storage
            filename = f"keyframe_{kf_idx + 1:04d}.jpg"
            rel_path = f"runs/{run_id}/keyframes/{filename}"
            buf = io.BytesIO()
            frame_img.save(buf, format="JPEG", quality=92, optimize=True)
            storage_path = storage.store_bytes(rel_path, buf.getvalue())
            public_url = f"/api/runs/{run_id}/keyframes/{filename}"

            keyframe_records.append({
                "keyframeIndex": kf_idx + 1,
                "timeSeconds": round(time_sec, 3),
                "sceneOrder": scene_order,
                "sceneTitle": active_scene.get("title", f"Scene {scene_order}"),
                "characterState": active_scene.get("characterState", "active"),
                "fileName": filename,
                "storagePath": str(storage_path),
                "url": public_url,
            })

        return keyframe_records

    def _draw_rainbow_title(self, draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: Any) -> None:
        """Draws playful multi-colored title headings matching Intro.mp4 style."""
        # If Hindi/Devanagari, draw complete phrase with Indic font to preserve ligatures and matras
        if any("\u0900" <= c <= "\u097f" for c in text):
            draw.text((x, y), text, font=font, fill=(59, 130, 246))
            return

        colors = [
            (59, 130, 246),   # Sky blue
            (16, 185, 129),   # Emerald
            (234, 179, 8),    # Amber
            (249, 115, 22),   # Orange
            (239, 68, 68),    # Ruby red
            (168, 85, 247),   # Purple
        ]
        cur_x = x
        for idx, char in enumerate(text):
            c = colors[idx % len(colors)]
            draw.text((cur_x, y), char, font=font, fill=c)
            cur_x += int(draw.textlength(char, font=font))

    def _draw_mouse_cursor(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        is_clicked: bool = False,
        click_progress: float = 0.0,
    ) -> None:
        """Renders an authentic, crisp OS arrow mouse cursor with click ripple animation."""
        poly = [
            (x, y),
            (x, y + 26),
            (x + 7, y + 20),
            (x + 13, y + 32),
            (x + 18, y + 29),
            (x + 12, y + 17),
            (x + 20, y + 17),
        ]
        draw.polygon(poly, fill=(0, 0, 0, 255), outline=(255, 255, 255, 255), width=2)
        if is_clicked:
            radius = int(10 + click_progress * 26)
            alpha = int(max(0, 240 * (1.0 - click_progress)))
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=(34, 197, 94, alpha), width=3)

    def _render_explainer_scene(
        self,
        scene_order: int,
        total_scenes: int,
        scene: dict[str, Any],
        scene_rel_sec: float,
        scene_progress: float,
        global_time_sec: float,
        width: int,
        height: int,
        font_title: Any,
        font_body: Any,
        font_letters: Any,
        font_badge: Any,
        font_indic: Any,
    ) -> Image.Image:
        """Renders 2D character-driven explainer frame with puppet gestures and UI paradigm."""
        # 1. Clean, crisp white studio canvas
        frame = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(frame, "RGBA")

        # Map scenes to 4 canonical explainer acts:
        # Act 1: Welcome & Vine Swing
        # Act 2: Rules, Magic Door & Fixation Rule
        # Act 3: Interactive Stimulus Game & Mouse Cursor Click
        # Act 4: Unicycle Celebration & Practice Call
        act = min(4, max(1, int(round((scene_order - 1) / max(1, total_scenes - 1) * 3)) + 1))

        # Check for Hindi or Indic script
        script_text = str(scene.get("translatedText") or scene.get("audioScript") or "").strip()
        is_hindi = any("\u0900" <= c <= "\u097f" for c in script_text)
        active_body_font = font_indic if is_hindi else font_body
        font_indic_title = get_indic_font(size=38)
        active_title_font = font_indic_title if is_hindi else font_title

        if act == 1:
            # ========================================================
            # ACT 1: WELCOME & VINE SWING
            # ========================================================
            title = "Welcome to Magic Island!" if not is_hindi else "जादुई द्वीप में आपका स्वागत है!"
            title_w = int(draw.textlength(title, font=active_title_font))
            self._draw_rainbow_title(draw, title, (width - title_w) // 2 + 80, 42, active_title_font)

            # Character: Monkey swinging dynamically on jungle vine!
            swing = self.sprites.get("swing_vine")
            if swing:
                sw_w, sw_h = swing.size
                scale = 520 / sw_h
                sw_tw, sw_th = int(sw_w * scale), int(sw_h * scale)
                swing_res = swing.resize((sw_tw, sw_th), Image.Resampling.LANCZOS)

                # Pendulum swing physics
                swing_offset_x = int(math.sin(scene_rel_sec * 3.2) * 26.0)
                swing_offset_y = int(math.cos(scene_rel_sec * 6.4) * 8.0)
                frame.paste(swing_res, (70 + swing_offset_x, 40 + swing_offset_y), swing_res)

            # Story Card: Magic Island illustration floating on right
            island = self.sprites.get("magic_island")
            if island:
                iw, ih = island.size
                isc = 340 / ih
                island_res = island.resize((int(iw * isc), 340), Image.Resampling.LANCZOS)
                card_x, card_y = 520, 140
                draw.rounded_rectangle([card_x - 6, card_y - 6, card_x + island_res.width + 6, card_y + 346], radius=20, fill=(241, 245, 249, 255), outline=(226, 232, 240, 255), width=2)
                frame.paste(island_res, (card_x, card_y))

            # Subtitle / Voice prompt
            sub1 = "A land where every creature can talk, fly, swim" if not is_hindi else "एक जादुई जगह जहाँ हर प्राणी बोल सकता है,"
            sub2 = "and become anything they wish to be!" if not is_hindi else "और जो चाहे वो बन सकता है!"
            draw.text((530, 520), sub1, font=active_body_font, fill=(71, 85, 105))
            draw.text((530, 560), sub2, font=active_body_font, fill=(71, 85, 105))

        elif act == 2:
            # ========================================================
            # ACT 2: MAGIC DOOR & GAMIFIED EYE-TRACKING FIXATION RULE
            # ========================================================
            title = "Keep Your Eyes on the Cross!" if not is_hindi else "स्क्रीन के बीच (+) पर ध्यान दें!"
            title_w = int(draw.textlength(title, font=active_title_font))
            self._draw_rainbow_title(draw, title, (width - title_w) // 2 + 60, 40, active_title_font)

            # Character: Standing Mascot with talking lip-sync and blinks
            blink_cycle = global_time_sec % 2.8
            is_blinking = 2.6 <= blink_cycle <= 2.76
            is_mouth_open = (int(global_time_sec * 7.0) % 3 != 0)

            if is_blinking:
                char_sprite = self.sprites.get("blink")
            elif is_mouth_open:
                char_sprite = self.sprites.get("talk_open")
            else:
                char_sprite = self.sprites.get("talk_closed")

            if char_sprite:
                cw, ch = char_sprite.size
                scale = 420 / ch
                c_tw, c_th = int(cw * scale), int(ch * scale)
                c_res = char_sprite.resize((c_tw, c_th), Image.Resampling.LANCZOS)
                bob_y = int(math.sin(global_time_sec * 2.5) * 4.0)
                frame.paste(c_res, (90, 200 + bob_y), c_res)

            # Central Stimulus Viewport with Centered Fixation Cross (+)
            box_x1, box_y1, box_x2, box_y2 = 420, 160, 1160, 380
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=24, outline=(0, 0, 0), width=3, fill=(255, 255, 255))

            # Pulsing fixation radar rings
            pulse = math.sin(global_time_sec * 5.0)
            cross_x, cross_y = (box_x1 + box_x2) // 2, (box_y1 + box_y2) // 2
            r_outer = int(32 + pulse * 6.0)
            draw.ellipse([cross_x - r_outer, cross_y - r_outer, cross_x + r_outer, cross_y + r_outer], outline=(239, 68, 68, 120), width=2)
            draw.ellipse([cross_x - 18, cross_y - 18, cross_x + 18, cross_y + 18], outline=(239, 68, 68, 200), width=2)
            draw.text((cross_x - 11, cross_y - 25), "+", font=font_letters, fill=(220, 38, 38))

            # Gamified Magic Boat floating on gentle waves
            boat = self.sprites.get("magic_boat")
            if boat:
                bw, bh = boat.size
                bsc = 72 / bh
                boat_res = boat.resize((int(bw * bsc), 72), Image.Resampling.LANCZOS)
                boat_wave_y = int(math.sin(global_time_sec * 3.5) * 6.0)
                frame.paste(boat_res, (cross_x - boat_res.width // 2, 400 + boat_wave_y), boat_res)

            # Gamified instruction text
            rule1 = "If you look away from the (+), the magic boat sinks!" if not is_hindi else "यदि आप (+) से आँखें हटाते हैं, तो नाव डूब जाएगी!"
            rule2 = "Keep your eyes locked right at the center during the game." if not is_hindi else "खेल के दौरान अपनी आँखें बिल्कुल केंद्र पर रखें।"
            draw.text((450, 510), rule1, font=active_body_font, fill=(220, 38, 38))
            draw.text((450, 555), rule2, font=active_body_font, fill=(71, 85, 105))

        elif act == 3:
            # ========================================================
            # ACT 3: INTERACTIVE LETTER GAME & ANIMATED MOUSE CURSOR
            # ========================================================
            title = "Letter Game Demonstration" if not is_hindi else "अक्षर खेल का प्रदर्शन"
            title_w = int(draw.textlength(title, font=active_title_font))
            self._draw_rainbow_title(draw, title, (width - title_w) // 2 + 50, 36, active_title_font)

            # Character: Thinking Mascot scratching head
            thinking = self.sprites.get("thinking")
            if thinking:
                tw, th = thinking.size
                scale = 420 / th
                th_tw, th_th = int(tw * scale), int(th * scale)
                th_res = thinking.resize((th_tw, th_th), Image.Resampling.LANCZOS)
                bob_y = int(math.sin(global_time_sec * 2.0) * 3.0)
                frame.paste(th_res, (80, 200 + bob_y), th_res)

            # Stimulus Display Box
            box_x1, box_y1, box_x2, box_y2 = 360, 160, 1180, 320
            draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=24, outline=(0, 0, 0), width=3, fill=(255, 255, 255))

            # Timing sub-phases:
            # Phase A (0.0s - 1.6s): Letters flash [K P T + B V L]
            # Phase B (1.6s - 2.8s): Mask interval [# # # + # # #]
            # Phase C (2.8s - 5.5s): Probe cue appears [_ blue underline under 'L']
            center_x = (box_x1 + box_x2) // 2

            if scene_rel_sec < 1.6:
                stim_text = "K   P   T     +     B   V   L"
                draw.text((center_x - 220, 215), stim_text, font=font_letters, fill=(15, 23, 42))
                phase_label = "FLASH PHASE"
            elif scene_rel_sec < 2.8:
                stim_text = "#   #   #     +     #   #   #"
                draw.text((center_x - 220, 215), stim_text, font=font_letters, fill=(71, 85, 105))
                phase_label = "RETENTION MASK"
            else:
                stim_text = "#   #   #     +     #   #   #"
                draw.text((center_x - 220, 215), stim_text, font=font_letters, fill=(71, 85, 105))
                # Blue probe underline under position 5
                cue_x = center_x + 105
                draw.line([(cue_x, 275), (cue_x + 36, 275)], fill=(37, 99, 235), width=5)
                phase_label = "PROBE CUE: REPORT LETTER"

            draw.rounded_rectangle([center_x - 120, 128, center_x + 120, 156], radius=8, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
            draw.text((center_x - 90, 132), phase_label, font=font_badge, fill=(30, 41, 59))

            # Multiple Choice Buttons Row
            choices = ["B", "F", "V", "K", "L", "N", "P", "T", "Z"]
            btn_w, btn_h = 64, 64
            gap = 18
            total_btns_w = len(choices) * btn_w + (len(choices) - 1) * gap
            start_btn_x = (width - total_btns_w) // 2 + 50
            btn_y = 440

            target_idx = 4  # 'L' is at index 4
            target_center_x = start_btn_x + target_idx * (btn_w + gap) + btn_w // 2
            target_center_y = btn_y + btn_h // 2

            # Cursor animation timing: glides from (width - 120, 600) to target_center between 2.6s and 4.0s
            cursor_start_t = 2.6
            cursor_dur = 1.4
            cursor_progress = max(0.0, min(1.0, (scene_rel_sec - cursor_start_t) / cursor_dur))
            has_clicked = scene_rel_sec >= (cursor_start_t + cursor_dur)
            click_elapsed = max(0.0, scene_rel_sec - (cursor_start_t + cursor_dur))

            # Render Buttons
            for i, ch in enumerate(choices):
                bx = start_btn_x + i * (btn_w + gap)
                is_target = (i == target_idx)
                is_active = is_target and has_clicked

                fill_c = (220, 252, 231) if is_active else (255, 255, 255)
                border_c = (22, 163, 74) if is_active else (0, 0, 0)
                b_width = 3 if is_active else 2

                draw.rectangle([bx, btn_y, bx + btn_w, btn_y + btn_h], fill=fill_c, outline=border_c, width=b_width)
                draw.text((bx + 20, btn_y + 12), ch, font=font_letters, fill=(15, 23, 42))

            # Draw "CORRECT!" badge once clicked
            if has_clicked:
                badge_txt = "CORRECT!" if not is_hindi else "सही उत्तर!"
                draw.rounded_rectangle([target_center_x - 70, btn_y - 42, target_center_x + 70, btn_y - 10], radius=10, fill=(34, 197, 94), outline=(22, 163, 74), width=2)
                draw.text((target_center_x - 50, btn_y - 38), badge_txt, font=active_body_font if is_hindi else font_badge, fill=(255, 255, 255))

            # Render Animated Mouse Cursor
            start_cx, start_cy = width - 120, 600
            cur_ease = ease_out_cubic(cursor_progress)
            cur_x = int(start_cx + (target_center_x - start_cx) * cur_ease)
            cur_y = int(start_cy + (target_center_y - start_cy) * cur_ease)

            self._draw_mouse_cursor(
                draw=draw,
                x=cur_x,
                y=cur_y,
                is_clicked=has_clicked,
                click_progress=min(1.0, click_elapsed / 0.8),
            )

            # Subtitle instruction at bottom
            instruction_note = "Report the letter indicated by the blue clue line!" if not is_hindi else "नीली रेखा द्वारा दर्शाए गए अक्षर पर क्लिक करें!"
            draw.text((460, 560), instruction_note, font=active_body_font, fill=(71, 85, 105))

        else:
            # ========================================================
            # ACT 4: UNICYCLE CELEBRATION & READY TO PLAY!
            # ========================================================
            title = "Let Us Practice The Game!" if not is_hindi else "आइए खेल का अभ्यास करें!"
            title_w = int(draw.textlength(title, font=active_title_font))
            self._draw_rainbow_title(draw, title, (width - title_w) // 2 + 50, 40, active_title_font)

            # Confetti rain particles
            for p in self.confetti_particles:
                cx = int((p.x + math.sin(global_time_sec * 2.5 + p.phase) * 36.0) % width)
                cy = int((p.y + global_time_sec * p.speed) % height)
                draw.rounded_rectangle([cx, cy, cx + p.size, cy + p.size * 0.7], radius=3, fill=p.color)

            # Mascot: Balancing upside-down on Unicycle with Clown Hat!
            uni = self.sprites.get("unicycle")
            if uni:
                uw, uh = uni.size
                scale = 540 / uh
                u_tw, u_th = int(uw * scale), int(uh * scale)
                uni_res = uni.resize((u_tw, u_th), Image.Resampling.LANCZOS)
                sway_x = int(math.sin(global_time_sec * 2.2) * 18.0)
                frame.paste(uni_res, (130 + sway_x, 120), uni_res)

            # Cheerful invitation text
            txt1 = "Do your best with the letter clues," if not is_hindi else "अक्षरों के संकेतों के साथ अपना सर्वश्रेष्ठ प्रयास करें,"
            txt2 = "and enjoy the ride on the magic boat!" if not is_hindi else "और जादुई नाव की यात्रा का आनंद लें!"
            txt3 = "Everyone inside is very excited to meet you!" if not is_hindi else "सभी आपसे मिलने के लिए बेहद उत्साहित हैं!"
            txt4 = "Are you ready?" if not is_hindi else "क्या आप तैयार हैं?"

            draw.text((540, 200), txt1, font=active_body_font, fill=(30, 41, 59))
            draw.text((540, 245), txt2, font=active_body_font, fill=(30, 41, 59))
            draw.text((540, 310), txt3, font=active_body_font, fill=(16, 185, 129))
            draw.text((540, 380), txt4, font=active_title_font, fill=(59, 130, 246))

            # Glowing "START GAME" button
            btn_pulse = 0.5 + 0.5 * math.sin(global_time_sec * 4.0)
            btn_border = (22, 163, 74, int(180 + btn_pulse * 75))
            draw.rounded_rectangle([540, 470, 880, 560], radius=24, fill=(34, 197, 94), outline=btn_border, width=4)
            btn_txt = "START GAME" if not is_hindi else "खेल शुरू करें"
            b_x = 590 if not is_hindi else 610
            draw.text((b_x, 495), btn_txt, font=active_body_font if is_hindi else font_letters, fill=(255, 255, 255))

        return frame
