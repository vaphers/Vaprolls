// WebSocket client for live audit progress

function connectToAudit(auditId, onProgress, onComplete) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/audit/${auditId}`;
    
    let ws = new WebSocket(wsUrl);
    let isComplete = false;

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'progress') {
                if (onProgress) onProgress(data);
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
            console.log("WebSocket closed unexpectedly. Reconnecting in 2s...");
            setTimeout(() => {
                // To avoid infinite reconnects if it's really dead, we might want to check the API status
                fetch(`/api/audit/${auditId}/status`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'complete') {
                            if (onComplete) onComplete();
                        } else {
                            connectToAudit(auditId, onProgress, onComplete);
                        }
                    }).catch(() => {
                        connectToAudit(auditId, onProgress, onComplete);
                    });
            }, 2000);
        }
    };

    ws.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}
