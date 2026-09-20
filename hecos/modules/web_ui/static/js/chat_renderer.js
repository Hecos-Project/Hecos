// chat_renderer.js
// Handles DOM manipulation, Markdown parsing, and UI Bubble logic

window.currentAudio = null;

// Initialize reasoning display defaults EARLY so renderThinkBlock is never
// skipped due to a race condition with the /hecos/status poll.
// The status poll will override these values once it resolves.
if (window.HecosShowReasoning === undefined)      window.HecosShowReasoning      = true;
if (window.HecosReasoningCollapsed === undefined)  window.HecosReasoningCollapsed = true;

function addBubble(role, text, id, opts) {
  const isUser = role === 'user';
  const msg = document.createElement('div');
  msg.className = `msg ${isUser?'user':'ai'}`;
  if(id) msg.id = id;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar`;
  
  if (isUser) {
    const usrSrc = window.HecosUserAvatar;
    if (usrSrc) {
        avatar.innerHTML = `
        <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="window.openAvatarFull('${usrSrc}')">
          <img src="${usrSrc}" style="width:100%; height:100%; object-fit:cover; border-radius:50%;" onerror="this.outerHTML='<i class=\'fas fa-user\'></i>'">
          <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
        </div>`;
    } else {
        avatar.innerHTML = '<i class="fas fa-user"></i>';
    }
  } else {
    const defaultAvatarSrc = window.HecosAvatar || "/assets/Hecos_Logo_SQR_NBG_LogoOnly.png";
    // Use the persona_name snapshot frozen at message-write time (if available), else current avatar
    const personaForAvatar = (opts && opts.persona_name) ? opts.persona_name : null;

    const renderAvatar = (avatarSrc) => {
      const imgStyle = avatarSrc !== "/assets/Hecos_Logo_SQR_NBG_LogoOnly.png"
        ? "object-fit:cover; border-radius:50%;"
        : "filter:drop-shadow(0 0 5px rgba(108,140,255,0.4));";
      avatar.innerHTML = `
        <div class="avatar-zoom-wrapper" style="width:100%; height:100%; display:flex; align-items:center; justify-content:center;" onclick="window.openAvatarFull('${avatarSrc}')">
          <img src="${avatarSrc}" onerror="this.src='/assets/Hecos_Logo_SQR_NBG_LogoOnly.png';" style="${imgStyle}">
          <div class="avatar-zoom-icon"><i class="fas fa-search-plus"></i></div>
        </div>`;
    };

    if (personaForAvatar) {
      // Start with current avatar, then async-update to the frozen persona avatar
      renderAvatar(defaultAvatarSrc);
      fetch(`/api/persona/avatar?persona=${encodeURIComponent(personaForAvatar)}`)
        .then(r => r.json())
        .then(d => { if (d.ok && d.avatar_path) renderAvatar(d.avatar_path); })
        .catch(() => {});
    } else {
      renderAvatar(defaultAvatarSrc);
    }
  }
  
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-content-wrapper';

  const header = document.createElement('div');
  header.className = 'msg-header';

  const nameEl = document.createElement('span');
  nameEl.className = 'msg-name';
  if (isUser) {
    nameEl.textContent = window.HecosUserName || 'User';
  } else {
    // Use the persona_name frozen at write time (historical restore), else fall back to current
    const frozenName = opts && opts.persona_name
      ? opts.persona_name.replace(/_/g, ' ').replace(/\.yaml$/i, '')
      : null;
    nameEl.textContent = frozenName || window.HecosPersonaName || 'Hecos';
  }

  const timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  const ts = (opts && opts.timestamp) ? new Date(opts.timestamp) : new Date();
  timeEl.textContent = ts.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

  header.appendChild(nameEl);
  header.appendChild(timeEl);
  wrapper.appendChild(header);

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';
  if(text) bubble.innerHTML = renderMarkdown(text);
  
  if (opts && opts.model_info) {
      bubble.setAttribute('title', opts.model_info);
      bubble.style.cursor = 'help';
  }
  
  wrapper.appendChild(bubble);

  msg.appendChild(avatar);
  msg.appendChild(wrapper);
  
  const chatArea = document.getElementById('chat-area');
  if (chatArea) {
      chatArea.appendChild(msg);
      chatArea.scrollTop = chatArea.scrollHeight;
  }
  
  // Track last real AI bubble for audio_ready (don't use :last-child which breaks when action-log divs follow)
  if (!isUser) {
      window._lastAiBubble = bubble;
      if (opts && opts.audio_file) {
          bubble.dataset.audioId = opts.audio_file;
          // Pre-load the audio badge for historical messages (without autoplay)
          if (typeof window.tryLoadAudio === 'function') {
              window.tryLoadAudio(bubble, false);
          }
      }
  }
  
  const hIdx = (opts && opts.historyIndex !== undefined) ? opts.historyIndex : 
               ((window.chatHistory) ? window.chatHistory.length - 1 : -1);

  if (typeof window.attachMessageActions === 'function') {
    window.attachMessageActions(msg, isUser ? 'user' : 'ai', hIdx);
  }
  return { msg, bubble };
}

// Fullscreen Avatar View
window.openAvatarFull = function(src) {
  let lb = document.getElementById('avatar-lightbox');
  if (!lb) {
    lb = document.createElement('div');
    lb.id = 'avatar-lightbox';
    lb.onclick = () => lb.classList.remove('active');
    document.body.appendChild(lb);
  }
  lb.innerHTML = `<img src="${src}">`;
  setTimeout(() => lb.classList.add('active'), 10);
};


function renderMarkdown(text) {
  let html = "";
  
  if (text) {
    // Auto-correct AI's persistent markdown syntax mistake: !(path) -> ![Image](path)
    text = text.replace(/!\(([^)]+)\)/g, '![Image]($1)');
    
    // Fix Windows paths and spaces inside markdown links so marked.js parses them correctly
    text = text.replace(/(\[[^\]]*\]\()([^)]+)(\))/g, function(match, p1, p2, p3) {
      let cleanUrl = p2.replace(/\\/g, '/');
      if (cleanUrl.includes(' ')) {
         cleanUrl = encodeURI(cleanUrl);
      }
      return p1 + cleanUrl + p3;
    });
  }
  
  if (typeof marked !== 'undefined') {
    // Optionally configure marked (e.g. breaks: true)
    html = marked.parse(text, { breaks: true });
    
    // Inject "Visual Editor" button for any .html links
    html = html.replace(/<a([^>]*)href="([^"]+\.html)"([^>]*)>(.*?)<\/a>/gi, function(match, p1, p2, p3, p4) {
      const editBtn = `<button class="hecos-btn sm" style="margin-left:8px; font-size:0.75em; padding:3px 8px; vertical-align:middle;" onclick="window.open('/docs/editor?file=' + encodeURIComponent('${p2}'), '_blank')"><i class="fas fa-magic"></i> Visual Editor</button>`;
      return match + editBtn;
    });
  } else {
    html = text
      .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  }
    
  if (typeof window.processAiMedia === 'function') {
    html = window.processAiMedia(html);
  } else if (typeof window.processAiImages === 'function') {
    html = window.processAiImages(html);
  }
  return html;
}

// Global Exports
window.addBubble = addBubble;
window.renderMarkdown = renderMarkdown;

// Alias used by chat_history.js to restore historical messages
window.appendMessage = function(role, text, opts = {}) {
    if (!text || opts.noSave === undefined) opts.noSave = true;
    if (!text || !text.trim()) return;

    let displayHtml = text;
    let thinkText = null;

    if (role !== 'user' && text) {
        // 1. Native JSON format fallback for history
        if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
            try {
                const parsed = JSON.parse(text);
                if (parsed.response && parsed.response.text) {
                    displayHtml = parsed.response.text;
                    if (parsed.thought && parsed.thought.reasoning) {
                        thinkText = parsed.thought.reasoning;
                    }
                }
            } catch (e) {
                // Not JSON, ignore
            }
        }
        // 2. <think> tag extraction for history
        if (!thinkText) {
            const thinkMatch = displayHtml.match(/<think>([\s\S]*?)<\/think>/i);
            if (thinkMatch) {
                thinkText = thinkMatch[1].trim();
                displayHtml = displayHtml.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
            }
        }
        // 3. Bare </think> tag (model omitted opening tag — most common for local models)
        if (!thinkText && displayHtml.includes('</think>')) {
            const parts = displayHtml.split('</think>');
            thinkText = parts[0].trim();
            displayHtml = parts.slice(1).join('').trim();
        }
    }

    const { bubble } = window.addBubble(role, displayHtml, null, opts);
    if (thinkText && window.renderThinkBlock) {
        window.renderThinkBlock(thinkText, bubble);
    }
};

/**
 * renderThinkBlock — renders a collapsible reasoning block before the AI bubble.
 * @param {string} thinkText  — the raw reasoning content
 * @param {Element} aiBubble  — the current AI response .msg-bubble element
 */
window.renderThinkBlock = function(thinkText, aiBubble) {
    if (!thinkText || !thinkText.trim()) return;

    const msgContainer = aiBubble ? aiBubble.closest('.msg') : null;
    if (!msgContainer) return;

    // Attach the reasoning text as a data attribute on the message container
    // so that attachMessageActions can detect it and build the button.
    // We URI encode it to prevent breaking HTML attributes.
    msgContainer.setAttribute('data-think-text', encodeURIComponent(thinkText));

    // Add a permanent indicator to the message header (next to the name)
    const nameEl = msgContainer.querySelector('.msg-name');
    if (nameEl && !nameEl.querySelector('.think-badge')) {
        const badge = document.createElement('span');
        badge.className = 'think-badge';
        badge.title = 'Reasoning process attached (click to expand)';
        badge.innerHTML = '💡';
        badge.style.cursor = 'pointer';
        badge.style.marginLeft = '6px';
        badge.style.opacity = '0.8';
        badge.style.fontSize = '0.9em';
        badge.style.transition = 'opacity 0.2s';
        
        // Add hover effect
        badge.onmouseenter = () => badge.style.opacity = '1';
        badge.onmouseleave = () => badge.style.opacity = '0.8';
        
        // When clicked, trigger the think-btn in the action bar if it exists
        badge.onclick = (e) => {
            e.stopPropagation();
            const thinkBtn = msgContainer.querySelector('.think-btn');
            if (thinkBtn) thinkBtn.click();
        };
        
        nameEl.appendChild(badge);
    }

    // If actions are already rendered, try to update them (rare race condition fallback)
    const existingBtn = msgContainer.querySelector('.think-btn');
    if (!existingBtn && typeof window.attachMessageActions === 'function') {
        const hIdx = msgContainer.getAttribute('data-hidx');
        if (hIdx !== null) {
            // Remove old action bar and re-attach
            const actionBar = msgContainer.querySelector('.msg-actions');
            if (actionBar) actionBar.remove();
            window.attachMessageActions(msgContainer, 'ai', parseInt(hIdx, 10));
        }
    }
};
