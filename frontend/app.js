document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('queryForm');
    const domainInput = document.getElementById('domainInput');
    const typeSelect = document.getElementById('typeSelect');
    const resolveBtn = document.getElementById('resolveBtn');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');
    const errorAlert = document.getElementById('errorAlert');
    const resultsArea = document.getElementById('resultsArea');
    const recordsList = document.getElementById('recordsList');
    const traceLog = document.getElementById('traceLog');

    // Use environment variable if available (for production build step injection) or fallback to local
    // In Vanilla JS, you'd usually replace this string in your CI/CD pipeline.
    const API_BASE_URL = window.API_URL || 'https://dns-resolver-upp3.onrender.com';
    // For local testing:
    const LOCAL_API_URL = 'http://localhost:8000';

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const domain = domainInput.value.trim();
        const type = typeSelect.value;
        if (!domain) return;

        // UI State: Loading
        btnText.classList.add('disabled');
        spinner.classList.remove('disabled');
        resolveBtn.disabled = true;
        errorAlert.classList.add('hidden');
        resultsArea.classList.add('hidden');

        try {
            // Priority to LOCAL_API_URL for local testing if running on localhost
            const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
                ? LOCAL_API_URL
                : API_BASE_URL;

            const url = `${baseUrl}/api/resolve?domain=${encodeURIComponent(domain)}&type=${type}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            renderResults(data);

        } catch (err) {
            errorAlert.textContent = `Error: ${err.message}`;
            errorAlert.classList.remove('hidden');
        } finally {
            // UI State: Reset
            btnText.classList.remove('disabled');
            spinner.classList.add('disabled');
            resolveBtn.disabled = false;
        }
    });

    function renderResults(data) {
        // Render Records
        recordsList.innerHTML = '';
        if (data.records && data.records.length > 0) {
            data.records.forEach((rec, index) => {
                const li = document.createElement('li');
                li.className = 'record-item';
                // Add staggered animation delay
                li.style.animation = `fadeIn ${0.3 + (index * 0.1)}s ease forwards`;

                let value = rec.data;
                if (typeof value === 'object' && value.preference !== undefined) {
                    value = `Pref: ${value.preference} | ${value.exchange}`;
                }

                li.innerHTML = `
                    <span class="badge">TTL: ${rec.ttl}s</span>
                    <span class="record-val">${value}</span>
                `;
                recordsList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.innerHTML = '<span style="color: var(--text-muted); font-style: italic;">No records found.</span>';
            recordsList.appendChild(li);
        }

        // Render Trace Log
        traceLog.innerHTML = '';
        if (data.trace && data.trace.length > 0) {
            data.trace.forEach((logEntry, index) => {
                const div = document.createElement('div');

                // Extract level (e.g., "INFO: msg")
                let level = "INFO";
                let msg = logEntry;
                if (logEntry.includes(": ")) {
                    const parts = logEntry.split(": ");
                    level = parts[0];
                    msg = parts.slice(1).join(": ");
                }

                div.className = `log-line log-${level}`;
                div.textContent = msg;
                div.style.animationDelay = `${index * 0.05}s`;
                traceLog.appendChild(div);
            });
        }

        // Show Results
        resultsArea.classList.remove('hidden');
    }
});
