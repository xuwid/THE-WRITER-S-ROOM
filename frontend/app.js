const modeEl = document.getElementById("mode");
const approvalEl = document.getElementById("approval");
const promptEl = document.getElementById("prompt");
const manualEl = document.getElementById("manual_script");
const runBtn = document.getElementById("runBtn");
const approveBtn = document.getElementById("approveBtn");
const refreshBtn = document.getElementById("refreshBtn");
const statusEl = document.getElementById("status");
const sceneManifestEl = document.getElementById("sceneManifest");
const characterDbEl = document.getElementById("characterDb");
const imagesEl = document.getElementById("images");

let lastCheckpointSessionId = null;

function setStatus(msg) {
  statusEl.textContent = msg;
}

function renderOutputs(data) {
  sceneManifestEl.textContent = JSON.stringify(data.scene_manifest || {}, null, 2);
  characterDbEl.textContent = JSON.stringify(data.character_db || [], null, 2);

  imagesEl.innerHTML = "";
  const assets = data.image_assets || [];
  for (const path of assets) {
    const name = path.split("/").pop();
    const wrap = document.createElement("div");
    const img = document.createElement("img");
    img.src = `/api/images/${name}`;
    img.alt = name;
    wrap.appendChild(img);
    imagesEl.appendChild(wrap);
  }
}

async function runPipeline() {
  setStatus("Running pipeline...");
  const payload = {
    mode: modeEl.value,
    prompt: promptEl.value,
    manual_script: manualEl.value,
    approved: approvalEl.value === "true",
  };

  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    setStatus(`Error: ${data.detail || "unknown error"}`);
    return;
  }

  renderOutputs(data);

  if (data.needs_approval) {
    lastCheckpointSessionId = data.session_id;
    approveBtn.disabled = false;
    setStatus(`Checkpoint reached for session ${data.session_id}. Click approve.`);
  } else {
    lastCheckpointSessionId = null;
    approveBtn.disabled = true;
    setStatus(`Pipeline completed: ${data.status}`);
  }
}

async function approveCheckpoint() {
  if (!lastCheckpointSessionId) {
    setStatus("No checkpoint available to approve.");
    return;
  }

  setStatus("Approving checkpoint and resuming...");
  const res = await fetch("/api/approve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: lastCheckpointSessionId, approved: true }),
  });

  const data = await res.json();
  if (!res.ok) {
    setStatus(`Error: ${data.detail || "approval failed"}`);
    return;
  }

  renderOutputs(data);
  approveBtn.disabled = true;
  lastCheckpointSessionId = null;
  setStatus(`Pipeline resumed and completed: ${data.status}`);
}

async function refreshOutputs() {
  const res = await fetch("/api/outputs");
  const data = await res.json();
  renderOutputs(data);
  setStatus("Outputs refreshed from disk.");
}

runBtn.addEventListener("click", runPipeline);
approveBtn.addEventListener("click", approveCheckpoint);
refreshBtn.addEventListener("click", refreshOutputs);

refreshOutputs();
