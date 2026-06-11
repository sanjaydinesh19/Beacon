<script lang="ts">
	type Phase = 'idle' | 'recording' | 'transcribing' | 'review' | 'saving' | 'saved' | 'error';

	let phase: Phase = 'idle';
	let transcript = '';
	let savedUrl = '';
	let errorMsg = '';
	let entryDate = new Date().toISOString().slice(0, 10);

	let mediaRecorder: MediaRecorder | null = null;
	let chunks: Blob[] = [];
	let recordDuration = 0;
	let durationTimer: ReturnType<typeof setInterval>;

	async function startRecording() {
		errorMsg = '';
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			mediaRecorder = new MediaRecorder(stream);
			chunks = [];
			recordDuration = 0;

			mediaRecorder.ondataavailable = (e) => {
				if (e.data.size > 0) chunks.push(e.data);
			};
			mediaRecorder.onstop = sendAudio;
			mediaRecorder.start(250);

			durationTimer = setInterval(() => recordDuration++, 1000);
			phase = 'recording';
		} catch (e: any) {
			errorMsg = 'Microphone access denied. Please allow mic permissions.';
			phase = 'error';
		}
	}

	function stopRecording() {
		clearInterval(durationTimer);
		mediaRecorder?.stop();
		mediaRecorder?.stream.getTracks().forEach((t) => t.stop());
		phase = 'transcribing';
	}

	async function sendAudio() {
		const blob = new Blob(chunks, { type: 'audio/webm' });
		const form = new FormData();
		form.append('audio', blob, 'recording.webm');

		try {
			const res = await fetch('/api/journal/transcribe', { method: 'POST', body: form });
			const data = await res.json();
			if (!res.ok) throw new Error(data.detail ?? 'Transcription failed');
			transcript = data.transcript;
			phase = 'review';
		} catch (e: any) {
			errorMsg = e.message;
			phase = 'error';
		}
	}

	async function saveToNotion() {
		phase = 'saving';
		errorMsg = '';

		try {
			const res = await fetch('/api/journal/save', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ transcript, entry_date: entryDate })
			});
			const data = await res.json();
			if (!res.ok) throw new Error(data.detail ?? 'Save failed');
			savedUrl = data.url;
			phase = 'saved';
		} catch (e: any) {
			errorMsg = e.message;
			phase = 'error';
		}
	}

	function reset() {
		phase = 'idle';
		transcript = '';
		savedUrl = '';
		errorMsg = '';
		entryDate = new Date().toISOString().slice(0, 10);
	}

	function fmt(s: number) {
		const m = Math.floor(s / 60).toString().padStart(2, '0');
		const sec = (s % 60).toString().padStart(2, '0');
		return `${m}:${sec}`;
	}
</script>

<svelte:head>
	<title>Journal — Beacon</title>
</svelte:head>

<div class="page">
	<header>
		<h1>Journal</h1>
		<p class="subtitle">Record, review, and save your daily entry.</p>
	</header>

	<div class="card">
		<!-- Date picker row -->
		<div class="date-row">
			<label for="entry-date">Entry date</label>
			<input
				id="entry-date"
				type="date"
				bind:value={entryDate}
				disabled={phase === 'recording' || phase === 'transcribing' || phase === 'saving'}
			/>
		</div>

		<!-- Main recorder area -->
		<div class="recorder">
			{#if phase === 'idle'}
				<button class="mic-btn" on:click={startRecording} aria-label="Start recording">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
						<rect x="9" y="2" width="6" height="13" rx="3" />
						<path d="M5 10a7 7 0 0 0 14 0" />
						<line x1="12" y1="17" x2="12" y2="22" />
						<line x1="9" y1="22" x2="15" y2="22" />
					</svg>
				</button>
				<p class="hint">Tap to start recording</p>

			{:else if phase === 'recording'}
				<button class="mic-btn recording pulse" on:click={stopRecording} aria-label="Stop recording">
					<svg viewBox="0 0 24 24" fill="currentColor">
						<rect x="7" y="7" width="10" height="10" rx="2" />
					</svg>
				</button>
				<p class="hint recording-hint">
					<span class="dot"></span>
					Recording — {fmt(recordDuration)}
				</p>
				<p class="sub-hint">Tap to stop</p>

			{:else if phase === 'transcribing'}
				<div class="spinner-wrap">
					<div class="spinner"></div>
				</div>
				<p class="hint">Transcribing…</p>

			{:else if phase === 'review'}
				<div class="transcript-area">
					<label for="transcript">Transcript — edit before saving</label>
					<textarea id="transcript" bind:value={transcript} rows={10} spellcheck="true"></textarea>
				</div>
				<div class="review-actions">
					<button class="btn-secondary" on:click={reset}>Discard</button>
					<button class="btn-primary" on:click={saveToNotion}>Send to Notion →</button>
				</div>

			{:else if phase === 'saving'}
				<div class="spinner-wrap">
					<div class="spinner"></div>
				</div>
				<p class="hint">Saving to Notion…</p>

			{:else if phase === 'saved'}
				<div class="saved-state">
					<span class="check">✓</span>
					<p class="hint">Saved!</p>
					{#if savedUrl}
						<a href={savedUrl} target="_blank" rel="noopener">Open in Notion →</a>
					{/if}
					<button class="btn-secondary" on:click={reset}>New entry</button>
				</div>

			{:else if phase === 'error'}
				<div class="error-state">
					<p class="error-msg">{errorMsg}</p>
					<button class="btn-secondary" on:click={reset}>Try again</button>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.page {
		max-width: 680px;
		display: flex;
		flex-direction: column;
		gap: 32px;
	}

	header h1 {
		font-size: 26px;
		font-weight: 700;
		margin-bottom: 6px;
	}

	.subtitle {
		color: var(--text-muted);
		font-size: 14px;
	}

	.card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 28px 32px;
		display: flex;
		flex-direction: column;
		gap: 28px;
	}

	.date-row {
		display: flex;
		align-items: center;
		gap: 14px;
	}

	.date-row label {
		font-size: 13px;
		color: var(--text-muted);
		font-weight: 500;
		white-space: nowrap;
	}

	.date-row input {
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--text);
		padding: 6px 10px;
		font-size: 13px;
		outline: none;
	}

	.date-row input:focus {
		border-color: var(--accent);
	}

	.recorder {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 16px;
		min-height: 260px;
		justify-content: center;
	}

	.mic-btn {
		width: 80px;
		height: 80px;
		border-radius: 50%;
		background: var(--surface-2);
		border: 2px solid var(--border);
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
		transition: all 0.2s;
	}

	.mic-btn:hover {
		border-color: var(--accent);
		color: var(--accent);
		background: var(--accent-dim);
	}

	.mic-btn svg {
		width: 30px;
		height: 30px;
	}

	.mic-btn.recording {
		background: #e05c5c22;
		border-color: var(--red);
		color: var(--red);
	}

	@keyframes pulse {
		0%, 100% { box-shadow: 0 0 0 0 #e05c5c44; }
		50% { box-shadow: 0 0 0 14px #e05c5c00; }
	}

	.pulse {
		animation: pulse 1.4s ease-in-out infinite;
	}

	.hint {
		font-size: 14px;
		color: var(--text-muted);
		text-align: center;
	}

	.sub-hint {
		font-size: 12px;
		color: var(--text-muted);
		opacity: 0.6;
	}

	.recording-hint {
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--red);
	}

	.dot {
		width: 8px;
		height: 8px;
		background: var(--red);
		border-radius: 50%;
		animation: pulse 1s ease-in-out infinite;
	}

	.spinner-wrap {
		width: 80px;
		height: 80px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 3px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.transcript-area {
		width: 100%;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.transcript-area label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-muted);
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}

	.transcript-area textarea {
		width: 100%;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 8px;
		color: var(--text);
		padding: 14px 16px;
		resize: vertical;
		outline: none;
		line-height: 1.65;
	}

	.transcript-area textarea:focus {
		border-color: var(--accent);
	}

	.review-actions {
		display: flex;
		gap: 10px;
		justify-content: flex-end;
		width: 100%;
	}

	.btn-primary {
		background: var(--accent);
		color: #0a0a0f;
		border: none;
		border-radius: 8px;
		padding: 10px 20px;
		font-weight: 600;
		font-size: 14px;
		transition: opacity 0.15s;
	}

	.btn-primary:hover {
		opacity: 0.85;
	}

	.btn-secondary {
		background: var(--surface-2);
		color: var(--text-muted);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 10px 20px;
		font-size: 14px;
		transition: all 0.15s;
	}

	.btn-secondary:hover {
		color: var(--text);
		border-color: var(--text-muted);
	}

	.saved-state,
	.error-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
	}

	.check {
		font-size: 36px;
		color: var(--green);
	}

	.error-msg {
		color: var(--red);
		font-size: 14px;
		text-align: center;
		max-width: 400px;
	}
</style>
