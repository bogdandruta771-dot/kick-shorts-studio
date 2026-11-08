// Global Studio State
        let currentScript = null;
        let activeSceneIndex = 0;
        let availablePresets = [];
        let previewDebounceTimer = null;
        let currentPreviewProgress = 0.50;
        let scenePlaybackInterval = null;

        // Initialize on DOM load
        document.addEventListener('DOMContentLoaded', async () => {
            lucide.createIcons();
            await checkSystemStatus();
            await loadPresets();
            await loadOutputsLibrary();
        });

        // 1. Check Server & Hardware Encoder Status
        async function checkSystemStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.encoder) {
                    const pill = document.getElementById('encoderPill') || document.getElementById('header-encoder-badge');
                    const text = document.getElementById('encoderText') || document.getElementById('header-encoder-text');
                    if (pill) pill.classList.remove('hidden');
                    if (text) text.innerText = ${data.encoder.toUpperCase()} Ready;
                }
            } catch (err) {
                console.warn('Status check notice:', err);
            }
        }

        let activePresetId = 'tradeit_mesto300_authentic';

        // 2. Load & Render Preset Templates
        function renderPresetButtons(activeId) {
            const container = document.getElementById('presetsList');
            if (!container) return;
            container.innerHTML = '';

            availablePresets.forEach((p) => {
                const btn = document.createElement('button');
                const isSelected = (p.id === activeId);
                btn.id = `presetBtn_${p.id}`;
                btn.className = `p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                    isSelected 
                        ? 'bg-brand-accent/25 border-brand-accent ring-2 ring-brand-accent/50 text-white shadow-lg glow-accent' 
                        : 'bg-brand-surface border-brand-border text-gray-300 hover:border-brand-accent/50 hover:bg-brand-surface/90'
                }`;
                btn.innerHTML = `
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[10px] font-mono ${isSelected ? 'text-brand-cyan font-bold' : 'text-gray-400'} truncate">${p.badge || 'Template'}</span>
                        <i data-lucide="${isSelected ? 'check-circle-2' : 'chevron-right'}" class="w-3.5 h-3.5 ${isSelected ? 'text-brand-cyan' : 'text-gray-500'} flex-shrink-0"></i>
                    </div>
                    <div class="text-xs font-semibold truncate ${isSelected ? 'text-white font-bold' : 'text-gray-200'}">${p.name}</div>
                    <div class="text-[10px] ${isSelected ? 'text-indigo-200' : 'text-gray-400'} truncate">${p.category || 'General'}</div>
                `;
                btn.onclick = () => selectPreset(p.id);
                container.appendChild(btn);
            });
            lucide.createIcons();
        }

        async function loadPresets() {
            try {
                const res = await fetch('/api/presets');
                const data = await res.json();
                availablePresets = data.presets || [];

                let defaultPreset = availablePresets.find(p => p.id === activePresetId) || availablePresets[0];
                if (defaultPreset) {
                    activePresetId = defaultPreset.id;
                    renderPresetButtons(activePresetId);
                    applyScriptData(defaultPreset);
                    previewSpecificScene(0, 0.50);
                }
            } catch (err) {
                console.error('Failed to load presets:', err);
            }
        }

        function selectPreset(presetId) {
            activePresetId = presetId;
            renderPresetButtons(presetId);
            const found = availablePresets.find(p => p.id === presetId);
            if (found) {
                applyScriptData(found);
                previewSpecificScene(0, 0.50);
            }
        }

        function applyScriptData(script) {
            currentScript = JSON.parse(JSON.stringify(script));
            document.getElementById('scriptBadge').innerText = script.name;
            document.getElementById('inputTopic').value = script.name;

            // Set up audio track UI if custom audio path is in script
            if (currentScript.custom_audio_path) {
                document.getElementById('badgeAudioTrackStatus').innerText = 'Audio Track Active';
                document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40';
                document.getElementById('labelAudioTrack').innerText = `Using master audio track: ${currentScript.custom_audio_path}`;
                document.getElementById('btnClearCustomAudio').classList.remove('hidden');
                const mPlayer = document.getElementById('masterAudioPlayer');
                mPlayer.src = currentScript.custom_audio_path;
                mPlayer.classList.remove('hidden');
            } else {
                clearCustomAudioTrack();
            }

            updateAudioButtonsUi();
            renderSceneTabs();
            renderSceneCards();
        }

        // 3. Render Dynamic Scene Switcher Tabs
        function renderSceneTabs() {
            const container = document.getElementById('sceneTabsContainer');
            if (!container || !currentScript) return;
            container.innerHTML = '';

            const scenes = currentScript.scenes || [];
            scenes.forEach((s, idx) => {
                const btn = document.createElement('button');
                const isActive = (idx === activeSceneIndex);
                btn.className = `scene-tab px-3 py-1 rounded-lg text-xs font-medium transition-colors flex-shrink-0 cursor-pointer ${
                    isActive 
                        ? 'text-white bg-brand-card border border-brand-accent ring-1 ring-brand-accent/50 shadow-md font-semibold' 
                        : 'text-gray-400 hover:text-white hover:bg-brand-surface/80 border border-transparent'
                }`;
                btn.innerText = `Scene ${idx + 1}`;
                btn.onclick = () => previewSpecificScene(idx);
                container.appendChild(btn);
            });

            // Add Scene Tab Button
            const addBtn = document.createElement('button');
            addBtn.className = 'scene-tab px-2.5 py-1 rounded-lg text-brand-cyan hover:text-white hover:bg-brand-card font-medium transition-colors text-xs flex items-center space-x-1 flex-shrink-0 cursor-pointer border border-transparent';
            addBtn.innerHTML = '<i data-lucide="plus" class="w-3 h-3"></i><span>Scene</span>';
            addBtn.onclick = () => addNewScene();
            container.appendChild(addBtn);

            // Video Player Tab Button
            const vidTab = document.createElement('button');
            vidTab.id = 'tabVideoPlayer';
            const isVidActive = (activeSceneIndex === -1);
            vidTab.className = `scene-tab px-3 py-1 rounded-lg font-medium transition-colors text-xs flex-shrink-0 cursor-pointer ${
                isVidActive
                    ? 'text-white bg-brand-card border border-brand-green ring-1 ring-brand-green/50 shadow-md font-semibold'
                    : 'text-brand-green hover:text-white hover:bg-brand-surface/80 border border-transparent'
            }`;
            vidTab.innerText = 'Video Player';
            vidTab.onclick = () => switchToVideoPlayerTab();
            container.appendChild(vidTab);

            lucide.createIcons();
        }

        // 4. Render Scene Cards & Item Choreography
        function renderSceneCards() {
            const container = document.getElementById('scenesContainer');
            if (!container || !currentScript) return;
            container.innerHTML = '';

            const scenes = currentScript.scenes || [];
            scenes.forEach((s, idx) => {
                const card = document.createElement('div');
                card.id = `sceneCard_${idx}`;
                card.className = `p-4 rounded-xl border transition-all ${idx === activeSceneIndex ? 'bg-brand-surface border-brand-accent ring-1 ring-brand-accent/40 shadow-lg' : 'bg-brand-surface/70 border-brand-border hover:border-gray-600'}`;

                // Items list markup
                let itemsListHtml = '';
                const items = s.items || [];
                if (items.length === 0) {
                    itemsListHtml = `<p class="text-xs text-gray-500 italic p-2">No visual items defined yet. Click "+ Add Item" below to add images, text, or badges!</p>`;
                } else {
                    items.forEach((item, itemIdx) => {
                        let typeIcon = 'layers';
                        let typeColor = 'text-brand-cyan';
                        if (item.type === 'text') { typeIcon = 'type'; typeColor = 'text-brand-green'; }
                        else if (item.type === 'badge') { typeIcon = 'shield'; typeColor = 'text-amber-400'; }
                        else if (item.type === 'arrows') { typeIcon = 'chevrons-up'; typeColor = 'text-brand-green'; }

                        const entryDir = item.entry_direction || 'left';
                        const exitDir = item.exit_direction || entryDir;

                        itemsListHtml += `
                            <div class="p-2.5 rounded-lg bg-brand-card/70 border border-brand-border text-xs space-y-2">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center space-x-2 truncate">
                                        <i data-lucide="${typeIcon}" class="w-3.5 h-3.5 ${typeColor} flex-shrink-0"></i>
                                        <input type="text" value="${item.name || ('Item ' + (itemIdx + 1))}" oninput="updateItemField(${idx}, ${itemIdx}, 'name', this.value)" class="bg-transparent border-b border-transparent hover:border-gray-600 focus:border-brand-accent text-xs font-medium text-white px-1 py-0.5 focus:outline-none truncate max-w-[160px]">
                                        <span class="text-[10px] font-mono text-gray-400 bg-brand-surface px-1.5 py-0.5 rounded border border-brand-border">${Math.round((item.start_t || 0) * 100)}% - ${Math.round((item.end_t || 1.0) * 100)}%</span>
                                    </div>
                                    <div class="flex items-center space-x-1 flex-shrink-0">
                                        <button onclick="toggleItemDrawer(${idx}, ${itemIdx})" title="Configure position & appearance" class="text-gray-400 hover:text-white p-1">
                                            <i data-lucide="settings" class="w-3.5 h-3.5"></i>
                                        </button>
                                        <button onclick="duplicateItemInScene(${idx}, ${itemIdx})" title="Duplicate item" class="text-gray-400 hover:text-brand-cyan p-1">
                                            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                                        </button>
                                        <button onclick="deleteItemFromScene(${idx}, ${itemIdx})" title="Delete item" class="text-gray-400 hover:text-red-400 p-1">
                                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                                        </button>
                                    </div>
                                </div>

                                <!-- Direct Direction Controls (Appear From & Exit To) -->
                                <div class="grid grid-cols-2 gap-2 pt-1 border-t border-brand-border/40">
                                    <div>
                                        <label class="block text-[10px] text-gray-400 mb-0.5">Appears From:</label>
                                        <select onchange="updateItemField(${idx}, ${itemIdx}, 'entry_direction', this.value, true)" class="w-full bg-brand-surface border border-brand-border rounded-lg px-2 py-1 text-[11px] text-white">
                                            <option value="left" ${entryDir === 'left' ? 'selected' : ''}>⬅️ Left Side</option>
                                            <option value="right" ${entryDir === 'right' ? 'selected' : ''}>➡️ Right Side</option>
                                            <option value="top" ${entryDir === 'top' ? 'selected' : ''}>⬆️ Top Side</option>
                                            <option value="bottom" ${entryDir === 'bottom' ? 'selected' : ''}>⬇️ Bottom Side</option>
                                            <option value="zoom" ${entryDir === 'zoom' ? 'selected' : ''}>🔍 Zoom In Pop</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label class="block text-[10px] text-gray-400 mb-0.5">Exits To:</label>
                                        <select onchange="updateItemField(${idx}, ${itemIdx}, 'exit_direction', this.value, true)" class="w-full bg-brand-surface border border-brand-border rounded-lg px-2 py-1 text-[11px] text-white">
                                            <option value="left" ${exitDir === 'left' ? 'selected' : ''}>⬅️ Left Side</option>
                                            <option value="right" ${exitDir === 'right' ? 'selected' : ''}>➡️ Right Side</option>
                                            <option value="top" ${exitDir === 'top' ? 'selected' : ''}>⬆️ Top Side</option>
                                            <option value="bottom" ${exitDir === 'bottom' ? 'selected' : ''}>⬇️ Bottom Side</option>
                                            <option value="zoom" ${exitDir === 'zoom' ? 'selected' : ''}>🔍 Zoom Out</option>
                                            <option value="none" ${exitDir === 'none' ? 'selected' : ''}>⏹️ Hold (None)</option>
                                        </select>
                                    </div>
                                </div>

                                <!-- Expandable Item Details Drawer -->
                                <div id="itemDrawer_${idx}_${itemIdx}" class="hidden pt-2 border-t border-brand-border/40 space-y-2 bg-brand-surface/60 p-2 rounded-lg">
                                    ${renderItemSpecificDetails(idx, itemIdx, item)}
                                </div>
                            </div>
                        `;
                    });
                }

                card.innerHTML = `
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center space-x-2">
                            <div class="flex items-center space-x-2 cursor-pointer hover:opacity-80 transition-opacity" onclick="previewSpecificScene(${idx})" title="Click to view Scene ${idx + 1} in live preview">
                                <span class="w-5 h-5 rounded-full bg-brand-card flex items-center justify-center text-xs font-mono font-bold ${idx === activeSceneIndex ? 'text-brand-accent bg-brand-accent/20 ring-1 ring-brand-accent/60' : 'text-brand-cyan'}">${idx + 1}</span>
                                <span class="text-xs font-semibold ${idx === activeSceneIndex ? 'text-brand-cyan font-bold' : 'text-white'}">Scene ${idx + 1}</span>
                            </div>
                            <div class="flex items-center space-x-1 bg-brand-card border border-brand-border px-1.5 py-0.5 rounded" title="Edit scene duration in seconds">
                                <input type="number" step="0.5" min="1.0" max="25.0" value="${(s.duration || 4.0)}" onchange="updateSceneDuration(${idx}, parseFloat(this.value))" class="w-9 bg-transparent text-[11px] font-mono text-brand-cyan focus:text-white focus:outline-none text-right">
                                <span class="text-[10px] text-gray-400 font-mono">s</span>
                            </div>
                        </div>
                        <div class="flex items-center space-x-1.5">
                            <button onclick="duplicateScene(${idx})" title="Duplicate scene" class="text-gray-400 hover:text-brand-cyan text-xs p-1">
                                <i data-lucide="copy" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="deleteScene(${idx})" title="Delete scene" class="text-gray-400 hover:text-red-400 text-xs p-1">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="previewSpecificScene(${idx})" class="text-xs text-brand-cyan hover:underline flex items-center space-x-1 ml-1">
                                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
                                <span>Preview</span>
                            </button>
                        </div>
                    </div>

                    <!-- Voiceover & Caption Inputs -->
                    <div class="space-y-2 text-xs">
                        <div>
                            <label class="text-[11px] text-gray-400">Voiceover Narration</label>
                            <textarea rows="2" oninput="updateSceneField(${idx}, 'voice_text', this.value, false)" class="w-full bg-brand-card border border-brand-border rounded-lg px-2.5 py-1.5 text-xs text-white">${s.voice_text || ''}</textarea>
                        </div>

                        <!-- On-Screen Visual Items & Direction Choreography -->
                        <div class="p-3 rounded-xl bg-brand-card/50 border border-brand-border space-y-2.5">
                            <div class="flex flex-wrap items-center justify-between gap-1.5">
                                <div class="flex items-center space-x-1.5">
                                    <i data-lucide="layers" class="w-3.5 h-3.5 text-brand-cyan"></i>
                                    <span class="text-xs font-semibold text-white">Visual Items</span>
                                    <span class="text-[10px] font-mono bg-brand-cyan/20 text-brand-cyan px-2 py-0.2 rounded-full">${items.length} layers</span>
                                </div>
                                <div class="flex items-center space-x-1">
                                    <button onclick="addItemToScene(${idx}, 'card')" class="text-[11px] bg-brand-cyan/20 hover:bg-brand-cyan/30 border border-brand-cyan/40 text-brand-cyan px-2 py-0.5 rounded-lg flex items-center space-x-1 font-medium transition-colors">
                                        <i data-lucide="plus" class="w-3 h-3"></i>
                                        <span>Card/Image</span>
                                    </button>
                                    <button onclick="addItemToScene(${idx}, 'text')" class="text-[11px] bg-brand-green/20 hover:bg-brand-green/30 border border-brand-green/40 text-brand-green px-2 py-0.5 rounded-lg flex items-center space-x-1 font-medium transition-colors">
                                        <i data-lucide="plus" class="w-3 h-3"></i>
                                        <span>Text</span>
                                    </button>
                                    <button onclick="addItemToScene(${idx}, 'badge')" class="text-[11px] bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-300 px-2 py-0.5 rounded-lg flex items-center space-x-1 font-medium transition-colors">
                                        <i data-lucide="shield" class="w-3 h-3"></i>
                                        <span>Badge</span>
                                    </button>
                                    <button onclick="addItemToScene(${idx}, 'arrows')" class="text-[11px] bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 px-2 py-0.5 rounded-lg flex items-center space-x-1 font-medium transition-colors">
                                        <i data-lucide="chevrons-up" class="w-3 h-3"></i>
                                        <span>Arrows</span>
                                    </button>
                                </div>
                            </div>

                            <div class="space-y-2">
                                ${itemsListHtml}
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(card);
            });
            lucide.createIcons();
        }

        // 5. Render Item Details Drawer (Sliders, Presets & Uploads)
        function renderItemSpecificDetails(sceneIdx, itemIdx, item) {
            let specificControls = '';
            if (item.type === 'card' || item.type === 'image') {
                specificControls = `
                    <div class="space-y-2">
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[10px] text-gray-400 mb-0.5">Asset Preset</label>
                                <select onchange="updateItemField(${sceneIdx}, ${itemIdx}, 'asset', this.value, true)" class="w-full bg-brand-card border border-brand-border rounded-lg px-2 py-1 text-[11px] text-white">
                                    <option value="tradeit_homepage_card.jpg" ${item.asset === 'tradeit_homepage_card.jpg' ? 'selected' : ''}>TradeIt Homepage Card</option>
                                    <option value="tradeit_dropdown_menu.jpg" ${item.asset === 'tradeit_dropdown_menu.jpg' ? 'selected' : ''}>TradeIt Dropdown Menu</option>
                                    <option value="tradeit_modal_raw.jpg" ${item.asset === 'tradeit_modal_raw.jpg' ? 'selected' : ''}>TradeIt Redeem Modal (Live Typing)</option>
                                    <option value="tradeit_header_toast.jpg" ${item.asset === 'tradeit_header_toast.jpg' ? 'selected' : ''}>Balance Toast Header</option>
                                    <option value="tradeit_item_grid.jpg" ${item.asset === 'tradeit_item_grid.jpg' ? 'selected' : ''}>CS2 Skins Grid</option>
                                    <option value="tradeit_floating_skins.jpg" ${item.asset === 'tradeit_floating_skins.jpg' ? 'selected' : ''}>3 Floating Dream Weapons</option>
                                    <option value="steam_proceed_stop.jpg" ${item.asset === 'steam_proceed_stop.jpg' ? 'selected' : ''}>Steam Proceed & STOP</option>
                                    <option value="missing_item_bar.jpg" ${item.asset === 'missing_item_bar.jpg' ? 'selected' : ''}>Missing Item Bar</option>
                                    <option value="steam_inventory_5x5.jpg" ${item.asset === 'steam_inventory_5x5.jpg' ? 'selected' : ''}>Steam 5x5 Inventory Grid</option>
                                    <option value="cs2_trade_badge.jpg" ${item.asset === 'cs2_trade_badge.jpg' ? 'selected' : ''}>CS2 Handshake Badge</option>
                                    <option value="prohibition_badge.jpg" ${item.asset === 'prohibition_badge.jpg' ? 'selected' : ''}>Prohibition Badge</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-[10px] text-gray-400 mb-0.5">Or Upload Custom Image</label>
                                <input type="file" accept="image/*" onchange="handleItemImageUpload(${sceneIdx}, ${itemIdx}, this)" class="w-full text-[10px] text-gray-400 file:mr-1.5 file:py-0.5 file:px-2 file:rounded file:border-0 file:text-[10px] file:bg-brand-card file:text-brand-cyan hover:file:bg-brand-border cursor-pointer">
                            </div>
                        </div>
                    </div>
                `;
            } else if (item.type === 'text') {
                const hlColor = rgbToHex(item.highlight_color || [0, 255, 65]);
                specificControls = `
                    <div class="space-y-2">
                        <div class="grid grid-cols-1 sm:grid-cols-12 gap-2">
                            <div class="sm:col-span-8">
                                <label class="block text-[10px] text-gray-400 mb-0.5">Caption Text ({code} supported)</label>
                                <input type="text" value="${item.text || ''}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'text', this.value, true)" class="w-full bg-brand-card border border-brand-border rounded-lg px-2 py-1 text-xs text-white">
                            </div>
                            <div class="sm:col-span-4">
                                <label class="block text-[10px] text-gray-400 mb-0.5">Highlight Word</label>
                                <input type="text" value="${item.highlight_word || ''}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'highlight_word', this.value, true)" class="w-full bg-brand-card border border-brand-border rounded-lg px-2 py-1 text-xs text-brand-cyan font-mono">
                            </div>
                        </div>
                        <div class="flex items-center space-x-3 text-[10px] text-gray-400">
                            <span>Font Size:</span>
                            <input type="range" min="50" max="130" step="2" value="${item.font_size || 84}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'font_size', parseInt(this.value), true)" class="w-24">
                            <span>Color:</span>
                            <input type="color" value="${hlColor}" onchange="updateItemHighlightColor(${sceneIdx}, ${itemIdx}, this.value)" class="w-4 h-4 rounded cursor-pointer border-0 p-0 bg-transparent">
                        </div>
                    </div>
                `;
            } else if (item.type === 'badge') {
                specificControls = `
                    <div>
                        <label class="block text-[10px] text-gray-400 mb-0.5">Badge Asset</label>
                        <select onchange="updateItemField(${sceneIdx}, ${itemIdx}, 'asset', this.value, true)" class="w-full bg-brand-card border border-brand-border rounded-lg px-2 py-1 text-[11px] text-white">
                            <option value="prohibition_badge.jpg" ${item.asset === 'prohibition_badge.jpg' ? 'selected' : ''}>Prohibition Sign (🚫)</option>
                            <option value="cs2_trade_badge.jpg" ${item.asset === 'cs2_trade_badge.jpg' ? 'selected' : ''}>CS2 Handshake Badge (🤝)</option>
                        </select>
                    </div>
                `;
            }

            // Universal timing, position & scale sliders
            return `
                ${specificControls}
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 border-t border-brand-border/40 text-[10px] text-gray-400">
                    <div>
                        <div class="flex justify-between"><span>X Pos</span><span>${Math.round((item.x_pct || 0.5) * 100)}%</span></div>
                        <input type="range" min="0.10" max="0.90" step="0.02" value="${item.x_pct || 0.5}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'x_pct', parseFloat(this.value), true)" class="w-full">
                    </div>
                    <div>
                        <div class="flex justify-between"><span>Y Pos</span><span>${Math.round((item.y_pct || 0.5) * 100)}%</span></div>
                        <input type="range" min="0.08" max="0.92" step="0.02" value="${item.y_pct || 0.5}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'y_pct', parseFloat(this.value), true)" class="w-full">
                    </div>
                    <div>
                        <div class="flex justify-between"><span>Scale</span><span>${(item.scale || 1.0).toFixed(2)}x</span></div>
                        <input type="range" min="0.5" max="1.5" step="0.05" value="${item.scale || 1.0}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'scale', parseFloat(this.value), true)" class="w-full">
                    </div>
                    <div>
                        <div class="flex justify-between"><span>Tilt</span><span>${item.max_tilt_deg || 0}°</span></div>
                        <input type="range" min="-8" max="8" step="0.5" value="${item.max_tilt_deg || 0}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'max_tilt_deg', parseFloat(this.value), true)" class="w-full">
                    </div>
                </div>
                <div class="grid grid-cols-2 gap-2 text-[10px] text-gray-400">
                    <div>
                        <div class="flex justify-between"><span>Active Start %</span><span>${Math.round((item.start_t || 0) * 100)}%</span></div>
                        <input type="range" min="0.0" max="0.9" step="0.05" value="${item.start_t || 0.0}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'start_t', parseFloat(this.value), true)" class="w-full">
                    </div>
                    <div>
                        <div class="flex justify-between"><span>Active End %</span><span>${Math.round((item.end_t || 1.0) * 100)}%</span></div>
                        <input type="range" min="0.1" max="1.0" step="0.05" value="${item.end_t || 1.0}" oninput="updateItemField(${sceneIdx}, ${itemIdx}, 'end_t', parseFloat(this.value), true)" class="w-full">
                    </div>
                </div>
            `;
        }

        function toggleItemDrawer(sceneIdx, itemIdx) {
            const el = document.getElementById(`itemDrawer_${sceneIdx}_${itemIdx}`);
            if (el) el.classList.toggle('hidden');
        }

        // 6. Item Field Updates
        function updateItemField(sceneIdx, itemIdx, field, val, triggerPreview = false) {
            if (currentScript && currentScript.scenes[sceneIdx] && currentScript.scenes[sceneIdx].items[itemIdx]) {
                currentScript.scenes[sceneIdx].items[itemIdx][field] = val;
                if (triggerPreview) {
                    debouncePreview(sceneIdx);
                }
            }
        }

        function updateItemHighlightColor(sceneIdx, itemIdx, hexVal) {
            const rgb = hexToRgb(hexVal);
            updateItemField(sceneIdx, itemIdx, 'highlight_color', rgb, true);
        }

        async function handleItemImageUpload(sceneIdx, itemIdx, inputElem) {
            if (!inputElem.files || !inputElem.files[0]) return;
            const file = inputElem.files[0];
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.url) {
                    currentScript.scenes[sceneIdx].items[itemIdx].image_path = data.url;
                    renderSceneCards();
                    previewSpecificScene(sceneIdx);
                }
            } catch (err) {
                alert('Image upload failed: ' + err.message);
            }
        }

        function addItemToScene(sceneIdx, type = 'card') {
            if (!currentScript || !currentScript.scenes[sceneIdx]) return;
            if (!currentScript.scenes[sceneIdx].items) {
                currentScript.scenes[sceneIdx].items = [];
            }
            const newId = 'item_' + Date.now();
            let newItem = {};
            if (type === 'text') {
                newItem = {
                    id: newId,
                    name: 'New Text Line',
                    type: 'text',
                    text: 'New Highlighted Text',
                    highlight_word: 'Highlighted',
                    highlight_color: [0, 255, 65],
                    text_color: [255, 255, 255],
                    font_size: 84,
                    font_style: 'serif_italic',
                    entry_direction: 'left',
                    exit_direction: 'left',
                    x_pct: 0.50,
                    y_pct: 0.20,
                    start_t: 0.0,
                    end_t: 1.0,
                    slide_distance: 500,
                    max_tilt_deg: 2.2
                };
            } else if (type === 'badge') {
                newItem = {
                    id: newId,
                    name: 'Prohibition Badge',
                    type: 'badge',
                    asset: 'prohibition_badge.jpg',
                    entry_direction: 'zoom',
                    exit_direction: 'zoom',
                    x_pct: 0.50,
                    y_pct: 0.50,
                    scale: 0.85,
                    start_t: 0.0,
                    end_t: 1.0,
                    slide_distance: 600,
                    max_tilt_deg: 0.0
                };
            } else if (type === 'arrows') {
                newItem = {
                    id: newId,
                    name: 'Upgrade Arrows Particles',
                    type: 'arrows',
                    entry_direction: 'bottom',
                    exit_direction: 'top',
                    x_pct: 0.50,
                    y_pct: 0.50,
                    scale: 1.0,
                    start_t: 0.0,
                    end_t: 1.0
                };
            } else {
                newItem = {
                    id: newId,
                    name: 'Custom Image Card',
                    type: 'card',
                    asset: 'tradeit_homepage_card.jpg',
                    image_path: '',
                    entry_direction: 'left',
                    exit_direction: 'right',
                    x_pct: 0.50,
                    y_pct: 0.50,
                    scale: 1.0,
                    start_t: 0.0,
                    end_t: 1.0,
                    slide_distance: 850,
                    max_tilt_deg: 3.5
                };
            }
            currentScript.scenes[sceneIdx].items.push(newItem);
            renderSceneCards();
            previewSpecificScene(sceneIdx);
        }

        function deleteItemFromScene(sceneIdx, itemIdx) {
            if (confirm('Delete this visual item from the screen?')) {
                currentScript.scenes[sceneIdx].items.splice(itemIdx, 1);
                renderSceneCards();
                previewSpecificScene(sceneIdx);
            }
        }

        function duplicateItemInScene(sceneIdx, itemIdx) {
            const item = currentScript.scenes[sceneIdx].items[itemIdx];
            const copy = JSON.parse(JSON.stringify(item));
            copy.id = 'item_' + Date.now();
            copy.name = (copy.name || 'Item') + ' (Copy)';
            currentScript.scenes[sceneIdx].items.splice(itemIdx + 1, 0, copy);
            renderSceneCards();
            previewSpecificScene(sceneIdx);
        }

        // 7. Scene Management (Add, Delete, Duplicate)
        function addNewScene() {
            if (!currentScript) return;
            if (!currentScript.scenes) currentScript.scenes = [];
            const newSceneNum = currentScript.scenes.length + 1;
            const newScene = {
                scene_num: newSceneNum,
                theme: currentScript.theme || 'tradeit',
                promocode: currentScript.promocode || 'MESTO300',
                duration: 4.0,
                caption: `Scene ${newSceneNum} Title`,
                caption_highlight: 'Title',
                highlight_color: [0, 255, 65],
                voice_text: `Scene ${newSceneNum} narration voiceover description.`,
                items: [
                    {
                        id: `s${newSceneNum}_card`,
                        name: 'Hero Card',
                        type: 'card',
                        asset: 'tradeit_homepage_card.jpg',
                        image_path: '',
                        entry_direction: 'left',
                        exit_direction: 'right',
                        x_pct: 0.50,
                        y_pct: 0.50,
                        scale: 1.0,
                        start_t: 0.0,
                        end_t: 1.0,
                        slide_distance: 850,
                        max_tilt_deg: 3.5
                    },
                    {
                        id: `s${newSceneNum}_txt`,
                        name: 'Top Caption',
                        type: 'text',
                        text: `Scene ${newSceneNum} Title`,
                        highlight_word: 'Title',
                        highlight_color: [0, 255, 65],
                        text_color: [255, 255, 255],
                        font_size: 84,
                        font_style: 'serif_italic',
                        entry_direction: 'left',
                        exit_direction: 'left',
                        x_pct: 0.50,
                        y_pct: 0.12,
                        start_t: 0.0,
                        end_t: 1.0,
                        slide_distance: 500,
                        max_tilt_deg: 2.2
                    }
                ]
            };
            currentScript.scenes.push(newScene);
            renderSceneTabs();
            renderSceneCards();
            previewSpecificScene(currentScript.scenes.length - 1, 0.50);
        }

        function deleteScene(sceneIdx) {
            if (currentScript.scenes.length <= 1) {
                alert('A storyboard must have at least one scene.');
                return;
            }
            if (confirm(`Delete Scene ${sceneIdx + 1}?`)) {
                currentScript.scenes.splice(sceneIdx, 1);
                currentScript.scenes.forEach((s, i) => s.scene_num = i + 1);
                activeSceneIndex = Math.min(activeSceneIndex, currentScript.scenes.length - 1);
                renderSceneTabs();
                renderSceneCards();
                previewSpecificScene(activeSceneIndex, 0.50);
            }
        }

        function duplicateScene(sceneIdx) {
            const s = currentScript.scenes[sceneIdx];
            const copy = JSON.parse(JSON.stringify(s));
            copy.scene_num = currentScript.scenes.length + 1;
            currentScript.scenes.splice(sceneIdx + 1, 0, copy);
            currentScript.scenes.forEach((sc, i) => sc.scene_num = i + 1);
            renderSceneTabs();
            renderSceneCards();
            previewSpecificScene(sceneIdx + 1, 0.50);
        }

        function updateSceneField(sceneIdx, field, val, triggerPreview = false) {
            if (currentScript && currentScript.scenes && currentScript.scenes[sceneIdx]) {
                currentScript.scenes[sceneIdx][field] = val;
                if (triggerPreview) debouncePreview(sceneIdx);
            }
        }

        function updateSceneDuration(sceneIdx, val) {
            if (currentScript && currentScript.scenes && currentScript.scenes[sceneIdx]) {
                currentScript.scenes[sceneIdx].duration = val;
                const scene = currentScript.scenes[activeSceneIndex];
                if (scene) {
                    document.getElementById('sceneDurMaxText').innerText = `${(scene.duration || 4.0).toFixed(1)}s`;
                }
            }
        }

        // 8. High-Performance Live Scrubber & Scene Preview Pipeline
        let isPreviewFetching = false;
        let pendingPreviewReq = null;
        let isScenePlaying = false;
        let scenePlaybackTimeout = null;

        function showPreviewIndicator(isLoading) {
            const spinner = document.getElementById('previewSpinner');
            const scrubSpinner = document.getElementById('scrubberSpinner');
            if (spinner) {
                if (isLoading) spinner.classList.remove('hidden');
                else spinner.classList.add('hidden');
            }
            if (scrubSpinner) {
                if (isLoading) scrubSpinner.classList.remove('hidden');
                else scrubSpinner.classList.add('hidden');
            }
        }

        function onScrubberMoved(val) {
            currentPreviewProgress = val;
            const scene = currentScript ? currentScript.scenes[activeSceneIndex] : null;
            const sceneDur = scene ? (scene.duration || 4.0) : 4.0;
            document.getElementById('scrubberTimeText').innerText = `${Math.round(val * 100)}% (${(val * sceneDur).toFixed(1)}s)`;
            
            // If playing, pause on manual scrub
            if (isScenePlaying) {
                toggleScenePlayback();
            }
            requestScenePreviewFrame(activeSceneIndex, currentPreviewProgress);
        }

        function requestScenePreviewFrame(idx, progress) {
            if (isPreviewFetching) {
                // Queue the latest requested position (skips intermediate dropped frames)
                pendingPreviewReq = { idx, progress };
                return;
            }
            fetchPreviewFrameDirect(idx, progress);
        }

        async function fetchPreviewFrameDirect(idx, progress) {
            isPreviewFetching = true;
            showPreviewIndicator(true);

            const scene = currentScript ? currentScript.scenes[idx] : null;
            if (!scene) {
                isPreviewFetching = false;
                showPreviewIndicator(false);
                return;
            }

            const sceneDur = scene.duration || 4.0;
            document.getElementById('previewLabel').innerText = `Scene ${idx + 1}: ${scene.caption || scene.voice_text || 'Preview'}`;

            try {
                const res = await fetch('/api/preview-scene', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        scene: scene,
                        progress: progress,
                        global_time: 1.5 + idx * 3.5 + progress * sceneDur,
                        width: 540,
                        height: 960
                    })
                });
                const data = await res.json();
                if (data.preview_url) {
                    const tempImg = new Image();
                    tempImg.onload = () => {
                        const img = document.getElementById('previewImage');
                        if (img) img.src = tempImg.src;
                    };
                    tempImg.src = data.preview_url + '?t=' + Date.now();
                }
            } catch (err) {
                console.warn('Preview frame notice:', err);
            } finally {
                isPreviewFetching = false;
                showPreviewIndicator(false);

                // If user scrubbed while this frame was rendering, immediately render the latest position
                if (pendingPreviewReq) {
                    const next = pendingPreviewReq;
                    pendingPreviewReq = null;
                    fetchPreviewFrameDirect(next.idx, next.progress);
                }
            }
        }

        async function runPlaybackLoop() {
            if (!isScenePlaying) return;
            const scene = currentScript ? currentScript.scenes[activeSceneIndex] : null;
            const sceneDur = scene ? (scene.duration || 4.0) : 4.0;

            currentPreviewProgress += 0.06;
            if (currentPreviewProgress > 1.0) {
                currentPreviewProgress = 0.04;
            }
            document.getElementById('sceneProgressScrubber').value = currentPreviewProgress;
            document.getElementById('scrubberTimeText').innerText = `${Math.round(currentPreviewProgress * 100)}% (${(currentPreviewProgress * sceneDur).toFixed(1)}s)`;

            await fetchPreviewFrameDirect(activeSceneIndex, currentPreviewProgress);

            if (isScenePlaying) {
                scenePlaybackTimeout = setTimeout(runPlaybackLoop, 50);
            }
        }

        function toggleScenePlayback() {
            const btn = document.getElementById('btnPlayScenePreview');
            if (isScenePlaying) {
                isScenePlaying = false;
                if (scenePlaybackTimeout) {
                    clearTimeout(scenePlaybackTimeout);
                    scenePlaybackTimeout = null;
                }
                document.getElementById('playIcon').setAttribute('data-lucide', 'play');
                if (btn) {
                    btn.className = 'w-7 h-7 rounded-lg bg-brand-card hover:bg-brand-border border border-brand-border text-brand-green flex items-center justify-center transition-colors flex-shrink-0 cursor-pointer';
                }
                lucide.createIcons();
            } else {
                isScenePlaying = true;
                document.getElementById('playIcon').setAttribute('data-lucide', 'pause');
                if (btn) {
                    btn.className = 'w-7 h-7 rounded-lg bg-brand-green/25 border border-brand-green ring-2 ring-brand-green/50 text-white flex items-center justify-center transition-all flex-shrink-0 cursor-pointer shadow-lg';
                }
                lucide.createIcons();
                runPlaybackLoop();
            }
        }

        function debouncePreview(idx) {
            clearTimeout(previewDebounceTimer);
            previewDebounceTimer = setTimeout(() => {
                previewSpecificScene(idx);
            }, 120);
        }

        async function previewSpecificScene(idx, progress = null) {
            activeSceneIndex = idx;
            if (progress !== null) {
                currentPreviewProgress = progress;
            }
            document.getElementById('sceneProgressScrubber').value = currentPreviewProgress;

            const scene = currentScript ? currentScript.scenes[idx] : null;
            if (!scene) return;

            const sceneDur = scene.duration || 4.0;
            document.getElementById('sceneDurMaxText').innerText = `${sceneDur.toFixed(1)}s`;
            document.getElementById('scrubberTimeText').innerText = `${Math.round(currentPreviewProgress * 100)}% (${(currentPreviewProgress * sceneDur).toFixed(1)}s)`;

            renderSceneTabs();

            // Update active styling on scene cards in storyboard
            if (currentScript && currentScript.scenes) {
                currentScript.scenes.forEach((_, sIdx) => {
                    const cEl = document.getElementById(`sceneCard_${sIdx}`);
                    if (cEl) {
                        if (sIdx === idx) {
                            cEl.className = 'p-4 rounded-xl border transition-all bg-brand-surface border-brand-accent ring-1 ring-brand-accent/40 shadow-lg';
                        } else {
                            cEl.className = 'p-4 rounded-xl border transition-all bg-brand-surface/70 border-brand-border hover:border-gray-600';
                        }
                    }
                });
            }

            document.getElementById('previewFrameContainer').classList.remove('hidden');
            document.getElementById('previewVideoContainer').classList.add('hidden');

            requestScenePreviewFrame(idx, currentPreviewProgress);
        }

        function refreshCurrentPreview() {
            fetchPreviewFrameDirect(activeSceneIndex, currentPreviewProgress);
        }

        function switchToVideoPlayerTab() {
            activeSceneIndex = -1;
            renderSceneTabs();
            // Unhighlight all scene cards in storyboard
            if (currentScript && currentScript.scenes) {
                currentScript.scenes.forEach((_, sIdx) => {
                    const cEl = document.getElementById(`sceneCard_${sIdx}`);
                    if (cEl) {
                        cEl.className = 'p-4 rounded-xl border transition-all bg-brand-surface/70 border-brand-border hover:border-gray-600';
                    }
                });
            }
            document.getElementById('previewFrameContainer').classList.add('hidden');
            document.getElementById('previewVideoContainer').classList.remove('hidden');
            document.getElementById('previewLabel').innerText = 'Rendered Short Video Player';
        }

        // 9. Master Audio Handlers
        function updateAudioButtonsUi() {
            const btnRef = document.getElementById('btnRefAudio');
            const btnUpload = document.getElementById('btnUploadAudio');
            if (!btnRef || !btnUpload) return;

            const path = currentScript ? currentScript.custom_audio_path : null;
            if (path && String(path).includes('ref_ad_audio')) {
                btnRef.className = 'text-xs bg-brand-cyan/25 border border-brand-cyan text-brand-cyan px-2.5 py-1.5 rounded-lg transition-all flex items-center space-x-1 ring-2 ring-brand-cyan/50 shadow-md font-semibold';
                btnUpload.className = 'text-xs bg-brand-surface hover:bg-brand-border border border-brand-border text-gray-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1 font-medium';
            } else if (path) {
                btnUpload.className = 'text-xs bg-brand-green/30 border border-brand-green text-brand-green px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1 font-semibold ring-2 ring-brand-green/50 shadow-md';
                btnRef.className = 'text-xs bg-brand-surface hover:bg-brand-border border border-brand-border text-gray-300 hover:text-white px-2.5 py-1.5 rounded-lg transition-colors flex items-center space-x-1 font-medium';
            } else {
                btnRef.className = 'text-xs bg-brand-surface hover:bg-brand-border border border-brand-border text-gray-300 hover:text-white px-2.5 py-1.5 rounded-lg transition-colors flex items-center space-x-1 font-medium';
                btnUpload.className = 'text-xs bg-brand-surface hover:bg-brand-border border border-brand-border text-gray-300 hover:text-white px-3 py-1.5 rounded-lg transition-colors flex items-center space-x-1 font-medium';
            }
        }

        async function handleCustomAudioUpload(inputEl) {
            if (!inputEl.files || !inputEl.files[0]) return;
            const file = inputEl.files[0];
            const formData = new FormData();
            formData.append('file', file);
            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.success) {
                    currentScript.custom_audio_path = data.local_path;
                    document.getElementById('badgeAudioTrackStatus').innerText = `User Audio (${data.duration ? data.duration.toFixed(1) + 's' : 'Active'})`;
                    document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-green/20 text-brand-green border border-brand-green/40';
                    document.getElementById('labelAudioTrack').innerText = `Loaded: ${file.name} • Master audio track`;
                    document.getElementById('btnClearCustomAudio').classList.remove('hidden');
                    const mPlayer = document.getElementById('masterAudioPlayer');
                    mPlayer.src = data.url;
                    mPlayer.classList.remove('hidden');
                    updateAudioButtonsUi();
                }
            } catch (err) {
                alert('Audio upload failed: ' + err.message);
            }
        }

        function useReferenceAdAudio() {
            if (!currentScript) return;
            currentScript.custom_audio_path = '/assets/cache/ref_ad_audio.wav';
            document.getElementById('badgeAudioTrackStatus').innerText = 'Ref Ad Audio (28.0s)';
            document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40';
            document.getElementById('labelAudioTrack').innerText = 'Using authentic reference ad audio & beat (ready (2).mp4)';
            document.getElementById('btnClearCustomAudio').classList.remove('hidden');
            const mPlayer = document.getElementById('masterAudioPlayer');
            mPlayer.src = '/assets/cache/ref_ad_audio.wav';
            mPlayer.classList.remove('hidden');
            updateAudioButtonsUi();
        }

        function clearCustomAudioTrack() {
            if (!currentScript) return;
            delete currentScript.custom_audio_path;
            document.getElementById('badgeAudioTrackStatus').innerText = 'TTS Mode';
            document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
            document.getElementById('labelAudioTrack').innerText = 'Upload user voice recording, ElevenLabs audio, or use reference track';
            document.getElementById('btnClearCustomAudio').classList.add('hidden');
            const mPlayer = document.getElementById('masterAudioPlayer');
            mPlayer.pause();
            mPlayer.src = '';
            mPlayer.classList.add('hidden');
            updateAudioButtonsUi();
        }

        function onVoiceChanged(val) {
            if (val.startsWith('eleven_')) {
                document.getElementById('badgeAudioTrackStatus').innerText = 'ElevenLabs Mode';
                document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
            } else {
                document.getElementById('badgeAudioTrackStatus').innerText = 'Edge-TTS Mode';
                document.getElementById('badgeAudioTrackStatus').className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30';
            }
        }

        function updateAudioVol(badgeId, val, isPct) {
            const badge = document.getElementById(badgeId);
            if (badge) {
                badge.innerText = isPct ? Math.round(val * 100) + '%' : val;
            }
        }

        // 10. AI Script Generation
        async function generateScript() {
            const topic = document.getElementById('inputTopic').value.trim();
            const product = document.getElementById('inputProductName').value.trim();
            if (!topic) {
                alert('Please enter a topic or problem first.');
                return;
            }

            const btn = document.getElementById('btnGenerateScript');
            btn.disabled = true;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Writing Script...</span>`;
            lucide.createIcons();

            try {
                const res = await fetch('/api/generate-script', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        topic: topic,
                        product_name: product || 'SmartApp'
                    })
                });
                const data = await res.json();
                if (data.script) {
                    activePresetId = null;
                    renderPresetButtons(null);
                    applyScriptData(data.script);
                    previewSpecificScene(0, 0.50);
                }
            } catch (err) {
                alert('Script generation failed: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Generate Script</span>`;
                lucide.createIcons();
            }
        }

        // 11. Test Voice Narration
        async function testVoicePreview() {
            if (!currentScript || !currentScript.scenes) return;
            const fullVoiceText = currentScript.scenes.map(s => s.voice_text || '').join(' ');
            const voice = document.getElementById('voiceSelect').value;

            const btn = document.getElementById('btnTestVoice');
            btn.disabled = true;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-brand-green"></i><span>Synthesizing...</span>`;
            lucide.createIcons();

            try {
                const res = await fetch('/api/preview-voice', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text: fullVoiceText.slice(0, 200) + '...',
                        voice: voice
                    })
                });
                const data = await res.json();
                if (data.audio_url) {
                    const playerContainer = document.getElementById('voiceAudioPlayerContainer');
                    const player = document.getElementById('voiceAudioPlayer');
                    player.src = data.audio_url;
                    playerContainer.classList.remove('hidden');
                    player.play();
                }
            } catch (err) {
                alert('Voice preview failed: ' + err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i data-lucide="volume-2" class="w-4 h-4 text-brand-green"></i><span>Test Narration Voice</span>`;
                lucide.createIcons();
            }
        }

        // 12. Full Video Render via SSE Stream
        async function startFullVideoRender() {
            if (!currentScript || !currentScript.scenes) {
                alert('No script loaded to render.');
                return;
            }

            const btn = document.getElementById('btnRenderVideo');
            const progressBox = document.getElementById('renderProgressBox');
            const successBox = document.getElementById('renderSuccessBox');
            const statusText = document.getElementById('renderStatusText');
            const percentText = document.getElementById('renderPercentText');
            const progressBar = document.getElementById('renderProgressBar');

            btn.disabled = true;
            btn.classList.add('opacity-50');
            progressBox.classList.remove('hidden');
            successBox.classList.add('hidden');
            progressBar.style.width = '3%';
            percentText.innerText = '3%';
            statusText.innerText = 'Starting video render job...';

            const fpsVal = parseInt(document.getElementById('fpsSelect').value) || 30;
            const voiceVal = document.getElementById('voiceSelect').value;
            const sfxVal = document.getElementById('chkWhoosh').checked;
            const musicVal = document.getElementById('chkMusic').checked;

            const voiceVol = parseFloat(document.getElementById('sliderVoiceVol').value) || 1.0;
            const musicVol = parseFloat(document.getElementById('sliderMusicVol').value) || 0.18;
            const sfxVol = parseFloat(document.getElementById('sliderSfxVol').value) || 0.8;

            try {
                const res = await fetch('/api/render-short', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        script_data: currentScript,
                        voice_id: voiceVal,
                        fps: fpsVal,
                        include_sfx: sfxVal,
                        include_music: musicVal,
                        voice_volume: voiceVol,
                        music_volume: musicVol,
                        sfx_volume: sfxVol,
                    })
                });
                const data = await res.json();
                const jobId = data.job_id;

                const evtSource = new EventSource(`/api/render-stream/${jobId}`);
                evtSource.onmessage = (e) => {
                    const evt = JSON.parse(e.data);
                    const pct = Math.round(evt.progress * 100);
                    progressBar.style.width = pct + '%';
                    percentText.innerText = pct + '%';
                    statusText.innerText = evt.message || 'Processing...';

                    if (evt.status === 'completed') {
                        evtSource.close();
                        btn.disabled = false;
                        btn.classList.remove('opacity-50');
                        progressBox.classList.add('hidden');
                        successBox.classList.remove('hidden');

                        if (evt.result && evt.result.video_url) {
                            document.getElementById('btnDownloadShort').href = evt.result.video_url;
                            document.getElementById('renderDetailsText').innerText = 
                                `${evt.result.resolution} • ${evt.result.fps}fps • ${evt.result.duration}s • File: ${evt.result.filename}`;

                            const vidPlayer = document.getElementById('finalVideoPlayer');
                            vidPlayer.src = evt.result.video_url;
                            switchToVideoPlayerTab();
                            vidPlayer.play().catch(() => {});
                        }

                        loadOutputsLibrary();
                    } else if (evt.status === 'failed') {
                        evtSource.close();
                        btn.disabled = false;
                        btn.classList.remove('opacity-50');
                        statusText.innerText = 'Render failed: ' + evt.error;
                        statusText.className = 'text-brand-red font-medium';
                    }
                };

                evtSource.onerror = () => {
                    evtSource.close();
                    btn.disabled = false;
                    btn.classList.remove('opacity-50');
                };

            } catch (err) {
                alert('Render failed to start: ' + err.message);
                btn.disabled = false;
                btn.classList.remove('opacity-50');
                progressBox.classList.add('hidden');
            }
        }

        // 13. Output Library
        async function loadOutputsLibrary() {
            try {
                const res = await fetch('/api/outputs');
                const data = await res.json();
                const container = document.getElementById('outputsList');
                if (!data.videos || data.videos.length === 0) {
                    container.innerHTML = '<p class="text-xs text-gray-500 italic">No rendered videos yet.</p>';
                    return;
                }
                container.innerHTML = '';
                data.videos.forEach(v => {
                    const item = document.createElement('div');
                    item.className = 'flex items-center justify-between p-2 rounded-lg bg-brand-surface border border-brand-border text-xs';
                    item.innerHTML = `
                        <div class="flex items-center space-x-2 truncate pr-2">
                            <i data-lucide="video" class="w-3.5 h-3.5 text-brand-cyan flex-shrink-0"></i>
                            <span class="truncate text-gray-200 font-mono text-[11px]">${v.filename}</span>
                        </div>
                        <div class="flex items-center space-x-2 flex-shrink-0">
                            <span class="text-[10px] text-gray-400 font-mono">${v.size_mb} MB</span>
                            <button onclick="playExistingVideo('${v.url}')" class="text-brand-cyan hover:underline text-[11px]">Play</button>
                            <a href="${v.url}" download class="text-brand-green hover:underline text-[11px]">Download</a>
                        </div>
                    `;
                    container.appendChild(item);
                });
                lucide.createIcons();
            } catch (err) {
                console.warn('Failed to load outputs library:', err);
            }
        }

        function playExistingVideo(url) {
            const vidPlayer = document.getElementById('finalVideoPlayer');
            vidPlayer.src = url;
            switchToVideoPlayerTab();
            vidPlayer.play().catch(() => {});
        }

        // Color conversion helpers
        function rgbToHex(rgbArr) {
            if (!rgbArr || rgbArr.length < 3) return '#00ff55';
            return '#' + rgbArr.slice(0, 3).map(x => {
                const hex = Math.min(255, Math.max(0, x)).toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            }).join('');
        }

        function hexToRgb(hex) {
            hex = hex.replace('#', '');
            if (hex.length === 3) {
                hex = hex.split('').map(c => c + c).join('');
            }
            const num = parseInt(hex, 16);
            return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
        }
