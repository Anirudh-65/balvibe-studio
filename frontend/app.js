/**
 * BalVibe Pipeline Studio – Frontend Application
 *
 * Interactive 6-step wizard that drives the backend pipeline:
 *   1. Experiment input
 *   2. Age & duration configuration
 *   3. Script review & editing
 *   4. Language selection & translation
 *   5. Voice selection & voiceover generation
 *   6. Final result with audio playback
 */

// ═══════════════════════════════════════════════════════════════
// State
// ═══════════════════════════════════════════════════════════════
const state = {
  currentStep: 1,
  totalSteps: 6,
  runId: null,
  experimentInstruction: "",
  ageBand: "6-8",
  duration: 60,
  storyline: null,          // English storyline
  translatedStoryline: null,
  selectedLanguage: "hi",
  selectedVoice: "male",
  pipelineResult: null,
};

const API_BASE = "";  // same origin

// ═══════════════════════════════════════════════════════════════
// DOM References
// ═══════════════════════════════════════════════════════════════
const $ = (id) => document.getElementById(id);
const panels = [null, $("step1Panel"), $("step2Panel"), $("step3Panel"), $("step4Panel"), $("step5Panel"), $("step6Panel")];

// ═══════════════════════════════════════════════════════════════
// Stepper
// ═══════════════════════════════════════════════════════════════
function updateStepper() {
  const steps = document.querySelectorAll(".step");
  const lines = document.querySelectorAll(".step-line");
  steps.forEach((el, idx) => {
    const stepNum = idx + 1;
    el.classList.remove("active", "completed");
    if (stepNum < state.currentStep) el.classList.add("completed");
    else if (stepNum === state.currentStep) el.classList.add("active");
  });
  lines.forEach((el, idx) => {
    el.classList.toggle("completed", idx + 1 < state.currentStep);
  });
}

function showStep(step) {
  panels.forEach((panel, i) => {
    if (i === 0) return;
    if (panel) panel.classList.toggle("hidden", i !== step);
  });
  state.currentStep = step;
  updateStepper();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ═══════════════════════════════════════════════════════════════
// Toast Notifications
// ═══════════════════════════════════════════════════════════════
function showToast(message, type = "info") {
  const container = $("toastContainer");
  const icons = { success: "✅", error: "❌", info: "ℹ️" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.add("toast-exit");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ═══════════════════════════════════════════════════════════════
// Loading Overlay
// ═══════════════════════════════════════════════════════════════
function showLoading(title, message) {
  $("loadingTitle").textContent = title;
  $("loadingMessage").textContent = message;
  $("loadingOverlay").classList.remove("hidden");
}

function hideLoading() {
  $("loadingOverlay").classList.add("hidden");
}

// ═══════════════════════════════════════════════════════════════
// API helpers
// ═══════════════════════════════════════════════════════════════
async function apiPost(endpoint, body) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Step 1: Experiment Input
// ═══════════════════════════════════════════════════════════════
const experimentInput = $("experimentInput");
const experimentCharCount = $("experimentCharCount");

experimentInput.addEventListener("input", () => {
  experimentCharCount.textContent = `${experimentInput.value.length} characters`;
});

$("loadSampleBtn").addEventListener("click", () => {
  experimentInput.value = "Show six numbers for exactly 2 seconds. Hide one number and ask the child to identify it. Include one practice round and three formal trials, then give a short closing. Do not tell the child whether an answer was correct.";
  experimentInput.dispatchEvent(new Event("input"));
  showToast("Sample experiment loaded", "info");
});

$("step1Next").addEventListener("click", () => {
  const text = experimentInput.value.trim();
  if (!text) {
    showToast("Please enter experiment instructions", "error");
    experimentInput.focus();
    return;
  }
  state.experimentInstruction = text;
  showStep(2);
});

// ═══════════════════════════════════════════════════════════════
// Step 2: Configure (Age & Duration)
// ═══════════════════════════════════════════════════════════════
$("step2Back").addEventListener("click", () => showStep(1));

$("step2Next").addEventListener("click", async () => {
  const ageRadio = document.querySelector('input[name="age"]:checked');
  const durRadio = document.querySelector('input[name="duration"]:checked');
  state.ageBand = ageRadio ? ageRadio.value : "6-8";
  state.duration = durRadio ? parseInt(durRadio.value) : 60;

  showLoading("Generating Script", `Creating a ${state.duration}s script for ages ${state.ageBand} using Groq AI...`);

  try {
    const data = await apiPost("/api/generate-script", {
      instruction: state.experimentInstruction,
      age: state.ageBand,
      duration: state.duration,
    });
    state.runId = data.runId;
    state.storyline = data.storyline;
    hideLoading();
    renderScriptEditor();
    showStep(3);
    showToast("English script generated successfully!", "success");
  } catch (err) {
    hideLoading();
    showToast(err.message, "error");
  }
});

// ═══════════════════════════════════════════════════════════════
// Step 3: Script Review & Edit
// ═══════════════════════════════════════════════════════════════
function renderScriptEditor() {
  const s = state.storyline;
  if (!s) return;

  // Meta badges
  $("scriptMeta").innerHTML = `
    <div class="meta-badge">Age: <span class="meta-value">${s.ageBand}</span></div>
    <div class="meta-badge">Duration: <span class="meta-value">${s.targetDurationSeconds}s</span></div>
    <div class="meta-badge">Scenes: <span class="meta-value">${s.scenes.length}</span></div>
    <div class="meta-badge">Language: <span class="meta-value">${s.language}</span></div>
  `;

  // Scene cards
  const editor = $("scenesEditor");
  editor.innerHTML = s.scenes.map((scene, idx) => `
    <div class="scene-card" data-scene-index="${idx}">
      <div class="scene-card-header" onclick="toggleSceneBody(${idx})">
        <div class="scene-card-title">
          <div class="scene-number">${scene.sceneOrder}</div>
          <span class="scene-name">${scene.characterName} – ${scene.characterState}</span>
        </div>
        <span class="scene-duration">${scene.durationSeconds.toFixed(1)}s</span>
      </div>
      <div class="scene-card-body" id="sceneBody${idx}">
        <textarea
          class="scene-textarea"
          id="sceneText${idx}"
          rows="3"
          data-scene-index="${idx}"
        >${escapeHtml(scene.audioScript)}</textarea>
        <div class="scene-meta-row">
          <span class="scene-meta-tag">${scene.characterType}</span>
          <span class="scene-meta-tag">${scene.visualAssetTag}</span>
          ${scene.trial ? `<span class="scene-meta-tag">Trial #${scene.trial.trialNumber}</span>` : ""}
        </div>
      </div>
    </div>
  `).join("");
}

// Toggle scene expand/collapse
window.toggleSceneBody = function(idx) {
  const body = $(`sceneBody${idx}`);
  if (body) body.style.display = body.style.display === "none" ? "block" : (body.style.display === "block" ? "none" : "block");
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function collectEditedScenes() {
  if (!state.storyline) return;
  state.storyline.scenes = state.storyline.scenes.map((scene, idx) => {
    const textarea = $(`sceneText${idx}`);
    if (textarea) {
      scene.audioScript = textarea.value;
      scene.sourceText = textarea.value;
    }
    return scene;
  });
}

$("saveScriptBtn").addEventListener("click", async () => {
  collectEditedScenes();
  showLoading("Saving Script", "Saving your edits...");
  try {
    await apiPost("/api/save-script", {
      runId: state.runId,
      storyline: state.storyline,
    });
    hideLoading();
    showToast("Script saved successfully!", "success");
  } catch (err) {
    hideLoading();
    showToast(err.message, "error");
  }
});

$("step3Back").addEventListener("click", () => showStep(2));

$("step3Next").addEventListener("click", () => {
  collectEditedScenes();
  showStep(4);
});

// ═══════════════════════════════════════════════════════════════
// Step 4: Translation
// ═══════════════════════════════════════════════════════════════
$("step4Back").addEventListener("click", () => showStep(3));

$("step4Translate").addEventListener("click", async () => {
  state.selectedLanguage = $("languageSelect").value;
  const langLabels = { en: "English", hi: "Hindi", bn: "Bengali", gu: "Gujarati", kn: "Kannada", ml: "Malayalam", mr: "Marathi", od: "Odia", pa: "Punjabi", ta: "Tamil", te: "Telugu" };

  showLoading("Translating", `Translating script to ${langLabels[state.selectedLanguage]}...`);

  try {
    const data = await apiPost("/api/translate", {
      runId: state.runId,
      storyline: state.storyline,
      language: state.selectedLanguage,
    });
    state.translatedStoryline = data.translatedStoryline;
    hideLoading();
    renderTranslation();
    $("translationPreview").classList.remove("hidden");
    $("step4Translate").classList.add("hidden");
    $("step4Next").classList.remove("hidden");
    showToast(`Translation to ${langLabels[state.selectedLanguage]} complete!`, "success");
  } catch (err) {
    hideLoading();
    showToast(err.message, "error");
  }
});

// Reset translate button when language changes
$("languageSelect").addEventListener("change", () => {
  $("translationPreview").classList.add("hidden");
  $("step4Translate").classList.remove("hidden");
  $("step4Next").classList.add("hidden");
});

function renderTranslation() {
  const ts = state.translatedStoryline;
  if (!ts) return;

  const container = $("translatedScenes");
  container.innerHTML = ts.scenes.map((scene) => `
    <div class="translated-scene">
      <div class="translated-header">
        <span class="translated-label">Scene ${scene.sceneOrder}</span>
        <span class="scene-duration">${scene.durationSeconds.toFixed(1)}s</span>
      </div>
      <div class="original-text">EN: ${escapeHtml(scene.audioScript)}</div>
      <div class="translated-text">${state.selectedLanguage.toUpperCase()}: ${escapeHtml(scene.translatedText)}</div>
    </div>
  `).join("");
}

$("step4Next").addEventListener("click", () => showStep(5));

// ═══════════════════════════════════════════════════════════════
// Step 5: Voiceover
// ═══════════════════════════════════════════════════════════════
$("step5Back").addEventListener("click", () => showStep(4));

$("step5Generate").addEventListener("click", async () => {
  const voiceSelect = $("voiceSelect");
  state.selectedVoice = voiceSelect.value;
  const speaker = state.selectedVoice;

  // Show progress
  const progressEl = $("voiceoverProgress");
  progressEl.classList.remove("hidden");
  $("voiceoverBar").style.width = "5%";
  $("voiceoverPercent").textContent = "5%";
  $("step5Generate").disabled = true;

  // Simulate progress while waiting
  let progressVal = 5;
  const progressInterval = setInterval(() => {
    if (progressVal < 85) {
      progressVal += Math.random() * 3 + 0.5;
      $("voiceoverBar").style.width = progressVal + "%";
      $("voiceoverPercent").textContent = Math.round(progressVal) + "%";
    }
  }, 1000);

  try {
    const data = await apiPost("/api/voiceover", {
      runId: state.runId,
      translatedStoryline: state.translatedStoryline,
      speaker,
      language: state.selectedLanguage,
    });

    clearInterval(progressInterval);
    $("voiceoverBar").style.width = "100%";
    $("voiceoverPercent").textContent = "100%";

    state.pipelineResult = data.pipelineResult;

    setTimeout(() => {
      renderResult();
      showStep(6);
      showToast("Voiceover generation complete! 🎉", "success");
      $("step5Generate").disabled = false;
      progressEl.classList.add("hidden");
    }, 600);
  } catch (err) {
    clearInterval(progressInterval);
    $("step5Generate").disabled = false;
    progressEl.classList.add("hidden");
    showToast(err.message, "error");
  }
});

// ═══════════════════════════════════════════════════════════════
// Step 6: Result
// ═══════════════════════════════════════════════════════════════
function renderResult() {
  const r = state.pipelineResult;
  if (!r) return;

  // Summary stats
  const totalDurationMs = r.scenes.reduce((sum, s) => sum + (s.audioDurationMs || 0), 0);
  const langLabels = { "en-IN": "English", "hi-IN": "Hindi", "bn-IN": "Bengali", "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "od-IN": "Odia", "pa-IN": "Punjabi", "ta-IN": "Tamil", "te-IN": "Telugu" };
  const voiceSelect = $("voiceSelect");
  const voiceLabel = voiceSelect.options[voiceSelect.selectedIndex].text;

  $("resultSummary").innerHTML = `
    <div class="result-stat">
      <div class="result-stat-value">${r.scenes.length}</div>
      <div class="result-stat-label">Scenes</div>
    </div>
    <div class="result-stat">
      <div class="result-stat-value">${(totalDurationMs / 1000).toFixed(1)}s</div>
      <div class="result-stat-label">Total Audio</div>
    </div>
    <div class="result-stat">
      <div class="result-stat-value">${langLabels[r.language] || r.language}</div>
      <div class="result-stat-label">Language</div>
    </div>
    <div class="result-stat">
      <div class="result-stat-value">${voiceLabel}</div>
      <div class="result-stat-label">Voice</div>
    </div>
    <div class="result-stat">
      <div class="result-stat-value">${r.ageBand}</div>
      <div class="result-stat-label">Age Band</div>
    </div>
  `;

  // Audio players
  const list = $("audioPlayerList");
  
  let combinedAudioHtml = "";
  if (r.combinedAudio) {
    combinedAudioHtml = `
      <div class="audio-item combined-audio">
        <div class="scene-number" style="width: auto; padding: 0 10px; border-radius: 4px;">Full Output</div>
        <div class="audio-item-info">
          <div class="audio-item-title">Combined Storyline Audio</div>
          <div class="audio-item-duration">${(totalDurationMs / 1000).toFixed(1)}s</div>
        </div>
        <audio controls preload="none" src="${r.combinedAudio}"></audio>
      </div>
      <hr style="margin: 1.5rem 0; border: none; border-top: 1px solid var(--border-color);"/>
      <h4 style="margin-bottom: 1rem; color: var(--text-color); font-weight: 500;">Individual Scenes</h4>
    `;
  }
  
  list.innerHTML = combinedAudioHtml + r.scenes.map((scene) => `
    <div class="audio-item">
      <div class="scene-number">${scene.sceneOrder}</div>
      <div class="audio-item-info">
        <div class="audio-item-title">${escapeHtml(scene.characterName)} – ${escapeHtml(scene.characterState)}</div>
        <div class="audio-item-duration">${scene.audioDurationMs ? (scene.audioDurationMs / 1000).toFixed(1) + 's' : '—'}</div>
      </div>
      <audio controls preload="none" src="${scene.audioFile}"></audio>
    </div>
  `).join("");
}

$("startOverBtn").addEventListener("click", () => {
  // Reset state
  state.runId = null;
  state.storyline = null;
  state.translatedStoryline = null;
  state.pipelineResult = null;
  experimentInput.value = "";
  experimentCharCount.textContent = "0 characters";
  $("translationPreview").classList.add("hidden");
  $("step4Translate").classList.remove("hidden");
  $("step4Next").classList.add("hidden");
  showStep(1);
  showToast("Ready for a new pipeline run!", "info");
});

$("downloadAllBtn").addEventListener("click", () => {
  const r = state.pipelineResult;
  if (!r) return;

  r.scenes.forEach((scene) => {
    if (scene.audioFile) {
      const a = document.createElement("a");
      a.href = scene.audioFile;
      a.download = `scene_${String(scene.sceneOrder).padStart(3, "0")}.wav`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  });
  showToast("Audio files download started!", "success");
});

// ═══════════════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  updateStepper();
});
