(function(){
    const mentionBox = document.getElementById('global-mention-autocomplete');
    const resultsContainer = document.getElementById('mention-results');
    let currentInput = null;
    let mentionMatchStr = '';
    let mentionStartIndex = -1;

    function closeMentions() {
        mentionBox.style.display = 'none';
        currentInput = null;
    }

    function positionMentionBox(inputEl) {
        const rect = inputEl.getBoundingClientRect();
        mentionBox.style.left = Math.max(10, rect.left) + 'px';
        const spaceBelow = window.innerHeight - rect.bottom;
        if (spaceBelow > 220) {
            mentionBox.style.top = (rect.bottom + 4) + 'px';
            mentionBox.style.bottom = 'auto';
        } else {
            mentionBox.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
            mentionBox.style.top = 'auto';
        }
    }

    function onSelectUser(username) {
        if (!currentInput) return;
        const val = currentInput.value;
        const before = val.substring(0, mentionStartIndex);
        const after = val.substring(mentionStartIndex + mentionMatchStr.length);
        
        currentInput.value = before + '@' + username + ' ' + after;
        
        currentInput.focus();
        currentInput.setSelectionRange(before.length + username.length + 2, before.length + username.length + 2);
        
        closeMentions();
        
        currentInput.dispatchEvent(new Event('input', {bubbles: true}));
    }

    let debounceTimer;
    function fetchMentions(query, inputEl) {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetch('/tweetapp/api/mentions-autocomplete/?q=' + encodeURIComponent(query))
                .then(r => r.json())
                .then(data => {
                    if (!data.users || data.users.length === 0) {
                        closeMentions();
                        return;
                    }
                    
                    resultsContainer.innerHTML = '';
                    data.users.forEach(u => {
                        const el = document.createElement('div');
                        el.style.display = 'flex';
                        el.style.alignItems = 'center';
                        el.style.gap = '10px';
                        el.style.padding = '10px 14px';
                        el.style.cursor = 'pointer';
                        el.style.borderBottom = '1px solid var(--border-subtle)';
                        el.onmouseover = () => el.style.background = 'var(--input)';
                        el.onmouseout = () => el.style.background = 'transparent';
                        
                        const avatar = u.avatar_url 
                            ? `<img src="${u.avatar_url}" style="width:28px;height:28px;border-radius:50%;object-fit:cover;">`
                            : `<div style="width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--card-bg);border:1px solid var(--border-subtle);color:var(--text-primary);font-size:12px;font-weight:bold;">${u.username.charAt(0).toUpperCase()}</div>`;
                        
                        el.innerHTML = `
                            ${avatar}
                            <div style="flex:1;min-width:0;line-height:1.2;text-align:left;">
                                <div style="font-weight:700;font-size:13px;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;">@${u.username}</div>
                                <div style="font-size:11px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${u.full_name}</div>
                            </div>
                        `;
                        el.addEventListener('mousedown', (e) => {
                            e.preventDefault(); 
                            onSelectUser(u.username);
                        });
                        resultsContainer.appendChild(el);
                    });
                    
                    mentionBox.style.display = 'block';
                    positionMentionBox(inputEl);
                })
                .catch(()=>closeMentions());
        }, 150); 
    }

    function handleInputLogic(e) {
        const input = e.target;
        if (input.tagName !== 'TEXTAREA' && input.tagName !== 'INPUT') return;
        if (input.type === 'password' || input.type === 'file' || input.type === 'hidden') return;
        
        const val = input.value;
        const curs = input.selectionStart;
        if (curs === undefined || curs === null) return;
        
        const textBeforeCursor = val.substring(0, curs);
        
        const match = textBeforeCursor.match(/(?:^|\s)(@[\w.]*)$/);
        
        if (match) {
            const query = match[1].substring(1); 
            if (query.trim() !== '') {
                currentInput = input;
                mentionMatchStr = match[1];
                mentionStartIndex = textBeforeCursor.lastIndexOf(mentionMatchStr);
                fetchMentions(query, input);
                return;
            }
        }
        closeMentions();
    }

    document.addEventListener('input', handleInputLogic);
    document.addEventListener('keyup', handleInputLogic);
    document.addEventListener('click', handleInputLogic);
    window.addEventListener('resize', closeMentions);
    
    document.addEventListener('mousedown', function(e) {
        if (mentionBox.style.display === 'block' && !mentionBox.contains(e.target) && e.target !== currentInput) {
            closeMentions();
        }
    });
})();
