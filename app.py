import io
from flask import Flask, request, send_file, jsonify, Response
from pypdf import PdfWriter, PdfReader

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit

# HTML embedded directly — no templates/ folder required
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF Merger</title>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Syne+Mono&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg:#0d0d0f; --surface:#16161a; --border:#2a2a32;
      --accent:#f0e040; --accent2:#e05aff; --text:#f0ede8;
      --muted:#7a7a8a; --danger:#ff5a5a; --success:#4affa0;
      --radius:12px;
    }
    body {
      background:var(--bg); color:var(--text); font-family:'Syne',sans-serif;
      min-height:100vh; display:flex; flex-direction:column; align-items:center;
      padding:48px 20px 80px; overflow-x:hidden;
    }
    body::before {
      content:''; position:fixed; top:-200px; left:50%;
      transform:translateX(-50%); width:800px; height:500px;
      background:radial-gradient(ellipse,rgba(240,224,64,0.07) 0%,transparent 70%);
      pointer-events:none; z-index:0;
    }
    .container { width:100%; max-width:680px; position:relative; z-index:1; }
    header { text-align:center; margin-bottom:48px; }
    .logo-badge {
      display:inline-flex; align-items:center; gap:8px;
      background:rgba(240,224,64,0.1); border:1px solid rgba(240,224,64,0.25);
      border-radius:999px; padding:6px 16px; font-size:11px; font-weight:700;
      letter-spacing:0.2em; text-transform:uppercase; color:var(--accent); margin-bottom:20px;
    }
    h1 { font-size:clamp(2.4rem,7vw,3.8rem); font-weight:800; line-height:1; letter-spacing:-0.03em; }
    h1 .word-pdf{color:var(--accent);} h1 .word-merge{color:var(--accent2);}
    .subtitle { margin-top:14px; color:var(--muted); font-size:1rem; }
    #drop-zone {
      border:2px dashed var(--border); border-radius:var(--radius);
      padding:52px 32px; text-align:center; cursor:pointer;
      transition:border-color .2s,background .2s,transform .15s; background:var(--surface);
    }
    #drop-zone:hover,#drop-zone.drag-over {
      border-color:var(--accent); background:rgba(240,224,64,0.04); transform:scale(1.005);
    }
    #drop-zone .icon { font-size:2.8rem; margin-bottom:12px; display:block; }
    #drop-zone h2 { font-size:1.15rem; font-weight:700; margin-bottom:6px; }
    #drop-zone p  { font-size:.85rem; color:var(--muted); }
    #file-input { display:none; }
    .browse-btn {
      display:inline-block; margin-top:16px; padding:9px 24px;
      background:var(--accent); color:#0d0d0f; border-radius:999px;
      font-weight:700; font-size:.85rem; letter-spacing:.05em; cursor:pointer;
      transition:opacity .15s,transform .1s;
    }
    .browse-btn:hover { opacity:.85; transform:scale(1.03); }
    #file-list-section { margin-top:28px; display:none; }
    .section-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
    .section-title { font-size:.75rem; font-weight:700; letter-spacing:.15em; text-transform:uppercase; color:var(--muted); }
    .clear-btn {
      background:none; border:1px solid var(--border); color:var(--muted);
      border-radius:6px; padding:4px 12px; font-size:.75rem; font-family:'Syne',sans-serif;
      cursor:pointer; transition:border-color .15s,color .15s;
    }
    .clear-btn:hover { border-color:var(--danger); color:var(--danger); }
    #file-list { list-style:none; display:flex; flex-direction:column; gap:8px; }
    .file-item {
      display:flex; align-items:center; gap:12px;
      background:var(--surface); border:1px solid var(--border);
      border-radius:var(--radius); padding:12px 16px; cursor:grab;
      transition:border-color .15s,box-shadow .15s,transform .15s;
      user-select:none; animation:slideIn .2s ease;
    }
    @keyframes slideIn { from{opacity:0;transform:translateY(-8px)} to{opacity:1;transform:translateY(0)} }
    .file-item:active  { cursor:grabbing; }
    .file-item.dragging { opacity:.4; transform:scale(.97); }
    .file-item.drag-target { border-color:var(--accent2); box-shadow:0 0 0 2px rgba(224,90,255,.2); }
    .drag-handle { color:var(--muted); font-size:1.1rem; flex-shrink:0; opacity:.5; }
    .file-num {
      font-family:'Syne Mono',monospace; font-size:.7rem; font-weight:700;
      background:rgba(240,224,64,.12); color:var(--accent);
      border-radius:6px; padding:2px 7px; flex-shrink:0; min-width:28px; text-align:center;
    }
    .file-info { flex:1; min-width:0; }
    .file-name { font-size:.9rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .file-size { font-size:.75rem; color:var(--muted); margin-top:2px; }
    .remove-btn {
      background:none; border:none; color:var(--muted); font-size:1rem;
      cursor:pointer; border-radius:6px; padding:4px 7px;
      transition:background .15s,color .15s; flex-shrink:0;
    }
    .remove-btn:hover { background:rgba(255,90,90,.12); color:var(--danger); }
    #merge-btn {
      width:100%; margin-top:24px; padding:16px;
      background:var(--accent); color:#0d0d0f; border:none;
      border-radius:var(--radius); font-family:'Syne',sans-serif;
      font-size:1rem; font-weight:800; letter-spacing:.04em; cursor:pointer;
      display:none; align-items:center; justify-content:center; gap:10px;
      transition:opacity .15s,transform .1s;
    }
    #merge-btn:hover    { opacity:.88; transform:translateY(-1px); }
    #merge-btn:active   { transform:translateY(0); }
    #merge-btn:disabled { opacity:.5; cursor:not-allowed; transform:none; }
    .spinner {
      width:18px; height:18px; border:2.5px solid rgba(0,0,0,.2);
      border-top-color:#0d0d0f; border-radius:50%;
      animation:spin .7s linear infinite; display:none;
    }
    @keyframes spin { to{transform:rotate(360deg)} }
    #toast {
      position:fixed; bottom:32px; left:50%;
      transform:translateX(-50%) translateY(12px);
      background:var(--surface); border:1px solid var(--border);
      border-radius:999px; padding:12px 24px; font-size:.85rem; font-weight:600;
      opacity:0; pointer-events:none; transition:opacity .25s,transform .25s;
      z-index:100; white-space:nowrap;
    }
    #toast.show    { opacity:1; transform:translateX(-50%) translateY(0); }
    #toast.success { border-color:var(--success); color:var(--success); }
    #toast.error   { border-color:var(--danger);  color:var(--danger);  }
    .tip { margin-top:20px; text-align:center; font-size:.78rem; color:var(--muted); }
    .tip span { color:var(--accent2); }
  </style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo-badge">&#9632; Tool</div>
    <h1><span class="word-pdf">PDF</span> <span class="word-merge">Merger</span></h1>
    <p class="subtitle">Upload PDFs &middot; Drag to reorder &middot; Download merged file</p>
  </header>

  <div id="drop-zone">
    <span class="icon">&#128196;</span>
    <h2>Drop your PDF files here</h2>
    <p>Files will be merged in the order shown below</p>
    <label for="file-input" class="browse-btn">Browse Files</label>
    <input type="file" id="file-input" multiple accept=".pdf"/>
  </div>

  <div id="file-list-section">
    <div class="section-header">
      <span class="section-title">Files to merge (<span id="file-count">0</span>)</span>
      <button class="clear-btn" id="clear-btn">Clear all</button>
    </div>
    <ul id="file-list"></ul>
    <button id="merge-btn">
      <span class="spinner" id="spinner"></span>
      <span id="btn-label">&#11015; Merge &amp; Download</span>
    </button>
    <p class="tip">Drag the <span>&#8801;</span> handle to reorder files before merging</p>
  </div>
</div>
<div id="toast"></div>

<script>
  const dropZone    = document.getElementById('drop-zone');
  const fileInput   = document.getElementById('file-input');
  const fileListEl  = document.getElementById('file-list');
  const listSection = document.getElementById('file-list-section');
  const fileCount   = document.getElementById('file-count');
  const mergeBtn    = document.getElementById('merge-btn');
  const clearBtn    = document.getElementById('clear-btn');
  const spinner     = document.getElementById('spinner');
  const btnLabel    = document.getElementById('btn-label');
  let files = [];

  dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('drag-over'); addFiles([...e.dataTransfer.files]); });
  dropZone.addEventListener('click', e => { if (!e.target.classList.contains('browse-btn')) fileInput.click(); });
  fileInput.addEventListener('change', () => { addFiles([...fileInput.files]); fileInput.value=''; });
  clearBtn.addEventListener('click', () => { files=[]; render(); });

  function addFiles(newFiles) {
    const pdfs = newFiles.filter(f => f.type==='application/pdf' || f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfs.length) { showToast('Only PDF files are supported','error'); return; }
    pdfs.forEach(f => files.push({ id: crypto.randomUUID(), file: f }));
    render();
  }

  function fmt(b) {
    if (b<1024) return b+' B';
    if (b<1024*1024) return (b/1024).toFixed(1)+' KB';
    return (b/(1024*1024)).toFixed(1)+' MB';
  }

  function render() {
    fileListEl.innerHTML='';
    fileCount.textContent=files.length;
    listSection.style.display = files.length ? 'block':'none';
    mergeBtn.style.display    = files.length ? 'flex' :'none';
    files.forEach((item,idx) => {
      const li = document.createElement('li');
      li.className='file-item'; li.draggable=true; li.dataset.id=item.id;
      li.innerHTML=`
        <span class="drag-handle" title="Drag to reorder">&#8801;</span>
        <span class="file-num">${String(idx+1).padStart(2,'0')}</span>
        <div class="file-info">
          <div class="file-name" title="${item.file.name}">${item.file.name}</div>
          <div class="file-size">${fmt(item.file.size)}</div>
        </div>
        <button class="remove-btn" title="Remove">&#10005;</button>`;
      li.addEventListener('dragstart', onDragStart);
      li.addEventListener('dragover',  onDragOver);
      li.addEventListener('drop',      onDrop);
      li.addEventListener('dragend',   onDragEnd);
      li.querySelector('.remove-btn').addEventListener('click', () => { files=files.filter(f=>f.id!==item.id); render(); });
      fileListEl.appendChild(li);
    });
  }

  let draggedId=null;
  function onDragStart(e) { draggedId=this.dataset.id; this.classList.add('dragging'); e.dataTransfer.effectAllowed='move'; }
  function onDragOver(e)  { e.preventDefault(); document.querySelectorAll('.file-item').forEach(el=>el.classList.remove('drag-target')); if(this.dataset.id!==draggedId) this.classList.add('drag-target'); }
  function onDrop(e) {
    e.stopPropagation();
    if (this.dataset.id===draggedId) return;
    const from=files.findIndex(f=>f.id===draggedId), to=files.findIndex(f=>f.id===this.dataset.id);
    const [m]=files.splice(from,1); files.splice(to,0,m); render();
  }
  function onDragEnd() { document.querySelectorAll('.file-item').forEach(el=>el.classList.remove('dragging','drag-target')); draggedId=null; }

  mergeBtn.addEventListener('click', async () => {
    if (files.length<2) { showToast('Add at least 2 PDFs to merge','error'); return; }
    mergeBtn.disabled=true; spinner.style.display='block'; btnLabel.textContent='Merging\u2026';
    const fd=new FormData();
    files.forEach(item => { fd.append('pdfs',item.file,item.file.name); fd.append('order[]',item.file.name); });
    try {
      const res=await fetch('/merge',{method:'POST',body:fd});
      if(!res.ok){const e=await res.json();throw new Error(e.error||'Merge failed');}
      const blob=await res.blob(), url=URL.createObjectURL(blob), a=document.createElement('a');
      a.href=url; a.download='merged.pdf'; a.click(); URL.revokeObjectURL(url);
      showToast('\u2713 Merged '+files.length+' files successfully','success');
    } catch(err) { showToast('Error: '+err.message,'error'); }
    finally { mergeBtn.disabled=false; spinner.style.display='none'; btnLabel.textContent='\u2B07 Merge & Download'; }
  });

  let tt;
  function showToast(msg,type='') {
    const t=document.getElementById('toast'); t.textContent=msg; t.className='show '+type;
    clearTimeout(tt); tt=setTimeout(()=>t.className='',3200);
  }
</script>
</body>
</html>"""


@app.route('/')
def index():
    return Response(HTML, mimetype='text/html')


@app.route('/merge', methods=['POST'])
def merge_pdfs():
    files = request.files.getlist('pdfs')
    order = request.form.getlist('order[]')

    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No PDF files provided'}), 400

    file_map = {}
    for f in files:
        if f and f.filename.lower().endswith('.pdf'):
            file_map[f.filename] = f

    ordered_files = [file_map[n] for n in order if n in file_map] if order else list(file_map.values())

    if not ordered_files:
        return jsonify({'error': 'No valid PDF files found'}), 400

    writer = PdfWriter()
    try:
        for f in ordered_files:
            f.seek(0)
            reader = PdfReader(io.BytesIO(f.read()))
            for page in reader.pages:
                writer.add_page(page)
    except Exception as e:
        return jsonify({'error': f'Failed to process PDF: {e}'}), 500

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name='merged.pdf')


if __name__ == '__main__':
    app.run(debug=True, port=5000)