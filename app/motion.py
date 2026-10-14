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
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\comicbd.ttf" if bold else r"C:\Windows\Fonts\comic.ttf",
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


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        f = (2.0 * t) - 2.0
        return 0.5 * f * f * f + 1.0


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - math.pow(1.0 - t, 3)


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


class Particle:
    def __init__(self, x: float, y: float, size: float, speed: float, phase: float, color: tuple[int, int, int, int]):
        self.x = x
        self.y = y
        self.size = size
        self.speed = speed
        self.phase = phase
        self.color = color


class MotionKeyframeEngine:
    """High-Definition 2D Character-Puppet & Cognitive Paradigm Explainer Engine.

    Features:
    - Crystal-sharp 3D Pixar explorer mascot monkey with expressive poses (waving, pointing,
      thoughtful head-scratching, and victorious celebration).
    - Rich, bright 3D Magic Island observatory studio background.
    - Frosted elevated task card housing the cognitive experiment paradigm.
    - Eye-tracking fixation cross '+' with pulsing radar rings and gamified sinking boat stake.
    - Full working-memory task walkthrough: Stimulus flash ('K P T + B V L') -> retention mask
      ('# # # + # # #') -> spatial probe cue ('_') -> response choices.
    - Smooth, slowly-decelerating mouse cursor arrow that glides gracefully and clicks the target.
    - Clean cinematic dip-to-light transitions between scenes (zero ghosting, zero double-exposure).
    """

    def __init__(self, sample_assets_dir: Path):
        self.sample_assets_dir = sample_assets_dir.resolve()
        self.sprites_dir = Path(__file__).resolve().parent / "assets" / "sprites"
        self.sprites: dict[str, Image.Image] = {}
        self.bg_image: Image.Image | None = None
        self._load_sprites()

        # Seed celebration confetti
        rng = random.Random(42)
        self.confetti_particles = [
            Particle(
                x=rng.uniform(400, 1200),
                y=rng.uniform(-250, 0),
                size=rng.uniform(7.0, 13.0),
                speed=rng.uniform(60.0, 110.0),
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
            for _ in range(40)
        ]

    def _load_sprites(self) -> None:
        """Loads high-res character sprites and background."""
        if not self.sprites_dir.exists():
            return

        # Background
        bg_path = self.sprites_dir / "studio_background.jpg"
        if bg_path.exists():
            try:
                self.bg_image = Image.open(bg_path).convert("RGB")
            except Exception:
                pass

        # Mascot sprites and props
        sprite_names = [
            "mascot_waving",
            "mascot_pointing",
            "mascot_curious",
            "mascot_celebrating",
            "magic_boat",
            "magic_island",
        ]
        for name in sprite_names:
            png_p = self.sprites_dir / f"{name}.png"
            jpg_p = self.sprites_dir / f"{name}.jpg"
            target_p = png_p if png_p.exists() else (jpg_p if jpg_p.exists() else None)
            if target_p:
                try:
                    if target_p.suffix.lower() == ".png":
                        self.sprites[name] = Image.open(target_p).convert("RGBA")
                    else:
                        self.sprites[name] = Image.open(target_p).convert("RGB")
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
        """Generates 80 to 120 keyframe image files with calibrated pacing,
        sharp character rendering, and clean scene transitions.
        """
        if not scenes:
            raise ValueError("No scenes provided for keyframe generation.")

        total_duration_ms = max(int(scenes[-1].get("endTimeMs", 0)), 1000)
        total_duration_sec = total_duration_ms / 1000.0
        total_keyframes = max(80, min(120, int(round(total_duration_sec * keyframe_fps))))
        actual_kf_fps = total_keyframes / max(total_duration_sec, 0.1)

        font_title = get_playful_font(size=32, bold=True)
        font_subtitle = get_ui_font(size=22, bold=False)
        font_letters = get_ui_font(size=38, bold=True)
        font_badge = get_ui_font(size=18, bold=True)
        font_indic_title = get_indic_font(size=26)
        font_indic_body = get_indic_font(size=20)

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
                font_subtitle=font_subtitle,
                font_letters=font_letters,
                font_badge=font_badge,
                font_indic_title=font_indic_title,
                font_indic_body=font_indic_body,
            )

            # 3. Clean Cinematic Dip-to-Light Transition (Zero Ghosting)
            # 0.25s fade to warm light before scene ends, 0.25s fade in from light as new scene starts
            transition_half = 0.25
            time_to_end = scene_end_sec - time_sec
            time_from_start = scene_rel_sec

            if 0.0 < time_to_end <= transition_half and active_scene_idx + 1 < len(scenes):
                # Fade outgoing scene to soft white
                fade_alpha = 1.0 - (time_to_end / transition_half)
                white_overlay = Image.new("RGB", (width, height), (255, 255, 255))
                frame_img = Image.blend(frame_img, white_overlay, alpha=fade_alpha * 0.85)
            elif time_from_start <= transition_half and active_scene_idx > 0:
                # Fade incoming scene in from soft white
                fade_alpha = 1.0 - (time_from_start / transition_half)
                white_overlay = Image.new("RGB", (width, height), (255, 255, 255))
                frame_img = Image.blend(frame_img, white_overlay, alpha=fade_alpha * 0.85)

            # 4. Save keyframe image to storage
            filename = f"keyframe_{kf_idx + 1:04d}.jpg"
            rel_path = f"runs/{run_id}/keyframes/{filename}"
            buf = io.BytesIO()
            frame_img.save(buf, format="JPEG", quality=94, optimize=True)
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
            (x, y + 28),
            (x + 8, y + 22),
            (x + 14, y + 34),
            (x + 19, y + 31),
            (x + 13, y + 19),
            (x + 22, y + 19),
        ]
        draw.polygon(poly, fill=(15, 23, 42, 255), outline=(255, 255, 255, 255), width=2)
        if is_clicked:
            radius = int(10 + click_progress * 24)
            alpha = int(max(0, 220 * (1.0 - click_progress)))
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
        font_subtitle: Any,
        font_letters: Any,
        font_badge: Any,
        font_indic_title: Any,
        font_indic_body: Any,
    ) -> Image.Image:
        """Renders high-definition explainer frame with sharp mascot, background, and UI paradigm."""
        # 1. Base Studio Background
        if self.bg_image:
            canvas = self.bg_image.resize((width, height), Image.Resampling.LANCZOS).copy()
        else:
            canvas = Image.new("RGB", (width, height), (248, 250, 252))

        # Map scenes to 4 canonical explainer acts:
        # Act 1: Welcome & World Establishment
        # Act 2: Eye-Tracking Fixation Rule & Gamified Boat Stake
        # Act 3: Stimulus Presentation & Slow Mouse Cursor Click
        # Act 4: Joyful Celebration & Practice Call
        act3_progress = scene_progress
        if total_scenes <= 1:
            act = 1
        elif total_scenes == 2:
            act = 1 if scene_order == 1 else 3
        elif total_scenes == 3:
            if scene_order == 1:
                act = 1
            elif scene_order == 2:
                # Scene 2 cleanly bridges Act 2 (Fixation Rule) and Act 3 (Task Demonstration & Cursor Click)
                split_threshold = 0.38
                if scene_progress < split_threshold:
                    act = 2
                else:
                    act = 3
                    act3_progress = max(0.0, min(1.0, (scene_progress - split_threshold) / (1.0 - split_threshold)))
            else:
                act = 4
        elif total_scenes == 4:
            act = scene_order
        else:
            ratio = (scene_order - 1) / max(1, total_scenes - 1)
            act = min(4, max(1, int(round(ratio * 3)) + 1))

        # Check for Hindi narration
        script_text = str(scene.get("translatedText") or scene.get("audioScript") or "").strip()
        is_hindi = any("\u0900" <= c <= "\u097f" for c in script_text)

        # Draw Frosted Interactive Card on the Right (X: 380 to 1230, Y: 50 to 670)
        card_box = [380, 50, 1230, 670]
        card_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(card_overlay)
        # Drop shadow
        cdraw.rounded_rectangle([card_box[0] + 4, card_box[1] + 6, card_box[2] + 4, card_box[3] + 6], radius=24, fill=(15, 23, 42, 50))
        # Semi-translucent white card
        cdraw.rounded_rectangle(card_box, radius=24, fill=(255, 255, 255, 240), outline=(226, 232, 240, 255), width=2)
        canvas = Image.alpha_composite(canvas.convert("RGBA"), card_overlay)

        draw = ImageDraw.Draw(canvas)

        # Mascot slow organic breathing & subtle weight shift
        # 4-second gentle breathing cycle
        sway_y = int(math.sin(global_time_sec * 1.5) * 4.0)
        sway_x = int(math.cos(global_time_sec * 0.75) * 1.5)
        mascot_target_h = 490
        mascot_base_x = 25 + sway_x
        mascot_base_y = 190 + sway_y

        if act == 1:
            # ========================================================
            # ACT 1: WELCOME & SETTING THE STAGE
            # ========================================================
            mascot = self.sprites.get("mascot_waving")
            if mascot:
                mw, mh = mascot.size
                msc = mascot_target_h / float(mh)
                m_res = mascot.resize((int(mw * msc), mascot_target_h), Image.Resampling.LANCZOS)
                canvas.paste(m_res, (mascot_base_x, mascot_base_y), m_res)

            # Card Header
            draw.text((430, 85), "Welcome to Magic Island!", font=font_title, fill=(30, 41, 59))
            if is_hindi:
                draw.text((430, 130), "जादुई द्वीप में आपका स्वागत है!", font=font_indic_title, fill=(59, 130, 246))

            # Narrative Explanation inside Card
            draw.text((440, 220), "Meet your explorer guide, Magic Monkey!", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 275), "Today we are testing your visual working memory on the island.", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 330), "Pay close attention to each rule so you can solve every challenge.", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 395), "Are you ready to join our scientific adventure?", font=font_subtitle, fill=(16, 185, 129))

            # Feature Badges
            draw.rounded_rectangle([440, 470, 640, 520], radius=12, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
            draw.text((465, 485), "EYE-TRACKING", font=font_badge, fill=(30, 41, 59))

            draw.rounded_rectangle([660, 470, 860, 520], radius=12, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
            draw.text((680, 485), "LETTER MEMORY", font=font_badge, fill=(30, 41, 59))

            draw.rounded_rectangle([880, 470, 1080, 520], radius=12, fill=(241, 245, 249), outline=(203, 213, 225), width=1)
            draw.text((915, 485), "CHILD STUDY", font=font_badge, fill=(30, 41, 59))

            # Bottom Subtitle
            sub_en = "Listen carefully to Magic Monkey's instructions."
            sub_hi = "मैजिक मंकी के निर्देशों को ध्यान से सुनें।"
            draw.text((440, 600), sub_en if not is_hindi else sub_hi, font=font_subtitle if not is_hindi else font_indic_body, fill=(100, 116, 139))

        elif act == 2:
            # ========================================================
            # ACT 2: EYE-TRACKING FIXATION RULE & GAMIFIED BOAT STAKE
            # ========================================================
            mascot = self.sprites.get("mascot_pointing")
            if mascot:
                mw, mh = mascot.size
                msc = mascot_target_h / float(mh)
                m_res = mascot.resize((int(mw * msc), mascot_target_h), Image.Resampling.LANCZOS)
                canvas.paste(m_res, (mascot_base_x, mascot_base_y), m_res)

            # Card Header
            draw.text((430, 85), "Rule 1: Keep Your Eyes on the Cross (+)", font=font_title, fill=(30, 41, 59))
            if is_hindi:
                draw.text((430, 130), "नियम १: केंद्र (+) पर आँखें केंद्रित रखें", font=font_indic_title, fill=(225, 29, 72))

            # Central Fixation Viewport Card
            vp_box = [460, 190, 1150, 420]
            draw.rounded_rectangle(vp_box, radius=18, fill=(248, 250, 252), outline=(203, 213, 225), width=2)

            # Pulsing fixation radar rings
            pulse = math.sin(global_time_sec * 3.5)
            cx, cy = (vp_box[0] + vp_box[2]) // 2, (vp_box[1] + vp_box[3]) // 2
            r_outer = int(40 + pulse * 6.0)
            draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=(239, 68, 68, 120), width=2)
            draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], outline=(239, 68, 68, 200), width=3)
            draw.text((cx - 13, cy - 26), "+", font=font_letters, fill=(220, 38, 38))

            # Gamified Magic Boat floating gently below
            boat = self.sprites.get("magic_boat")
            if boat:
                bw, bh = boat.size
                bsc = 78 / float(bh)
                boat_scaled = boat.resize((int(bw * bsc), 78), Image.Resampling.LANCZOS)
                boat_bob_y = int(math.sin(global_time_sec * 2.8) * 4.0)
                canvas.paste(boat_scaled, (cx - boat_scaled.width // 2, 445 + boat_bob_y), boat_scaled)

            # Rule Explanation Text
            rule1 = "If your eyes wander away from the cross (+), the magic boat sinks!" if not is_hindi else "यदि आप (+) से आँखें हटाते हैं, तो जादुई नाव डूब जाएगी!"
            rule2 = "Keep your gaze locked right on the center cross throughout the game." if not is_hindi else "खेल के दौरान अपनी आँखें हमेशा केंद्र (+) पर रखें।"
            draw.text((440, 555), rule1, font=font_subtitle if not is_hindi else font_indic_title, fill=(220, 38, 38))
            draw.text((440, 600), rule2, font=font_subtitle if not is_hindi else font_indic_body, fill=(71, 85, 105))

        elif act == 3:
            # ========================================================
            # ACT 3: COGNITIVE TASK WALKTHROUGH & SLOW MOUSE CLICK
            # ========================================================
            # Timing Breakdown within Act 3:
            # 0.0 -> 0.20 * dur: Fixation Cross (+)
            # 0.20 -> 0.45 * dur: Letter Stimulus Flash (K P T + B V L)
            # 0.45 -> 0.65 * dur: Retention Mask Interval (# # # + # # #)
            # 0.65 -> 0.75 * dur: Blue Probe Cue appears under position 5
            # 0.75 -> 0.90 * dur: Mouse Cursor glides slowly with cubic ease-in-out to button [L]
            # 0.90 -> 1.00 * dur: Click registered, ripple radiates, green CORRECT badge pops!

            is_clicked = act3_progress >= 0.88
            click_progress = max(0.0, min(1.0, (act3_progress - 0.88) / 0.12)) if is_clicked else 0.0

            # Mascot selection: Curious thinking pose before click, Victory celebration after click!
            mascot = self.sprites.get("mascot_celebrating") if is_clicked else self.sprites.get("mascot_curious")
            if mascot:
                mw, mh = mascot.size
                msc = mascot_target_h / float(mh)
                m_res = mascot.resize((int(mw * msc), mascot_target_h), Image.Resampling.LANCZOS)
                canvas.paste(m_res, (mascot_base_x, mascot_base_y), m_res)

            # Card Header
            draw.text((430, 80), "Live Task Demonstration: Working Memory", font=font_title, fill=(30, 41, 59))
            if is_hindi:
                draw.text((430, 125), "अक्षर खेल: नीली रेखा वाले अक्षर की पहचान करें", font=font_indic_title, fill=(37, 99, 235))

            # Stimulus Array Viewport Box
            vp_box = [460, 175, 1150, 345]
            draw.rounded_rectangle(vp_box, radius=18, fill=(248, 250, 252), outline=(203, 213, 225), width=2)
            cx = (vp_box[0] + vp_box[2]) // 2

            # Determine task sub-phase
            if act3_progress < 0.20:
                # Fixation
                draw.text((cx - 13, 230), "+", font=font_letters, fill=(220, 38, 38))
                phase_badge = "1. FIXATION CROSS"
            elif act3_progress < 0.45:
                # Flash Letters
                stim_txt = "K   P   T     +     B   V   L"
                draw.text((cx - 240, 230), stim_txt, font=font_letters, fill=(15, 23, 42))
                phase_badge = "2. STIMULUS PRESENTATION"
            elif act3_progress < 0.65:
                # Retention Mask
                stim_txt = "#   #   #     +     #   #   #"
                draw.text((cx - 240, 230), stim_txt, font=font_letters, fill=(71, 85, 105))
                phase_badge = "3. RETENTION MASK (MEMORY)"
            else:
                # Probe Cue active
                stim_txt = "#   #   #     +     #   #   #"
                draw.text((cx - 240, 230), stim_txt, font=font_letters, fill=(71, 85, 105))
                # Vibrant Blue Underline Cue under position 5 ('L')
                cue_x = cx + 115
                draw.line([(cue_x, 295), (cue_x + 40, 295)], fill=(37, 99, 235), width=6)
                phase_badge = "4. PROBE CUE: REPORT LETTER"

            # Phase Badge Pill
            draw.rounded_rectangle([cx - 140, 185, cx + 140, 215], radius=8, fill=(219, 234, 254), outline=(147, 197, 253), width=1)
            draw.text((cx - 115, 190), phase_badge, font=font_badge, fill=(30, 58, 138))

            # Response Buttons Row
            choices = ["B", "F", "V", "K", "L", "N", "P", "T", "Z"]
            btn_w, btn_h, gap = 64, 64, 15
            total_w = len(choices) * btn_w + (len(choices) - 1) * gap
            start_x = (card_box[0] + card_box[2] - total_w) // 2
            btn_y = 395

            target_idx = 4  # 'L'
            target_cx = start_x + target_idx * (btn_w + gap) + btn_w // 2
            target_cy = btn_y + btn_h // 2

            for i, ch in enumerate(choices):
                bx = start_x + i * (btn_w + gap)
                is_target = (i == target_idx)
                is_active = is_target and is_clicked
                fill_c = (220, 252, 231) if is_active else (255, 255, 255)
                border_c = (22, 163, 74) if is_active else (203, 213, 225)
                bw = 3 if is_active else 2
                draw.rounded_rectangle([bx, btn_y, bx + btn_w, btn_y + btn_h], radius=12, fill=fill_c, outline=border_c, width=bw)
                draw.text((bx + 20, btn_y + 10), ch, font=font_letters, fill=(15, 23, 42))

            # CORRECT! Badge
            if is_clicked:
                badge_w = 130
                draw.rounded_rectangle([target_cx - badge_w // 2, btn_y - 42, target_cx + badge_w // 2, btn_y - 10], radius=10, fill=(34, 197, 94), outline=(22, 163, 74), width=2)
                draw.text((target_cx - 48, btn_y - 38), "CORRECT!", font=font_badge, fill=(255, 255, 255))

            # Slow, Elegant Mouse Cursor Trajectory
            start_cx, start_cy = 1100, 560
            if act3_progress < 0.70:
                cur_x, cur_y = start_cx, start_cy
            elif act3_progress < 0.88:
                # Graceful glide using cubic ease-in-out
                travel_p = (act3_progress - 0.70) / 0.18
                ease_p = ease_in_out_cubic(travel_p)
                cur_x = int(start_cx + (target_cx + 8 - start_cx) * ease_p)
                cur_y = int(start_cy + (target_cy + 8 - start_cy) * ease_p)
            else:
                cur_x = target_cx + 8
                cur_y = target_cy + 8

            self._draw_mouse_cursor(draw, cur_x, cur_y, is_clicked=is_clicked, click_progress=click_progress)

            # Subtitle at bottom
            instruction_note = "The mouse cursor smoothly glides to and selects the correct answer [L]." if not is_hindi else "माउस कर्सर धीरे-धीरे सही उत्तर [L] पर जाकर क्लिक करता है।"
            draw.text((440, 505), instruction_note, font=font_subtitle if not is_hindi else font_indic_body, fill=(51, 65, 85))

            metrics_note = "Accuracy and reaction time (RT) are automatically recorded for science." if not is_hindi else "सटीकता और प्रतिक्रिया समय (RT) स्वचालित रूप से रिकॉर्ड किए जाते हैं।"
            draw.text((440, 545), metrics_note, font=font_subtitle if not is_hindi else font_indic_body, fill=(16, 185, 129))

        else:
            # ========================================================
            # ACT 4: JOYFUL CELEBRATION & READY TO PLAY!
            # ========================================================
            mascot = self.sprites.get("mascot_celebrating")
            if mascot:
                mw, mh = mascot.size
                msc = mascot_target_h / float(mh)
                m_res = mascot.resize((int(mw * msc), mascot_target_h), Image.Resampling.LANCZOS)
                # Joyful springy bounce loop
                bounce_y = int(-14.0 * abs(math.sin(global_time_sec * 2.2)))
                canvas.paste(m_res, (mascot_base_x, mascot_base_y + bounce_y), m_res)

            # Confetti rain particles drifting calmly
            for p in self.confetti_particles:
                cx = int((p.x + math.sin(global_time_sec * 1.5 + p.phase) * 20.0) % width)
                cy = int((p.y + global_time_sec * p.speed) % height)
                draw.rounded_rectangle([cx, cy, cx + p.size, cy + p.size * 0.7], radius=3, fill=p.color)

            # Card Header
            draw.text((430, 85), "Great Job! You Are Ready To Play!", font=font_title, fill=(30, 41, 59))
            if is_hindi:
                draw.text((430, 130), "शानदार! अब आप खेल का अभ्यास शुरू करने के लिए तैयार हैं!", font=font_indic_title, fill=(16, 185, 129))

            # Checklist
            draw.text((440, 220), "• Keep your eyes centered on the cross (+)", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 270), "• Remember the letters when they flash", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 320), "• Click the matching letter indicated by the blue clue line", font=font_subtitle, fill=(51, 65, 85))
            draw.text((440, 370), "• Have fun on Magic Island with Magic Monkey!", font=font_subtitle, fill=(51, 65, 85))

            # Glowing START PRACTICE button
            btn_pulse = 0.5 + 0.5 * math.sin(global_time_sec * 3.0)
            btn_outline = (22, 163, 74, int(180 + btn_pulse * 75))
            btn_w = 420
            draw.rounded_rectangle([440, 450, 440 + btn_w, 540], radius=24, fill=(34, 197, 94), outline=btn_outline, width=3)
            draw.text((490, 475), "START PRACTICE", font=font_letters, fill=(255, 255, 255))

        return canvas.convert("RGB")
