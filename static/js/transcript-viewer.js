class TranscriptViewer {
    constructor(options = {}) {
        this.options = {
            containerId: 'transcript-container',
            searchId: 'transcript-search',
            downloadId: 'transcript-download',
            highlightClass: 'highlight',
            activeClass: 'active',
            timestampClass: 'timestamp',
            segmentClass: 'segment',
            autoScroll: true,
            searchDelay: 300,
            scrollOffset: 100,
            player: null, // Reference to PodcastPlayer instance
            ...options
        };

        this.container = document.getElementById(this.options.containerId);
        this.searchInput = document.getElementById(this.options.searchId);
        this.downloadBtn = document.getElementById(this.options.downloadId);
        this.transcript = [];
        this.currentSegment = null;
        this.searchTimeout = null;
        this.searchResults = [];
        this.currentSearchIndex = -1;

        this.initializeViewer();
    }

    initializeViewer() {
        // Create viewer structure
        this.container.innerHTML = `
            <div class="transcript-controls">
                <div class="search-container">
                    <input type="text" id="${this.options.searchId}" 
                           placeholder="Search transcript...">
                    <div class="search-results">
                        <span class="result-count"></span>
                        <button class="prev-result" disabled>↑</button>
                        <button class="next-result" disabled>↓</button>
                    </div>
                </div>
                <div class="transcript-options">
                    <button id="${this.options.downloadId}">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <div class="format-selector">
                        <select>
                            <option value="txt">Text</option>
                            <option value="srt">SRT</option>
                            <option value="vtt">VTT</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="transcript-content"></div>
        `;

        // Cache DOM elements
        this.content = this.container.querySelector('.transcript-content');
        this.resultCount = this.container.querySelector('.result-count');
        this.prevButton = this.container.querySelector('.prev-result');
        this.nextButton = this.container.querySelector('.next-result');
        this.formatSelect = this.container.querySelector('.format-selector select');

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Search functionality
        this.searchInput.addEventListener('input', () => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.performSearch(this.searchInput.value);
            }, this.options.searchDelay);
        });

        // Search navigation
        this.prevButton.addEventListener('click', () => this.navigateSearch('prev'));
        this.nextButton.addEventListener('click', () => this.navigateSearch('next'));

        // Download functionality
        this.downloadBtn.addEventListener('click', () => {
            this.downloadTranscript(this.formatSelect.value);
        });

        // Segment click handling
        this.content.addEventListener('click', (e) => {
            const segment = e.target.closest(`.${this.options.segmentClass}`);
            if (segment) {
                const time = parseFloat(segment.dataset.time);
                if (this.options.player) {
                    this.options.player.audio.currentTime = time;
                    if (!this.options.player.isPlaying) {
                        this.options.player.togglePlayPause();
                    }
                }
            }
        });

        // Player time update handling
        if (this.options.player) {
            this.options.player.audio.addEventListener('timeupdate', () => {
                this.highlightCurrentSegment(this.options.player.audio.currentTime);
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (document.activeElement === this.searchInput) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if (e.shiftKey) {
                        this.navigateSearch('prev');
                    } else {
                        this.navigateSearch('next');
                    }
                }
                if (e.key === 'Escape') {
                    this.searchInput.value = '';
                    this.clearSearch();
                }
            }
        });
    }

    loadTranscript(transcript) {
        this.transcript = transcript;
        this.renderTranscript();
    }

    renderTranscript() {
        this.content.innerHTML = this.transcript.map((segment, index) => `
            <div class="${this.options.segmentClass}" 
                 data-time="${segment.start}" 
                 data-index="${index}">
                <span class="${this.options.timestampClass}">
                    ${this.formatTimestamp(segment.start)}
                </span>
                <span class="text">${segment.text}</span>
            </div>
        `).join('');
    }

    highlightCurrentSegment(currentTime) {
        const segments = this.content.querySelectorAll(`.${this.options.segmentClass}`);
        let activeSegment = null;

        segments.forEach(segment => {
            const time = parseFloat(segment.dataset.time);
            const nextTime = segment.nextElementSibling ? 
                parseFloat(segment.nextElementSibling.dataset.time) : Infinity;

            if (currentTime >= time && currentTime < nextTime) {
                activeSegment = segment;
            }
            segment.classList.remove(this.options.activeClass);
        });

        if (activeSegment && activeSegment !== this.currentSegment) {
            this.currentSegment = activeSegment;
            activeSegment.classList.add(this.options.activeClass);

            if (this.options.autoScroll) {
                this.scrollToSegment(activeSegment);
            }
        }
    }

    scrollToSegment(segment) {
        const containerRect = this.content.getBoundingClientRect();
        const segmentRect = segment.getBoundingClientRect();

        if (segmentRect.top < containerRect.top || 
            segmentRect.bottom > containerRect.bottom) {
            this.content.scrollTo({
                top: segment.offsetTop - this.options.scrollOffset,
                behavior: 'smooth'
            });
        }
    }

    performSearch(query) {
        this.clearSearch();
        
        if (!query) return;

        const searchRegex = new RegExp(query, 'gi');
        const segments = this.content.querySelectorAll(`.${this.options.segmentClass}`);

        segments.forEach(segment => {
            const text = segment.querySelector('.text');
            const content = text.textContent;
            const matches = [...content.matchAll(searchRegex)];

            if (matches.length > 0) {
                this.searchResults.push(segment);
                let highlightedContent = content;
                let offset = 0;

                matches.forEach(match => {
                    const start = match.index + offset;
                    const end = start + match[0].length;
                    const highlight = `<mark class="${this.options.highlightClass}">${
                        highlightedContent.slice(start, end)
                    }</mark>`;
                    
                    highlightedContent = 
                        highlightedContent.slice(0, start) + 
                        highlight + 
                        highlightedContent.slice(end);
                    
                    offset += highlight.length - match[0].length;
                });

                text.innerHTML = highlightedContent;
            }
        });

        this.updateSearchNavigation();
    }

    navigateSearch(direction) {
        if (!this.searchResults.length) return;

        if (direction === 'next') {
            this.currentSearchIndex = 
                (this.currentSearchIndex + 1) % this.searchResults.length;
        } else {
            this.currentSearchIndex = 
                (this.currentSearchIndex - 1 + this.searchResults.length) % 
                this.searchResults.length;
        }

        const segment = this.searchResults[this.currentSearchIndex];
        this.scrollToSegment(segment);
        this.updateSearchNavigation();
    }

    updateSearchNavigation() {
        const count = this.searchResults.length;
        this.resultCount.textContent = count ? 
            `${this.currentSearchIndex + 1} of ${count} results` : 
            'No results';

        this.prevButton.disabled = count === 0;
        this.nextButton.disabled = count === 0;
    }

    clearSearch() {
        const segments = this.content.querySelectorAll(`.${this.options.segmentClass}`);
        segments.forEach(segment => {
            const text = segment.querySelector('.text');
            text.textContent = text.textContent;
        });

        this.searchResults = [];
        this.currentSearchIndex = -1;
        this.updateSearchNavigation();
    }

    downloadTranscript(format) {
        let content = '';
        const filename = `transcript.${format}`;

        switch (format) {
            case 'txt':
                content = this.transcript.map(segment => 
                    `${this.formatTimestamp(segment.start)}\n${segment.text}\n`
                ).join('\n');
                break;

            case 'srt':
                content = this.transcript.map((segment, index) => 
                    `${index + 1}\n${
                        this.formatSrtTimestamp(segment.start)
                    } --> ${
                        this.formatSrtTimestamp(segment.end || 
                            this.transcript[index + 1]?.start || 
                            segment.start + 5)
                    }\n${segment.text}\n`
                ).join('\n');
                break;

            case 'vtt':
                content = `WEBVTT\n\n${
                    this.transcript.map((segment, index) => 
                        `${this.formatVttTimestamp(segment.start)} --> ${
                            this.formatVttTimestamp(segment.end || 
                                this.transcript[index + 1]?.start || 
                                segment.start + 5)
                        }\n${segment.text}\n`
                    ).join('\n')
                }`;
                break;
        }

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    formatTimestamp(seconds) {
        const date = new Date(seconds * 1000);
        const mm = date.getUTCMinutes().toString().padStart(2, '0');
        const ss = date.getUTCSeconds().toString().padStart(2, '0');
        return `${mm}:${ss}`;
    }

    formatSrtTimestamp(seconds) {
        const date = new Date(seconds * 1000);
        const hh = date.getUTCHours().toString().padStart(2, '0');
        const mm = date.getUTCMinutes().toString().padStart(2, '0');
        const ss = date.getUTCSeconds().toString().padStart(2, '0');
        const ms = date.getUTCMilliseconds().toString().padStart(3, '0');
        return `${hh}:${mm}:${ss},${ms}`;
    }

    formatVttTimestamp(seconds) {
        const date = new Date(seconds * 1000);
        const hh = date.getUTCHours().toString().padStart(2, '0');
        const mm = date.getUTCMinutes().toString().padStart(2, '0');
        const ss = date.getUTCSeconds().toString().padStart(2, '0');
        const ms = date.getUTCMilliseconds().toString().padStart(3, '0');
        return `${hh}:${mm}:${ss}.${ms}`;
    }
}

// Example usage:
/*
const player = new PodcastPlayer('playerContainer');
const transcript = new TranscriptViewer({
    containerId: 'transcript-container',
    player: player
});

// Load transcript
transcript.loadTranscript([
    { start: 0, text: "Welcome to our podcast!" },
    { start: 3.5, text: "Today we're discussing spiritual business practices." },
    // ... more segments
]);
*/
