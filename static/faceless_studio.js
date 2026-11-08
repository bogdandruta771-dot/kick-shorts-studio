/**
 * OmniStudio - Fused Faceless AI Shorts Studio Controller (MoneyPrinterTurbo + SupoClip + OmniStudio)
 */

let facelessScriptData = null;
let facelessEventSource = null;

// Initial setup
document.addEventListener("DOMContentLoaded", () => {
    initFacelessStudio();
});

async function initFacelessStudio() {
    await Promise.all([
        loadFacelessVoices(),
        loadSubtitlePresets()
    ]);
}

async function loadFacelessVoices() {
    const sel = document.getElementById("faceless-voice-select");
    if (!sel) return;
    try {
        const res = await fetch("/api/faceless/voices");
        const data = await res.json();
        sel.innerHTML = "";
        data.voices.forEach(v => {
            const opt = document.createElement("option");
            opt.value = v.id;
            opt.textContent = `${v.name} (${v.gender})`;
            if (v.id === "en-US-ChristopherNeural") opt.selected = true;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.warn("Failed to load voices:", e);
    }
}

async function loadSubtitlePresets() {
    const container = document.getElementById("faceless-subtitle-presets");
    if (!container) return;
    try {
        const res = await fetch("/api/faceless/presets");
        const data = await res.json();
        container.innerHTML = "";
        
        Object.entries(data.presets).forEach(([key, p], idx) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = `p-3 rounded-xl border text-left transition-all ${idx === 0 ? 'border-cyan-500 bg-cyan-500/10' : 'border-brand-border bg-brand-surface hover:border-zinc-500'}`;
            btn.dataset.preset = key;
            btn.onclick = () => selectSubtitlePreset(key);
            
            btn.innerHTML = `
                <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-semibold text-white">${p.name}</span>
                    <span class="w-3.5 h-3.5 rounded-full border border-black" style="background: ${p.highlight}"></span>
                </div>
                <p class="text-[10px] text-zinc-400 leading-tight">${p.description}</p>
            `;
            container.appendChild(btn);
        });
    } catch (e) {
        console.warn("Failed to load subtitle presets:", e);
    }
}

let selectedPresetKey = "submagic_yellow";

function selectSubtitlePreset(key) {
    selectedPresetKey = key;
    const container = document.getElementById("faceless-subtitle-presets");
    if (!container) return;
    container.querySelectorAll("button").forEach(b => {
        if (b.dataset.preset === key) {
            b.className = "p-3 rounded-xl border text-left transition-all border-cyan-500 bg-cyan-500/10 shadow-lg shadow-cyan-500/10";
        } else {
            b.className = "p-3 rounded-xl border text-left transition-all border-brand-border bg-brand-surface hover:border-zinc-500";
        }
    });
}

function setFacelessTopic(topicText) {
    const input = document.getElementById("faceless-topic-input");
    if (input) {
        input.value = topicText;
        generateFacelessScriptUI();
    }
}

async function generateFacelessScriptUI() {
    const topicInput = document.getElementById("faceless-topic-input");
    const genBtn = document.getElementById("btn-faceless-gen-script");
    const scriptBox = document.getElementById("faceless-script-editor");
    const affiliateCheckbox = document.getElementById("faceless-include-affiliate");
    
    const topic = topicInput ? topicInput.value.trim() : "";
    if (!topic) {
        alert("Please enter a topic or select a preset idea.");
        return;
    }

    if (genBtn) {
        genBtn.disabled = true;
        genBtn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin inline mr-1"></i> Generating Viral Script...`;
        lucide.createIcons();
    }

    try {
        const res = await fetch("/api/faceless/generate-script", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                topic: topic,
                provider: "auto",
                include_affiliate: affiliateCheckbox ? affiliateCheckbox.checked : true,
                promo_code: "mesto300"
            })
        });

        const data = await res.json();
        if (data.success && data.script) {
            facelessScriptData = data.script;
            renderScriptEditorUI(data.script);
            const renderBtn = document.getElementById("btn-faceless-render-short");
            if (renderBtn) renderBtn.disabled = false;
        } else {
            alert("Script generation failed: " + (data.detail || "Unknown error"));
        }
    } catch (e) {
        alert("Network error generating script: " + e.message);
    } finally {
        if (genBtn) {
            genBtn.disabled = false;
            genBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4 inline mr-1"></i> Generate Script`;
            lucide.createIcons();
        }
    }
}

function renderScriptEditorUI(script) {
    const titleEl = document.getElementById("faceless-script-title");
    const container = document.getElementById("faceless-segments-container");
    if (titleEl) titleEl.value = script.title || "Viral Faceless Short";
    if (!container) return;

    container.innerHTML = "";
    script.segments.forEach((seg, idx) => {
        const card = document.createElement("div");
        card.className = "p-3 rounded-xl bg-brand-surface border border-brand-border space-y-2";
        
        const labels = ["Hook (0-5s)", "Context / Setup (5-15s)", "Climax / Twist (15-25s)", "Payoff / CTA (25-35s)"];
        const label = labels[idx] || `Beat #${idx + 1}`;

        card.innerHTML = `
            <div class="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                <span class="font-bold text-indigo-400 uppercase tracking-wider">${label}</span>
                <span class="text-[10px] bg-zinc-800 px-2 py-0.5 rounded text-zinc-300">Beat ${idx + 1}</span>
            </div>
            <textarea id="faceless-seg-text-${idx}" rows="2" class="w-full text-xs bg-brand-bg/80 border border-brand-border rounded-lg p-2 text-zinc-100 focus:border-cyan-500 focus:outline-none resize-none leading-relaxed">${seg.text}</textarea>
            <div class="flex items-center gap-2">
                <i data-lucide="video" class="w-3.5 h-3.5 text-cyan-400"></i>
                <span class="text-[10px] text-zinc-400 uppercase font-mono">B-Roll Visual:</span>
                <input id="faceless-seg-kw-${idx}" type="text" value="${seg.visual_keyword || ''}" class="flex-1 text-[11px] bg-brand-bg/80 border border-brand-border rounded px-2 py-1 text-zinc-200 focus:border-cyan-500 focus:outline-none font-mono">
            </div>
        `;
        container.appendChild(card);
    });
    lucide.createIcons();
    
    const editorWrapper = document.getElementById("faceless-editor-wrapper");
    if (editorWrapper) editorWrapper.classList.remove("hidden");
}

function collectEditedScript() {
    if (!facelessScriptData) return null;
    const titleEl = document.getElementById("faceless-script-title");
    const updated = {
        title: titleEl ? titleEl.value.trim() : "Viral Faceless Short",
        segments: []
    };

    facelessScriptData.segments.forEach((_, idx) => {
        const textEl = document.getElementById(`faceless-seg-text-${idx}`);
        const kwEl = document.getElementById(`faceless-seg-kw-${idx}`);
        updated.segments.push({
            text: textEl ? textEl.value.trim() : "",
            visual_keyword: kwEl ? kwEl.value.trim() : ""
        });
    });
    return updated;
}

async function startFacelessShortRender() {
    const finalScript = collectEditedScript();
    if (!finalScript || finalScript.segments.length === 0) {
        alert("Please generate or enter script segments first.");
        return;
    }

    const voiceSel = document.getElementById("faceless-voice-select");
    const voiceId = voiceSel ? voiceSel.value : "en-US-ChristopherNeural";
    const pexelsKeyInput = document.getElementById("faceless-pexels-key");
    const pixabayKeyInput = document.getElementById("faceless-pixabay-key");
    const renderBtn = document.getElementById("btn-faceless-render-short");

    const payload = {
        script_data: finalScript,
        voice_id: voiceId,
        subtitle_preset: selectedPresetKey,
        pexels_api_key: pexelsKeyInput ? pexelsKeyInput.value.trim() : null,
        pixabay_api_key: pixabayKeyInput ? pixabayKeyInput.value.trim() : null,
        bgm_volume: 0.14
    };

    if (renderBtn) {
        renderBtn.disabled = true;
        renderBtn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin inline mr-1"></i> Rendering Short...`;
        lucide.createIcons();
    }

    const progressBox = document.getElementById("faceless-progress-box");
    const progressBar = document.getElementById("faceless-progress-bar");
    const progressMsg = document.getElementById("faceless-progress-msg");
    const previewWrapper = document.getElementById("faceless-preview-wrapper");

    if (progressBox) progressBox.classList.remove("hidden");
    if (progressBar) progressBar.style.width = "5%";
    if (progressMsg) progressMsg.textContent = "Starting render pipeline...";

    try {
        const res = await fetch("/api/faceless/render", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.job_id) {
            trackFacelessProgress(data.job_id);
        } else {
            throw new Error(data.detail || "Failed to start render job");
        }
    } catch (e) {
        alert("Render error: " + e.message);
        if (renderBtn) {
            renderBtn.disabled = false;
            renderBtn.innerHTML = `<i data-lucide="clapperboard" class="w-4 h-4 inline mr-1"></i> Render Faceless Short`;
            lucide.createIcons();
        }
    }
}

function trackFacelessProgress(jobId) {
    if (facelessEventSource) {
        facelessEventSource.close();
    }

    facelessEventSource = new EventSource(`/api/faceless/render-stream/${jobId}`);
    const progressBar = document.getElementById("faceless-progress-bar");
    const progressMsg = document.getElementById("faceless-progress-msg");
    const previewWrapper = document.getElementById("faceless-preview-wrapper");
    const videoPlayer = document.getElementById("faceless-video-player");
    const downloadLink = document.getElementById("faceless-download-btn");
    const renderBtn = document.getElementById("btn-faceless-render-short");

    facelessEventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const pct = Math.round((data.progress || 0) * 100);
            
            if (progressBar) progressBar.style.width = `${pct}%`;
            if (progressMsg) progressMsg.textContent = `${pct}% - ${data.message || 'Processing...'}`;

            if (data.status === "completed" && data.result) {
                facelessEventSource.close();
                if (progressMsg) progressMsg.textContent = "100% - Faceless Short Ready!";
                if (previewWrapper) previewWrapper.classList.remove("hidden");
                if (videoPlayer) {
                    videoPlayer.src = data.result.video_url;
                    videoPlayer.load();
                    videoPlayer.play().catch(() => {});
                }
                if (downloadLink) {
                    downloadLink.href = data.result.video_url;
                    downloadLink.download = data.result.filename;
                }
                if (renderBtn) {
                    renderBtn.disabled = false;
                    renderBtn.innerHTML = `<i data-lucide="check" class="w-4 h-4 inline mr-1 text-emerald-400"></i> Render Finished!`;
                    lucide.createIcons();
                }
            } else if (data.status === "failed") {
                facelessEventSource.close();
                alert("Rendering failed: " + (data.error || data.message));
                if (renderBtn) {
                    renderBtn.disabled = false;
                    renderBtn.innerHTML = `<i data-lucide="clapperboard" class="w-4 h-4 inline mr-1"></i> Try Again`;
                    lucide.createIcons();
                }
            }
        } catch (err) {
            console.error("SSE parse error", err);
        }
    };

    facelessEventSource.onerror = () => {
        facelessEventSource.close();
    };
}

/**
 * SupoClip AI Virality Scorer for Stream Clipper Tab
 */
async function triggerSupoClipViralityScore() {
    const scoreBtn = document.getElementById("btn-supoclip-score");
    const scoreResultBox = document.getElementById("supoclip-virality-results");
    
    // Check if we have audio or transcript in session
    if (scoreBtn) {
        scoreBtn.disabled = true;
        scoreBtn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin inline mr-1"></i> Scoring Virality...`;
        lucide.createIcons();
    }

    try {
        // Collect transcript words from current session if available
        let transcriptPayload = [];
        if (window.currentSessionTranscript && window.currentSessionTranscript.length > 0) {
            transcriptPayload = window.currentSessionTranscript;
        } else {
            // Heuristic sample from video title or default demo stream
            transcriptPayload = [
                {start: 0.0, end: 5.0, text: "Alright chat let's open these 100 cases."},
                {start: 5.1, end: 12.0, text: "Nothing yet, wait look at that gold icon!"},
                {start: 12.1, end: 25.0, text: "NO WAY! BRO I JUST PULLED A FACTORY NEW DRAGON LORE KNIFE! HOLY SHIT!"},
                {start: 25.1, end: 35.0, text: "CLIP THAT RIGHT NOW! This is a 50 thousand dollar drop!"}
            ];
        }

        const res = await fetch("/api/virality/score", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                transcript: transcriptPayload,
                provider: "auto",
                target_clip_duration: 35.0
            })
        });

        const data = await res.json();
        if (data.success && data.clips && data.clips.length > 0) {
            renderViralityResultsUI(data);
        } else {
            alert("No viral clips detected or scoring error.");
        }
    } catch (e) {
        alert("Virality scoring error: " + e.message);
    } finally {
        if (scoreBtn) {
            scoreBtn.disabled = false;
            scoreBtn.innerHTML = `<i data-lucide="flame" class="w-4 h-4 inline mr-1 text-amber-400"></i> AI Virality Hunter (SupoClip)`;
            lucide.createIcons();
        }
    }
}

function renderViralityResultsUI(data) {
    const box = document.getElementById("supoclip-virality-results");
    if (!box) return;

    box.innerHTML = `
        <div class="p-3 bg-indigo-950/40 border border-indigo-500/40 rounded-xl space-y-2 mb-3">
            <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-indigo-300 flex items-center gap-1.5">
                    <i data-lucide="flame" class="w-3.5 h-3.5 text-amber-400"></i>
                    AI Highlight Hunter Results (${data.engine})
                </span>
                <span class="text-[10px] text-zinc-400 font-mono">${data.clips.length} Viral Moments Found</span>
            </div>
        </div>
        <div class="space-y-2.5" id="supoclip-clips-list"></div>
    `;

    const list = box.querySelector("#supoclip-clips-list");
    data.clips.forEach(c => {
        const item = document.createElement("div");
        item.className = "p-3 rounded-xl bg-brand-surface border border-brand-border hover:border-indigo-500/50 transition-all cursor-pointer";
        item.onclick = () => applyViralTrim(c.start_time, c.end_time, c.titles[0]);

        item.innerHTML = `
            <div class="flex items-center justify-between mb-1.5">
                <span class="text-xs font-bold text-white flex items-center gap-2">
                    <span class="px-1.5 py-0.5 rounded bg-indigo-600 text-[10px] font-mono">Rank #${c.rank}</span>
                    ${c.headline}
                </span>
                <span class="px-2 py-0.5 rounded-full text-xs font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    ${c.virality_score}/100
                </span>
            </div>
            <p class="text-[11px] text-zinc-300 mb-2">${c.rationale}</p>
            <div class="flex items-center justify-between text-[10px] text-zinc-400 font-mono">
                <span>⏱️ ${c.start_time.toFixed(1)}s - ${c.end_time.toFixed(1)}s (${c.duration.toFixed(1)}s)</span>
                <span class="text-indigo-400 underline font-semibold">Click to Apply Trim & Title</span>
            </div>
        `;
        list.appendChild(item);
    });

    box.classList.remove("hidden");
    lucide.createIcons();
}

function applyViralTrim(startTime, endTime, viralTitle) {
    // Set trim inputs in Step 2 / Step 3 if available
    const trimStartInput = document.getElementById("trim-start-sec");
    const trimEndInput = document.getElementById("trim-end-sec");
    const titleInput = document.getElementById("ai-title-input");

    if (trimStartInput) trimStartInput.value = startTime;
    if (trimEndInput) trimEndInput.value = endTime;
    if (titleInput && viralTitle) titleInput.value = viralTitle;

    alert(`Applied viral highlight trim: ${startTime}s to ${endTime}s!`);
}
