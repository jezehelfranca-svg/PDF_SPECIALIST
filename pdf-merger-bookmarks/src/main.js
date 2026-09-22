import { PDFDocument } from 'pdf-lib';
import * as pdfjsLib from 'pdfjs-dist/build/pdf.mjs';
import PdfWorker from 'pdfjs-dist/build/pdf.worker.mjs?worker&inline';
import { addOutlineTree, countOutlineItems } from './pdf/bookmarks.js';
import './styles.css';

const APP_VERSION = '2.0.0';

pdfjsLib.GlobalWorkerOptions.workerPort = new PdfWorker({
  name: 'atlas-pdf-preview-worker',
});

const state = {
  entries: [],
  busy: false,
  dragId: null,
};

let idSequence = 0;
let toastTimer = null;

const app = document.querySelector('#app');

app.innerHTML = `
  <div class="page-shell">
    <header class="site-header">
      <a class="brand" href="#workspace" aria-label="Atlas PDF Merger home">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 40 40" role="img">
            <path d="M11 7.5h13l6 6V32.5H11z" />
            <path d="M24 7.5v7h6M15.5 20h10M15.5 25h7" />
          </svg>
        </span>
        <span>
          <strong>ATLAS</strong>
          <small>PDF MERGER</small>
        </span>
      </a>
      <div class="header-meta">
        <span class="privacy-chip">
          <span class="privacy-dot" aria-hidden="true"></span>
          100% local processing
        </span>
        <span class="version-chip">v${APP_VERSION}</span>
      </div>
    </header>

    <main id="workspace">
      <section class="hero" aria-labelledby="pageTitle">
        <p class="eyebrow">PRIVATE PDF WORKSPACE</p>
        <h1 id="pageTitle">Merge files.<br /><span>Keep the map.</span></h1>
        <p class="hero-copy">
          Arrange PDFs in the order you need, preserve their source outlines,
          and export one document with real, clickable bookmarks.
        </p>
        <div class="trust-row" aria-label="App capabilities">
          <span>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>
            No uploads
          </span>
          <span>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>
            Unicode bookmarks
          </span>
          <span>
            <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>
            Works offline
          </span>
        </div>
      </section>

      <div class="workspace-grid">
        <section class="work-panel" aria-labelledby="filesHeading">
          <div class="panel-heading">
            <div>
              <p class="step-label">STEP 01</p>
              <h2 id="filesHeading">Build your document</h2>
            </div>
            <button id="addMoreButton" class="text-button" type="button" hidden>
              <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12" /></svg>
              Add PDFs
            </button>
          </div>

          <input
            id="fileInput"
            data-testid="file-input"
            class="visually-hidden"
            type="file"
            accept="application/pdf,.pdf"
            multiple
          />

          <div
            id="dropZone"
            class="drop-zone"
            data-testid="drop-zone"
            role="button"
            tabindex="0"
            aria-describedby="dropHelp"
          >
            <span class="drop-icon" aria-hidden="true">
              <svg viewBox="0 0 48 48"><path d="M24 31V13m0 0-7 7m7-7 7 7M12 28v7h24v-7" /></svg>
            </span>
            <div>
              <strong>Drop PDF files here</strong>
              <p id="dropHelp">or click to browse from your computer</p>
            </div>
            <span class="browse-label">CHOOSE FILES</span>
          </div>

          <div id="fileWorkspace" class="file-workspace" hidden>
            <div class="list-toolbar">
              <div id="summary" class="summary" aria-live="polite"></div>
              <button id="clearButton" class="quiet-button" type="button">Clear all</button>
            </div>
            <p class="reorder-hint">
              Drag rows or use the arrow buttons. Edit a bookmark title at any time.
            </p>
            <div id="fileList" class="file-list" data-testid="file-list"></div>
          </div>
        </section>

        <aside class="settings-panel" aria-labelledby="exportHeading">
          <div class="panel-heading compact">
            <div>
              <p class="step-label">STEP 02</p>
              <h2 id="exportHeading">Export settings</h2>
            </div>
          </div>

          <label class="field-label" for="outputName">Output filename</label>
          <div class="filename-field">
            <input
              id="outputName"
              type="text"
              value="merged_with_bookmarks"
              maxlength="120"
              autocomplete="off"
              spellcheck="false"
            />
            <span>.pdf</span>
          </div>

          <div class="setting-list">
            <label class="setting-row">
              <span>
                <strong>Preserve source bookmarks</strong>
                <small>Nest existing outlines below each file title</small>
              </span>
              <input id="preserveBookmarks" type="checkbox" checked />
              <span class="toggle" aria-hidden="true"></span>
            </label>

            <label class="setting-row">
              <span>
                <strong>Open bookmark panel</strong>
                <small>Ask compatible PDF readers to show the outline</small>
              </span>
              <input id="openBookmarkPanel" type="checkbox" checked />
              <span class="toggle" aria-hidden="true"></span>
            </label>
          </div>

          <div class="export-summary" id="exportSummary">
            <div>
              <span>FILES</span>
              <strong id="exportFileCount">0</strong>
            </div>
            <div>
              <span>PAGES</span>
              <strong id="exportPageCount">0</strong>
            </div>
            <div>
              <span>BOOKMARKS</span>
              <strong id="exportBookmarkCount">0</strong>
            </div>
          </div>

          <button id="mergeButton" class="merge-button" data-testid="merge-button" type="button" disabled>
            <span>Merge and download</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14" /></svg>
          </button>

          <div class="progress-track" aria-hidden="true"><span id="progressBar"></span></div>
          <div id="status" class="status-card" data-testid="status" role="status" aria-live="polite">
            <span class="status-icon" aria-hidden="true"></span>
            <p>Add at least one PDF to begin.</p>
          </div>

          <p class="local-note">
            Your files never leave this device. Merging happens entirely inside your browser.
          </p>
        </aside>
      </div>
    </main>

    <footer>
      <span>ATLAS PDF MERGER v${APP_VERSION}</span>
      <span>Offline-first document utility</span>
    </footer>
  </div>
  <div id="toast" class="toast" role="status" aria-live="polite"></div>
`;

const elements = {
  addMoreButton: document.querySelector('#addMoreButton'),
  clearButton: document.querySelector('#clearButton'),
  dropZone: document.querySelector('#dropZone'),
  exportBookmarkCount: document.querySelector('#exportBookmarkCount'),
  exportFileCount: document.querySelector('#exportFileCount'),
  exportPageCount: document.querySelector('#exportPageCount'),
  fileInput: document.querySelector('#fileInput'),
  fileList: document.querySelector('#fileList'),
  fileWorkspace: document.querySelector('#fileWorkspace'),
  mergeButton: document.querySelector('#mergeButton'),
  openBookmarkPanel: document.querySelector('#openBookmarkPanel'),
  outputName: document.querySelector('#outputName'),
  preserveBookmarks: document.querySelector('#preserveBookmarks'),
  progressBar: document.querySelector('#progressBar'),
  status: document.querySelector('#status'),
  summary: document.querySelector('#summary'),
  toast: document.querySelector('#toast'),
};

function escapeForAttribute(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('"', '&quot;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; value >= 1024 && index < units.length; index += 1) {
    value /= 1024;
    unit = units[index];
  }
  const digits = value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(digits)} ${unit}`;
}

function plural(value, singular, pluralValue = `${singular}s`) {
  return `${value} ${value === 1 ? singular : pluralValue}`;
}

function cleanBookmarkTitle(value) {
  return String(value ?? '')
    .replace(/\u0000/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 512);
}

function titleFromFilename(filename) {
  return cleanBookmarkTitle(filename.replace(/\.pdf$/i, '')) || 'Untitled PDF';
}

function safeDownloadName(value) {
  const base = String(value ?? '')
    .replace(/\.pdf$/i, '')
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_')
    .replace(/[. ]+$/g, '')
    .trim()
    .slice(0, 120);
  return `${base || 'merged_with_bookmarks'}.pdf`;
}

function setProgress(value) {
  const bounded = Math.max(0, Math.min(100, value));
  elements.progressBar.style.width = `${bounded}%`;
}

function setStatus(message, type = 'neutral') {
  elements.status.dataset.type = type;
  elements.status.querySelector('p').textContent = message;
}

function showToast(message, type = 'info') {
  window.clearTimeout(toastTimer);
  elements.toast.textContent = message;
  elements.toast.dataset.type = type;
  elements.toast.classList.add('visible');
  toastTimer = window.setTimeout(() => elements.toast.classList.remove('visible'), 4200);
}

function setBusy(isBusy) {
  state.busy = isBusy;
  document.body.classList.toggle('is-busy', isBusy);
  elements.fileInput.disabled = isBusy;
  elements.clearButton.disabled = isBusy;
  elements.addMoreButton.disabled = isBusy;
  elements.outputName.disabled = isBusy;
  elements.preserveBookmarks.disabled = isBusy;
  elements.openBookmarkPanel.disabled = isBusy;
  updateSummary();
}

function totalPages() {
  return state.entries.reduce((sum, entry) => sum + entry.pageCount, 0);
}

function sourceBookmarkCount() {
  return state.entries.reduce(
    (sum, entry) => sum + countOutlineItems(entry.outline),
    0,
  );
}

function outputBookmarkCount() {
  const nested = elements.preserveBookmarks.checked ? sourceBookmarkCount() : 0;
  return state.entries.length + nested;
}

function updateSummary() {
  const fileCount = state.entries.length;
  const pageCount = totalPages();
  const totalBytes = state.entries.reduce((sum, entry) => sum + entry.file.size, 0);

  elements.fileWorkspace.hidden = fileCount === 0;
  elements.dropZone.classList.toggle('compact', fileCount > 0);
  elements.addMoreButton.hidden = fileCount === 0;
  elements.summary.innerHTML = fileCount
    ? `<strong>${plural(fileCount, 'file')}</strong><span>${plural(pageCount, 'page')} / ${formatBytes(totalBytes)}</span>`
    : '';

  elements.exportFileCount.textContent = String(fileCount);
  elements.exportPageCount.textContent = String(pageCount);
  elements.exportBookmarkCount.textContent = String(fileCount ? outputBookmarkCount() : 0);
  elements.mergeButton.disabled = state.busy || fileCount === 0 || pageCount === 0;

  if (!state.busy && fileCount === 0) {
    setProgress(0);
    setStatus('Add at least one PDF to begin.', 'neutral');
  }
}

function actionButton(action, label, iconPath, disabled = false) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'row-action';
  button.dataset.action = action;
  button.setAttribute('aria-label', label);
  button.title = label;
  button.disabled = disabled;
  button.innerHTML = `<svg viewBox="0 0 20 20" aria-hidden="true"><path d="${iconPath}" /></svg>`;
  return button;
}

function renderFiles() {
  elements.fileList.replaceChildren();

  state.entries.forEach((entry, index) => {
    const card = document.createElement('article');
    card.className = 'file-card';
    card.dataset.id = entry.id;
    card.dataset.testid = 'file-card';
    card.draggable = !state.busy;

    const order = document.createElement('div');
    order.className = 'order-cell';
    order.innerHTML = `
      <span class="drag-grip" aria-hidden="true">
        <i></i><i></i><i></i><i></i><i></i><i></i>
      </span>
      <strong>${String(index + 1).padStart(2, '0')}</strong>
    `;

    const preview = document.createElement('div');
    preview.className = 'page-preview';
    if (entry.thumbnail) {
      const image = document.createElement('img');
      image.src = entry.thumbnail;
      image.alt = `First page preview of ${entry.file.name}`;
      preview.append(image);
    } else {
      preview.innerHTML = `
        <span>PDF</span>
        <svg viewBox="0 0 30 36" aria-hidden="true"><path d="M5 2h13l7 7v25H5zM18 2v8h7" /></svg>
      `;
    }

    const details = document.createElement('div');
    details.className = 'file-details';
    const sourceBookmarks = countOutlineItems(entry.outline);
    details.innerHTML = `
      <div class="source-name" title="${escapeForAttribute(entry.file.name)}">${escapeForAttribute(entry.file.name)}</div>
      <div class="file-meta">
        <span>${plural(entry.pageCount, 'page')}</span>
        <span>${formatBytes(entry.file.size)}</span>
        <span>${sourceBookmarks ? plural(sourceBookmarks, 'source bookmark') : 'No source bookmarks'}</span>
      </div>
      <label class="bookmark-field">
        <span>BOOKMARK TITLE</span>
        <input
          type="text"
          data-action="bookmark-title"
          value="${escapeForAttribute(entry.title)}"
          maxlength="512"
          aria-label="Bookmark title for ${escapeForAttribute(entry.file.name)}"
        />
      </label>
    `;

    const actions = document.createElement('div');
    actions.className = 'row-actions';
    actions.append(
      actionButton('move-up', `Move ${entry.file.name} up`, 'm5 12 5-5 5 5', index === 0 || state.busy),
      actionButton('move-down', `Move ${entry.file.name} down`, 'm5 8 5 5 5-5', index === state.entries.length - 1 || state.busy),
      actionButton('remove', `Remove ${entry.file.name}`, 'M5 5l10 10M15 5 5 15', state.busy),
    );

    card.append(order, preview, details, actions);
    elements.fileList.append(card);
  });

  updateSummary();
}

function isPdfCandidate(file) {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
}

function hasPdfSignature(bytes) {
  const header = new TextDecoder('latin1').decode(bytes.subarray(0, 1024));
  return header.includes('%PDF-');
}

async function resolveOutlinePage(pdf, destination) {
  try {
    let resolved = destination;
    if (typeof resolved === 'string') resolved = await pdf.getDestination(resolved);
    if (!Array.isArray(resolved) || resolved.length === 0) return null;
    const target = resolved[0];
    if (Number.isInteger(target)) return target;
    if (target && typeof target === 'object') return await pdf.getPageIndex(target);
  } catch {
    return null;
  }
  return null;
}

async function mapSourceOutline(pdf, items) {
  const mapped = [];

  for (const item of items || []) {
    const children = await mapSourceOutline(pdf, item.items || []);
    const pageIndex = await resolveOutlinePage(pdf, item.dest);
    const title = cleanBookmarkTitle(item.title);

    if (Number.isInteger(pageIndex) && pageIndex >= 0 && pageIndex < pdf.numPages) {
      mapped.push({
        title: title || 'Untitled source bookmark',
        pageIndex,
        children,
      });
    } else if (children.length > 0) {
      mapped.push(...children);
    }
  }

  return mapped;
}

async function renderFirstPage(pdf) {
  const page = await pdf.getPage(1);
  const baseViewport = page.getViewport({ scale: 1 });
  const targetWidth = 360;
  const scale = Math.min(1.5, targetWidth / Math.max(baseViewport.width, 1));
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d', { alpha: false });
  canvas.width = Math.max(1, Math.ceil(viewport.width));
  canvas.height = Math.max(1, Math.ceil(viewport.height));
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, canvas.width, canvas.height);
  await page.render({ canvas, canvasContext: context, viewport }).promise;
  return canvas.toDataURL('image/jpeg', 0.82);
}

async function inspectFile(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (!hasPdfSignature(bytes)) throw new Error('The file does not have a valid PDF header.');

  const source = await PDFDocument.load(bytes, { updateMetadata: false });
  const pageCount = source.getPageCount();
  if (pageCount === 0) throw new Error('The PDF has no pages.');

  let thumbnail = null;
  let outline = [];
  let previewWarning = '';
  let loadingTask;
  let pdf;

  try {
    loadingTask = pdfjsLib.getDocument({
      data: bytes.slice(),
      isEvalSupported: false,
      useWasm: false,
    });
    pdf = await loadingTask.promise;
    const [outlineResult, thumbnailResult] = await Promise.allSettled([
      pdf.getOutline().then((sourceOutline) => mapSourceOutline(pdf, sourceOutline || [])),
      renderFirstPage(pdf),
    ]);
    if (outlineResult.status === 'fulfilled') {
      outline = outlineResult.value;
    } else {
      previewWarning = `Bookmark scan: ${outlineResult.reason?.message || 'unavailable'}`;
    }
    if (thumbnailResult.status === 'fulfilled') {
      thumbnail = thumbnailResult.value;
    } else {
      previewWarning = [previewWarning, `Preview: ${thumbnailResult.reason?.message || 'unavailable'}`]
        .filter(Boolean)
        .join(' ');
    }
  } catch (error) {
    previewWarning = error?.message || 'Preview unavailable';
  } finally {
    if (pdf) await pdf.destroy();
    else if (loadingTask) await loadingTask.destroy();
  }

  return {
    id: `pdf-${Date.now()}-${idSequence += 1}`,
    file,
    bytes,
    pageCount,
    title: titleFromFilename(file.name),
    thumbnail,
    outline,
    previewWarning,
  };
}

function readableError(error, filename) {
  const raw = error?.message || String(error || 'Unknown error');
  if (/encrypt|password/i.test(raw)) {
    return `${filename} is password-protected. Remove the password and try again.`;
  }
  if (/invalid pdf|header|parse|unexpected/i.test(raw)) {
    return `${filename} could not be read as a valid PDF.`;
  }
  return `${filename}: ${raw}`;
}

async function addFiles(fileList) {
  if (state.busy) return;
  const files = Array.from(fileList || []);
  const candidates = files.filter(isPdfCandidate);
  const rejected = files.length - candidates.length;

  if (candidates.length === 0) {
    showToast(rejected ? 'Only PDF files can be added.' : 'No files selected.', 'error');
    return;
  }

  setBusy(true);
  elements.dropZone.classList.add('processing');
  let added = 0;
  const errors = [];

  for (let index = 0; index < candidates.length; index += 1) {
    const file = candidates[index];
    setProgress(((index + 0.25) / candidates.length) * 100);
    setStatus(`Reading ${file.name} (${index + 1} of ${candidates.length})`, 'working');

    try {
      const entry = await inspectFile(file);
      state.entries.push(entry);
      added += 1;
      renderFiles();
    } catch (error) {
      errors.push(readableError(error, file.name));
    }

    setProgress(((index + 1) / candidates.length) * 100);
  }

  elements.dropZone.classList.remove('processing');
  setBusy(false);
  setProgress(0);
  elements.fileInput.value = '';
  renderFiles();

  const previewWarnings = state.entries.filter((entry) => entry.previewWarning).length;
  if (added > 0) {
    setStatus(
      `${plural(added, 'PDF')} ready. ${plural(totalPages(), 'page')} will be merged.`,
      'ready',
    );
  }

  if (errors.length > 0 || rejected > 0) {
    const parts = [...errors];
    if (rejected) parts.push(`${plural(rejected, 'non-PDF file')} ignored.`);
    showToast(parts.join(' '), 'error');
  } else if (previewWarnings > 0) {
    showToast('Some preview or source-bookmark details could not be read, but the PDFs can still be merged.', 'info');
  } else {
    showToast(`${plural(added, 'PDF')} added.`, 'success');
  }
}

function shiftOutline(nodes, offset) {
  return nodes.map((node) => ({
    title: node.title,
    pageIndex: node.pageIndex + offset,
    children: shiftOutline(node.children || [], offset),
  }));
}

function downloadBytes(bytes, filename) {
  const blob = new Blob([bytes], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.hidden = true;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

async function mergeAndDownload() {
  if (state.busy || state.entries.length === 0) return;

  setBusy(true);
  setProgress(2);
  const filename = safeDownloadName(elements.outputName.value);
  const preserve = elements.preserveBookmarks.checked;

  try {
    const merged = await PDFDocument.create();
    const outline = [];
    let pageOffset = 0;

    merged.setTitle(filename.replace(/\.pdf$/i, ''));
    merged.setSubject('Merged PDF with document outline bookmarks');
    merged.setCreator(`Atlas PDF Merger v${APP_VERSION}`);
    merged.setProducer(`Atlas PDF Merger v${APP_VERSION} / pdf-lib`);
    merged.setCreationDate(new Date());
    merged.setModificationDate(new Date());

    for (let index = 0; index < state.entries.length; index += 1) {
      const entry = state.entries[index];
      setStatus(`Merging ${entry.file.name} (${index + 1} of ${state.entries.length})`, 'working');
      setProgress(5 + ((index + 0.5) / state.entries.length) * 72);

      const source = await PDFDocument.load(entry.bytes, { updateMetadata: false });
      const pageIndices = source.getPageIndices();
      if (pageIndices.length === 0) continue;

      const copiedPages = await merged.copyPages(source, pageIndices);
      copiedPages.forEach((page) => merged.addPage(page));

      outline.push({
        title: cleanBookmarkTitle(entry.title) || titleFromFilename(entry.file.name),
        pageIndex: pageOffset,
        children: preserve ? shiftOutline(entry.outline, pageOffset) : [],
      });
      pageOffset += copiedPages.length;
    }

    if (merged.getPageCount() === 0) throw new Error('The selected files contain no mergeable pages.');

    setStatus('Writing Unicode bookmarks and finalizing the PDF...', 'working');
    setProgress(82);
    addOutlineTree(merged, outline, {
      openPanel: elements.openBookmarkPanel.checked,
    });

    const result = await merged.save({
      addDefaultPage: false,
      objectsPerTick: 40,
      updateFieldAppearances: false,
      useObjectStreams: true,
    });

    setProgress(96);
    downloadBytes(result, filename);
    setProgress(100);
    setStatus(
      `${filename} is ready - ${plural(merged.getPageCount(), 'page')} and ${plural(countOutlineItems(outline), 'bookmark')}.`,
      'success',
    );
    showToast('Merge complete. Your bookmarked PDF is downloading.', 'success');
  } catch (error) {
    console.error(error);
    setStatus(`Merge failed: ${error?.message || error}`, 'error');
    showToast('The PDF could not be merged. Check the file list and try again.', 'error');
  } finally {
    setBusy(false);
    window.setTimeout(() => setProgress(0), 1200);
    renderFiles();
  }
}

function moveEntry(id, direction) {
  if (state.busy) return;
  const index = state.entries.findIndex((entry) => entry.id === id);
  const destination = index + direction;
  if (index < 0 || destination < 0 || destination >= state.entries.length) return;
  const [entry] = state.entries.splice(index, 1);
  state.entries.splice(destination, 0, entry);
  renderFiles();
  const movedCard = document.querySelector(`.file-card[data-id="${CSS.escape(id)}"]`);
  const preferredAction = direction < 0 ? 'move-up' : 'move-down';
  const focusTarget = movedCard?.querySelector(
    `button[data-action="${preferredAction}"]:not(:disabled)`,
  ) || movedCard?.querySelector('button:not(:disabled)');
  focusTarget?.focus({ preventScroll: true });
  setStatus(`${entry.file.name} moved to position ${destination + 1}.`, 'ready');
}

function clearDropMarkers() {
  elements.fileList.querySelectorAll('.drop-before, .drop-after').forEach((card) => {
    card.classList.remove('drop-before', 'drop-after');
  });
}

elements.fileInput.addEventListener('change', (event) => addFiles(event.target.files));
elements.addMoreButton.addEventListener('click', () => elements.fileInput.click());
elements.dropZone.addEventListener('click', () => elements.fileInput.click());
elements.dropZone.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    elements.fileInput.click();
  }
});

for (const eventName of ['dragenter', 'dragover']) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!state.busy) elements.dropZone.classList.add('drag-active');
  });
}

for (const eventName of ['dragleave', 'drop']) {
  elements.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.dropZone.classList.remove('drag-active');
  });
}

elements.dropZone.addEventListener('drop', (event) => {
  if (!state.busy) addFiles(event.dataTransfer.files);
});

elements.clearButton.addEventListener('click', () => {
  if (state.busy || state.entries.length === 0) return;
  state.entries = [];
  renderFiles();
  showToast('File list cleared.', 'info');
  elements.dropZone.focus();
});

elements.fileList.addEventListener('input', (event) => {
  if (event.target.dataset.action !== 'bookmark-title') return;
  const id = event.target.closest('.file-card')?.dataset.id;
  const entry = state.entries.find((candidate) => candidate.id === id);
  if (entry) entry.title = event.target.value;
});

elements.fileList.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button || state.busy) return;
  const id = button.closest('.file-card')?.dataset.id;
  const index = state.entries.findIndex((entry) => entry.id === id);
  if (index < 0) return;

  if (button.dataset.action === 'move-up') moveEntry(id, -1);
  if (button.dataset.action === 'move-down') moveEntry(id, 1);
  if (button.dataset.action === 'remove') {
    const [removed] = state.entries.splice(index, 1);
    renderFiles();
    showToast(`${removed.file.name} removed.`, 'info');
  }
});

elements.fileList.addEventListener('dragstart', (event) => {
  if (state.busy) {
    event.preventDefault();
    return;
  }
  const card = event.target.closest('.file-card');
  if (!card) return;
  state.dragId = card.dataset.id;
  card.classList.add('dragging');
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData('text/plain', state.dragId);
});

elements.fileList.addEventListener('dragover', (event) => {
  if (!state.dragId) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = 'move';
  clearDropMarkers();
  const card = event.target.closest('.file-card');
  if (!card || card.dataset.id === state.dragId) return;
  const rect = card.getBoundingClientRect();
  card.classList.add(event.clientY > rect.top + rect.height / 2 ? 'drop-after' : 'drop-before');
});

elements.fileList.addEventListener('drop', (event) => {
  if (!state.dragId || state.busy) return;
  event.preventDefault();
  const targetCard = event.target.closest('.file-card');
  if (targetCard?.dataset.id === state.dragId) {
    state.dragId = null;
    clearDropMarkers();
    return;
  }

  const draggedIndex = state.entries.findIndex((entry) => entry.id === state.dragId);
  if (draggedIndex < 0) return;

  const [dragged] = state.entries.splice(draggedIndex, 1);
  if (!targetCard) {
    state.entries.push(dragged);
  } else {
    const targetIndex = state.entries.findIndex((entry) => entry.id === targetCard.dataset.id);
    const rect = targetCard.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    state.entries.splice(targetIndex + (after ? 1 : 0), 0, dragged);
  }

  state.dragId = null;
  clearDropMarkers();
  renderFiles();
});

elements.fileList.addEventListener('dragend', (event) => {
  event.target.closest('.file-card')?.classList.remove('dragging');
  state.dragId = null;
  clearDropMarkers();
});

elements.preserveBookmarks.addEventListener('change', updateSummary);
elements.openBookmarkPanel.addEventListener('change', updateSummary);
elements.mergeButton.addEventListener('click', mergeAndDownload);

updateSummary();
