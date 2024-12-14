class PodcastPlayer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.audio = new Audio();
        this.currentEpisode = null;
        this.isPlaying = false;
        this.progress = 0;
        
        this.initializePlayer();
        this.setupEventListeners();
    }

    initializePlayer() {
        // Create player HTML
        this.container.innerHTML = `
            <div class="podcast-player">
                <div class="player-artwork">
                    <img src="" alt="Episode artwork" id="playerArtwork">
                </div>
                <div class="player-info">
                    <div class="episode-info">
                        <h3 id="playerTitle"></h3>
                        <p id="playerDescription"></p>
                    </div>
                    <div class="player-controls">
                        <button class="btn-backward" title="15 seconds backward">
                            <i class="fas fa-backward-step"></i>
                        </button>
                        <button class="btn-play-pause" title="Play/Pause">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn-forward" title="15 seconds forward">
                            <i class="fas fa-forward-step"></i>
                        </button>
                    </div>
                    <div class="progress-container">
                        <span id="currentTime">00:00</span>
                        <div class="progress-bar">
                            <div class="progress-fill"></div>
                        </div>
                        <span id="duration">00:00</span>
                    </div>
                    <div class="player-options">
                        <div class="playback-rate">
                            <button class="btn-rate" title="Playback speed">1x</button>
                        </div>
                        <div class="volume-control">
                            <i class="fas fa-volume-up"></i>
                            <input type="range" min="0" max="100" value="100" class="volume-slider">
                        </div>
                        <button class="btn-share" title="Share episode">
                            <i class="fas fa-share-alt"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Cache DOM elements
        this.playPauseBtn = this.container.querySelector('.btn-play-pause');
        this.backwardBtn = this.container.querySelector('.btn-backward');
        this.forwardBtn = this.container.querySelector('.btn-forward');
        this.progressBar = this.container.querySelector('.progress-bar');
        this.progressFill = this.container.querySelector('.progress-fill');
        this.currentTimeDisplay = this.container.querySelector('#currentTime');
        this.durationDisplay = this.container.querySelector('#duration');
        this.rateBtn = this.container.querySelector('.btn-rate');
        this.volumeSlider = this.container.querySelector('.volume-slider');
        this.shareBtn = this.container.querySelector('.btn-share');
        this.artwork = this.container.querySelector('#playerArtwork');
        this.titleDisplay = this.container.querySelector('#playerTitle');
        this.descriptionDisplay = this.container.querySelector('#playerDescription');
    }

    setupEventListeners() {
        // Play/Pause
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());

        // Seek backward/forward
        this.backwardBtn.addEventListener('click', () => this.seek(-15));
        this.forwardBtn.addEventListener('click', () => this.seek(15));

        // Progress bar
        this.progressBar.addEventListener('click', (e) => this.setProgress(e));

        // Playback rate
        this.rateBtn.addEventListener('click', () => this.cyclePlaybackRate());

        // Volume
        this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));

        // Share
        this.shareBtn.addEventListener('click', () => this.shareEpisode());

        // Audio events
        this.audio.addEventListener('timeupdate', () => this.updateProgress());
        this.audio.addEventListener('ended', () => this.onEpisodeEnd());
        this.audio.addEventListener('loadedmetadata', () => this.onMetadataLoaded());
    }

    loadEpisode(episode) {
        this.currentEpisode = episode;
        this.audio.src = episode.audioUrl;
        this.artwork.src = episode.artwork;
        this.titleDisplay.textContent = episode.title;
        this.descriptionDisplay.textContent = episode.description;
        
        // Reset player state
        this.progress = 0;
        this.progressFill.style.width = '0%';
        this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        this.isPlaying = false;
        
        // Load saved progress if any
        const savedProgress = this.getSavedProgress(episode.id);
        if (savedProgress) {
            this.audio.currentTime = savedProgress;
        }
    }

    togglePlayPause() {
        if (this.isPlaying) {
            this.audio.pause();
            this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        } else {
            this.audio.play();
            this.playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
        }
        this.isPlaying = !this.isPlaying;
    }

    seek(seconds) {
        this.audio.currentTime = Math.max(0, Math.min(
            this.audio.currentTime + seconds,
            this.audio.duration
        ));
    }

    setProgress(e) {
        const rect = this.progressBar.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        this.audio.currentTime = percent * this.audio.duration;
    }

    updateProgress() {
        if (!this.audio.duration) return;
        
        this.progress = (this.audio.currentTime / this.audio.duration) * 100;
        this.progressFill.style.width = `${this.progress}%`;
        
        this.currentTimeDisplay.textContent = this.formatTime(this.audio.currentTime);
        this.durationDisplay.textContent = this.formatTime(this.audio.duration);
        
        // Save progress every 5 seconds
        if (this.currentEpisode && this.audio.currentTime % 5 < 0.1) {
            this.saveProgress();
        }
    }

    cyclePlaybackRate() {
        const rates = [1, 1.25, 1.5, 1.75, 2];
        const currentRate = this.audio.playbackRate;
        const currentIndex = rates.indexOf(currentRate);
        const nextRate = rates[(currentIndex + 1) % rates.length];
        
        this.audio.playbackRate = nextRate;
        this.rateBtn.textContent = `${nextRate}x`;
    }

    setVolume(value) {
        this.audio.volume = value / 100;
        
        // Update volume icon
        const volumeIcon = this.container.querySelector('.volume-control i');
        if (value > 50) {
            volumeIcon.className = 'fas fa-volume-up';
        } else if (value > 0) {
            volumeIcon.className = 'fas fa-volume-down';
        } else {
            volumeIcon.className = 'fas fa-volume-mute';
        }
    }

    async shareEpisode() {
        if (!this.currentEpisode) return;
        
        const shareData = {
            title: this.currentEpisode.title,
            text: this.currentEpisode.description,
            url: window.location.href
        };

        try {
            if (navigator.share) {
                await navigator.share(shareData);
            } else {
                // Fallback to clipboard
                await navigator.clipboard.writeText(window.location.href);
                alert('Episode link copied to clipboard!');
            }
        } catch (err) {
            console.error('Error sharing:', err);
        }
    }

    saveProgress() {
        if (!this.currentEpisode) return;
        
        const progress = {
            episodeId: this.currentEpisode.id,
            timestamp: Date.now(),
            progress: this.audio.currentTime
        };
        
        localStorage.setItem(
            `podcast_progress_${this.currentEpisode.id}`,
            JSON.stringify(progress)
        );
    }

    getSavedProgress(episodeId) {
        const saved = localStorage.getItem(`podcast_progress_${episodeId}`);
        if (saved) {
            const { progress } = JSON.parse(saved);
            return progress;
        }
        return null;
    }

    onEpisodeEnd() {
        this.isPlaying = false;
        this.playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
        
        // Clear saved progress
        if (this.currentEpisode) {
            localStorage.removeItem(`podcast_progress_${this.currentEpisode.id}`);
        }
        
        // Emit event for playlist handling
        this.container.dispatchEvent(new CustomEvent('episodeEnded', {
            detail: { episodeId: this.currentEpisode?.id }
        }));
    }

    onMetadataLoaded() {
        this.durationDisplay.textContent = this.formatTime(this.audio.duration);
    }

    formatTime(seconds) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hrs > 0) {
            return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

// Example usage:
/*
const player = new PodcastPlayer('playerContainer');

// Load episode
player.loadEpisode({
    id: '123',
    title: 'Example Episode',
    description: 'This is an example episode',
    audioUrl: 'path/to/audio.mp3',
    artwork: 'path/to/artwork.jpg'
});

// Listen for episode end
document.getElementById('playerContainer').addEventListener('episodeEnd', (e) => {
    console.log('Episode ended:', e.detail.episodeId);
    // Load next episode, update UI, etc.
});
*/
