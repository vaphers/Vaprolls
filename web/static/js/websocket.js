// WebSocket client for live audit progress

function connectToAudit(auditId, onProgress, onComplete, onTier2Complete) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/audit/${auditId}`;
    
    let ws = new WebSocket(wsUrl);
    let isComplete = false;

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            
            // Centralized state store integration
            if (window.AppState && typeof window.AppState.handleWsMessage === 'function') {
                window.AppState.handleWsMessage(data);
            }

            if (data.type === 'progress' || data.type === 'initial_state' || data.type === 'status') {
                if (onProgress) onProgress(data);
            } else if (data.type === 'analyzers_tier2_complete') {
                if (onTier2Complete) onTier2Complete(data);
            } else if (data.type === 'complete') {
                isComplete = true;
                ws.close();
                if (onComplete) onComplete(data);
            }
        } catch (err) {
            console.error("Error parsing WS message", err);
        }
    };

    ws.onclose = () => {
        if (!isComplete) {
            console.log("WebSocket closed. Reconnecting in 2s...");
            setTimeout(() => {
                fetch(`/api/audit/${auditId}/status`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'complete') {
                            if (onComplete) onComplete();
                        } else {
                            connectToAudit(auditId, onProgress, onComplete, onTier2Complete);
                        }
                    }).catch(() => {
                        connectToAudit(auditId, onProgress, onComplete, onTier2Complete);
                    });
            }, 2000);
        }
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
    };

    return ws;
}
