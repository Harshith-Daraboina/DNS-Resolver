document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('queryForm');
    const domainInput = document.getElementById('domainInput');
    const typeSelect = document.getElementById('typeSelect');
    const resolveBtn = document.getElementById('resolveBtn');
    const loadingStatus = document.getElementById('loading');
    const errorAlert = document.getElementById('errorAlert');
    const resultsArea = document.getElementById('resultsArea');
    const recordsList = document.getElementById('recordsList');
    const traceLog = document.getElementById('traceLog');

    const API_BASE_URL = window.API_URL || 'https://dns-resolver-upp3.onrender.com';
    const LOCAL_API_URL = 'http://localhost:8000';

    // Loading Spinner effect
    const spinnerChars = ['|', '/', '-', '\\'];
    let spinnerInt;
    const spinnerSpan = document.querySelector('.spinner');

    function startSpinner() {
        let i = 0;
        loadingStatus.classList.remove('hidden');
        spinnerInt = setInterval(() => {
            spinnerSpan.textContent = spinnerChars[i];
            i = (i + 1) % spinnerChars.length;
        }, 100);
    }

    function stopSpinner() {
        clearInterval(spinnerInt);
        loadingStatus.classList.add('hidden');
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const domain = domainInput.value.trim();
        const type = typeSelect.value;
        if (!domain) return;

        // UI State: Loading
        resolveBtn.disabled = true;
        resolveBtn.textContent = "[WORKING...]";
        errorAlert.classList.add('hidden');
        resultsArea.classList.add('hidden');
        startSpinner();

        try {
            const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
                ? LOCAL_API_URL
                : API_BASE_URL;

            const url = `${baseUrl}/api/resolve?domain=${encodeURIComponent(domain)}&type=${type}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('SYSTEM FAULT: ENDPOINT UNREACHABLE / TIMEOUT_FAILURE');
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            renderResults(data);

        } catch (err) {
            errorAlert.textContent = `${err.message}`;
            errorAlert.classList.remove('hidden');
        } finally {
            // UI State: Reset
            stopSpinner();
            resolveBtn.disabled = false;
            resolveBtn.textContent = "[EXECUTE]";
        }
    });

    function typeWriterEffect(element) {
        element.style.animation = `typeLine 0.1s ease forwards`;
    }

    // Process and render results sequentially to mimic terminal output stream
    async function renderResults(data) {
        resultsArea.classList.remove('hidden');
        traceLog.innerHTML = '';
        recordsList.innerHTML = '';

        // 1. Stream Trace Logs first
        if (data.trace && data.trace.length > 0) {
            for (let i = 0; i < data.trace.length; i++) {
                const logEntry = data.trace[i];
                const div = document.createElement('div');

                let level = "INFO";
                let msg = logEntry;
                if (logEntry.includes(": ")) {
                    const parts = logEntry.split(": ");
                    level = parts[0];
                    msg = parts.slice(1).join(": ");
                }

                div.className = `log-line log-${level}`;

                // Format timestamp prefix
                const now = new Date();
                const timePrefix = `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}] `;

                div.textContent = timePrefix + msg;
                traceLog.appendChild(div);

                typeWriterEffect(div);

                // Auto scroll to bottom
                traceLog.scrollTop = traceLog.scrollHeight;

                // Add artificial delay for that sweet 90s modem feel
                await new Promise(r => setTimeout(r, 60));
            }
        } else {
            const div = document.createElement('div');
            div.className = `log-line log-WARNING`;
            div.textContent = "> NO TRACE DATA RECIEVED.";
            traceLog.appendChild(div);
            typeWriterEffect(div);
        }

        // Wait a small moment before showing final answers
        await new Promise(r => setTimeout(r, 400));

        // 2. Render Final Records
        if (data.records && data.records.length > 0) {
            for (let i = 0; i < data.records.length; i++) {
                const rec = data.records[i];
                const li = document.createElement('li');
                li.className = 'record-item';

                let value = rec.data;
                if (typeof value === 'object' && value.preference !== undefined) {
                    value = `PREF: ${value.preference} | EXCH: ${value.exchange}`;
                }

                // Add brackets around IPv4/IPv6 for aesthetics
                if (data.record_type === 'A' || data.record_type === 'AAAA') {
                    value = `[${value}]`;
                }

                li.innerHTML = `
                    <div class="record-data">
                        <span class="badge">TTL:${rec.ttl}</span>
                        <span class="record-val">${value}</span>
                    </div>
                `;
                recordsList.appendChild(li);
                typeWriterEffect(li);
                await new Promise(r => setTimeout(r, 100));
            }
        } else {
            const li = document.createElement('li');
            li.innerHTML = '<span style="color: var(--text-warning);">RECORD_NOT_FOUND (404)</span>';
            li.className = 'record-item';
            recordsList.appendChild(li);
            typeWriterEffect(li);
        }
    }
});
