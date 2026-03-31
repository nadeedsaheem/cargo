document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatMessages = document.getElementById('chat-messages');
    const senderSelect = document.getElementById('sender-type');
    const insightsContent = document.getElementById('ai-insights-content');
    const decisionBtn = document.getElementById('decision-btn');
    
    const dashMatches = document.getElementById('dash-matches');
    const dashProfit = document.getElementById('dash-profit');
    const dashCo2 = document.getElementById('dash-co2');

    const notif = document.getElementById('smart-notification');
    const notifDesc = document.getElementById('notif-desc');
    const notifAccept = document.getElementById('notif-accept-btn');
    const notifClose = document.getElementById('notif-close-btn');
    const resetBtn = document.getElementById('reset-btn');
    
    let isWaitingForResponse = false;
    let pendingMatchData = null;

    function formatCurrency(amount) {
        return "₹" + amount.toLocaleString('en-IN');
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function appendMessage(text, senderClass, confidence = null) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${senderClass}`;
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = `bubble`;
        
        // Convert Markdown line breaks to HTML
        let formattedText = text.replace(/\n/g, '<br>');
        bubbleDiv.innerHTML = formattedText; 
        
        if (confidence !== null && senderClass === 'bot') {
            const confBadge = document.createElement('div');
            confBadge.className = `confidence-badge ${confidence < 70 ? 'low' : ''}`;
            confBadge.innerHTML = `<i class="fa-solid fa-microchip"></i> ${confidence}%`;
            bubbleDiv.appendChild(confBadge);
        }
        
        msgDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.id = typingId;
        msgDiv.className = 'message bot';
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'bubble';
        bubbleDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        msgDiv.appendChild(bubbleDiv);
        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        return typingId;
    }

    async function handleAcceptMatch(profit, co2) {
        try {
            const response = await fetch('/api/accept_match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ profit: profit, co2: co2 })
            });
            const data = await response.json();
            updateDashboard(data.global_stats);
            appendMessage(`✅ <b>Match Accepted!</b> Generated ${formatCurrency(profit)} in profit. Route data dispatched.`, 'system');
            
            notif.classList.remove('show');
            setTimeout(() => notif.classList.add('hidden'), 500);
            
            insightsContent.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-check" style="color: #10b981;"></i>
                    <p style="margin-top:20px;">Operation Secured.</p>
                </div>
            `;
        } catch (error) {
            console.error(error);
        }
    }

    notifAccept.addEventListener('click', () => {
        if(pendingMatchData) handleAcceptMatch(pendingMatchData.profit_gain, pendingMatchData.co2_reduction);
    });

    notifClose.addEventListener('click', () => {
        notif.classList.remove('show');
        setTimeout(() => notif.classList.add('hidden'), 500);
    });

    function showNotification(match) {
        pendingMatchData = {
            profit_gain: parseInt(match.insights.profit_gain) || 0,
            co2_reduction: parseFloat(match.insights.co2_reduction) || 0
        };
        
        notif.classList.remove('hidden');
        document.getElementById('notif-title').innerHTML = `🏆 BEST MATCH RECOMMENDED`;
        document.getElementById('notif-title').style.color = '#10b981';
        
        notifDesc.innerHTML = `<b>${match.score}% Match:</b> ${match.load.capacity || 'cargo'}t <br>${match.truck.start} To ${match.truck.destination}`;
        
        setTimeout(() => notif.classList.add('show'), 50);
        setTimeout(() => {
            if (notif.classList.contains('show')) {
                notif.classList.remove('show');
                setTimeout(() => notif.classList.add('hidden'), 500);
            }
        }, 10000);
    }

    function updateDashboard(stats) {
        dashMatches.innerText = stats.total_matches;
        dashProfit.innerText = stats.total_profit.toLocaleString('en-IN');
        dashCo2.innerText = stats.total_co2_saved;
    }

    window.acceptMatchFromCard = function(profit, co2) {
        handleAcceptMatch(profit, co2);
    };

    function processMatchSystemAlert(match, allMatches) {
        let sysMsg = `🏆 <b style="color: #10b981;">BEST MATCH RECOMMENDED</b> 🏆<br><br>
            💡 <b>Choose THIS option:</b><br>
            🚚 <b>Truck:</b> ${match.truck.start} → ${match.truck.destination}<br>
            📦 <b>Cargo:</b> ${match.load.start} → ${match.load.destination}<br><br>
            <b>Reason:</b><br>`;
            
        if (match.reasons && match.reasons.length > 0) {
            match.reasons.forEach(r => sysMsg += `${r}<br>`);
        } else {
            sysMsg += `✔ High route alignment<br>`;
        }
        
        sysMsg += `<br>📍 <b>Distance to pickup:</b> ${match.dist_to_pickup} km<br>
            ⏱️ <b>ETA to pickup:</b> ${match.insights.pickup_eta}<br>
            🔥 <b>Match Score:</b> ${match.score}%<br>`;

        if (allMatches.length > 1) {
            sysMsg += `<br><b style="color:#f59e0b;">Other Options Available:</b><br>`;
            for(let i=1; i<allMatches.length; i++) {
                let mType = allMatches[i].truck.start === match.truck.start ? allMatches[i].load : allMatches[i].truck;
                sysMsg += `Option ${i+1}: ${mType.start} → ${mType.destination} | <b>Score: ${allMatches[i].score}%</b><br>`;
            }
        }
            
        setTimeout(() => appendMessage(sysMsg, 'system'), 800);
    }

    function updateInsightsPanel(response) {
        if (response.global_stats) updateDashboard(response.global_stats);

        insightsContent.innerHTML = '';
        let contentHTML = '';

        const matches = response.matches || [];
        const suggestions = response.copilot_suggestions || [];

        if (suggestions.length > 0) {
            contentHTML += `
                <div class="copilot-panel">
                    <h3><i class="fa-solid fa-brain"></i> Predictive Copilot</h3>
                    ${suggestions.map(s => `<div class="suggestion-item">${s}</div>`).join('')}
                </div>
            `;
        }

        if (matches.length > 0) {
            matches.forEach((m, idx) => {
                const rankClass = idx === 0 ? 'top-rank' : `rank-${idx + 1}`;
                const badgeText = idx === 0 ? '👍 RECOMMENDED' : `Option #${idx + 1}`;
                
                contentHTML += `
                    <div class="match-card-v2 ${rankClass}" style="animation-delay: ${idx * 0.15}s">
                        <div class="rank-badge">${badgeText}</div>
                        
                        <div class="match-locations">
                            ${m.truck.start} <i class="fa-solid fa-route"></i> ${m.truck.destination}
                        </div>
                        
                        <div class="metrics-grid">
                            <div class="metric highlight">
                                <span>Score & Efficiency</span>
                                <strong>${m.score}% | ${m.insights.route_efficiency}</strong>
                            </div>
                            <div class="metric profit">
                                <span>Est. Profit</span>
                                <strong>${m.insights.profit_gain_formatted}</strong>
                            </div>
                            <div class="metric">
                                <span>ETA & Distance</span>
                                <strong>${m.insights.eta} (${m.insights.distance})</strong>
                            </div>
                            <div class="metric">
                                <span>CO₂ Reduced</span>
                                <strong><i class="fa-solid fa-leaf" style="color: #34d399;"></i> ${m.insights.co2_reduction}kg</strong>
                            </div>
                        </div>
                        <button class="accept-btn" onclick="window.acceptMatchFromCard(${m.insights.profit_gain}, ${m.insights.co2_reduction})">Sign Contract</button>
                    </div>
                `;
            });
            
            showNotification(matches[0]);
            processMatchSystemAlert(matches[0], matches);
            
        } else if (response.extracted_data.confidence > 30) {
            contentHTML += `
                <div class="empty-state" style="margin-top: 20px;">
                    <i class="fa-solid fa-satellite-dish fa-fade" style="font-size: 2.5rem; color: #64748b;"></i>
                    <p style="margin-top: 15px;">Entity registered in the node network.<br>Awaiting suitable pairings...</p>
                </div>
            `;
        }

        if (!contentHTML) {
            contentHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-radar fa-spin-pulse"></i>
                    <p>Awaiting routing data...</p>
                </div>
            `;
        }
        
        insightsContent.innerHTML = contentHTML;
    }

    decisionBtn.addEventListener('click', async () => {
        if (isWaitingForResponse) return;
        isWaitingForResponse = true;
        
        appendMessage("Copilot, what should I do right now?", 'user', null);
        const typingId = showTypingIndicator();
        
        try {
            const resp = await fetch('/api/decision');
            const data = await resp.json();
            document.getElementById(typingId).remove();
            appendMessage(data.recommendation, 'bot', 99);
        } catch (e) {
            document.getElementById(typingId).remove();
            appendMessage("Decision Engine Offline.", 'system');
        } finally {
            isWaitingForResponse = false;
        }
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (isWaitingForResponse) return;
        
        const text = messageInput.value.trim();
        if (!text) return;
        
        // Task 5: Typing Shortcut Reset
        if (text.toLowerCase() === 'reset') {
            messageInput.value = '';
            executeResetFlow();
            return;
        }
        
        const senderType = senderSelect.value;
        const uiSenderClass = senderType === 'driver' ? 'driver' : 'loader';
        
        appendMessage(text, 'user ' + uiSenderClass, null);
        messageInput.value = '';
        
        isWaitingForResponse = true;
        const typingId = showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, sender: senderType })
            });
            
            const data = await response.json();
            document.getElementById(typingId).remove();
            
            let botText = '';
            const ext = data.extracted_data;
            
            if (ext.confidence > 30) {
                const eType = ext.type.charAt(0).toUpperCase() + ext.type.slice(1);
                botText = `Parsed: <b>${eType}</b> from <b>${ext.start}</b> to <b>${ext.destination}</b>`;
                if (ext.capacity) botText += ` (${ext.capacity} ton capacity).`;
                
                if (data.matches && data.matches.length > 0) {
                    botText += `<br>✅ Generated top ranking recommendations. Review your AI Insights dashboard.`;
                } else {
                    botText += `<br>⏳ Logged to active registry. Monitoring region for optimal matches...`;
                }
            } else {
                botText = "⚠️ <b>Low Confidence Data.</b> Could you please provide clearer Start and Destination locations?";
            }

            appendMessage(botText, 'bot', ext.confidence);
            updateInsightsPanel(data);
            
        } catch (error) {
            console.error('Error:', error);
            document.getElementById(typingId).remove();
            appendMessage('API Error or Network Disconnect.', 'system');
        } finally {
            isWaitingForResponse = false;
        }
    });

    async function executeResetFlow() {
        if (isWaitingForResponse) return;
        isWaitingForResponse = true;
        
        try {
            const resp = await fetch('/api/reset', { method: 'POST' });
            const data = await resp.json();
            
            // Clear UI
            chatMessages.innerHTML = '';
            insightsContent.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-radar fa-spin-pulse"></i>
                    <p>Awaiting routing data...</p>
                </div>
            `;
            updateDashboard(data.global_stats);
            
            // Inject welcome / confirmation block
            appendMessage('🔄 <b>System Memory Wiped.</b> Ready for new operations.', 'system');
        } catch(e) {
            console.error('Reset Failed:', e);
            appendMessage('⚠️ System Reset Failed.', 'system');
        } finally {
            isWaitingForResponse = false;
        }
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', executeResetFlow);
    }
});
