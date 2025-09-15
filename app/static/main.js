async function ingest() {
  const text = document.getElementById('ingestText').value.trim();
  const source = document.getElementById('source').value.trim();
  const title = document.getElementById('title').value.trim();
  const status = document.getElementById('ingestStatus');
  status.textContent = 'Adding...';
  try {
    const res = await fetch('/ingest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([{ text, source, title }])
    });
    const data = await res.json();
    status.textContent = `Added ${data.added_chunks} chunks.`;
  } catch (e) {
    status.textContent = 'Failed to ingest.';
  }
}

async function upload() {
  const fileInput = document.getElementById('fileInput');
  const source = document.getElementById('source').value.trim();
  const title = document.getElementById('title').value.trim();
  const status = document.getElementById('ingestStatus');
  const file = fileInput.files && fileInput.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { status.textContent = 'File too large (>10MB)'; return; }
  status.textContent = 'Uploading...';
  try {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('source', source);
    fd.append('title', title);
    const res = await fetch('/ingest-file', { method: 'POST', body: fd });
    const data = await res.json();
    status.textContent = `Added ${data.added_chunks} chunks.`;
  } catch (e) {
    status.textContent = 'Upload failed.';
  }
}

async function ask() {
  const q = document.getElementById('question').value.trim();
  const ans = document.getElementById('answer');
  const srcs = document.getElementById('sources');
  ans.textContent = 'Thinking...';
  srcs.innerHTML = '';
  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, k: 4 })
    });
    const data = await res.json();
    ans.textContent = data.answer || '(no answer)';
    if (Array.isArray(data.sources)) {
      data.sources.forEach(s => {
        const div = document.createElement('div');
        div.className = 'src';
        div.textContent = `[${s.title || s.source}] ${s.snippet || ''}`;
        srcs.appendChild(div);
      });
    }
  } catch (e) {
    ans.textContent = 'Error fetching answer.';
  }
}

document.getElementById('ingestBtn').addEventListener('click', ingest);
document.getElementById('uploadBtn').addEventListener('click', upload);
document.getElementById('askBtn').addEventListener('click', ask);

