/* cmd_execute.js — HDCS Palette Execution */

export async function executeCommand(rawInput) {
    // Determine context based on current URL path
    const path = window.location.pathname;
    let context = "chat";
    if (path.includes("flows")) context = "flows";
    else if (path.includes("config/ui")) context = "hub";

    try {
        const res = await fetch('/api/commands/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cmd: rawInput,
                context: context
            })
        });
        
        const data = await res.json();
        
        if (!data.ok) {
            console.error("HDCS Error:", data.error);
            showToast("Command Error: " + data.error, "error");
        } else {
            // For Flows contextual output, we can show it in a toast or update a log panel
            if (data.output_target === "flows" && context === "flows") {
                // If there's a flow log panel, update it. Otherwise show toast.
                showToast("Flow executed. Check logs.", "success");
            }
        }
        return data;
    } catch (e) {
        console.error("HDCS execution failed:", e);
        showToast("Execution failed", "error");
        return null;
    }
}

function showToast(msg, type="info") {
    // Attempt to use existing Hecos toast if available
    if (typeof window.showToast === 'function') {
        window.showToast(msg, type);
    } else {
        alert(msg);
    }
}
