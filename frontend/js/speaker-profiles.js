class SpeakerProfileManager {
    constructor() {
        this.profiles = new Map();
        this.currentProfile = null;
        this.audioRecorder = null;
        this.isRecording = false;
        this.recordedChunks = [];
        
        // Initialize UI elements
        this.initializeUI();
        this.loadProfiles();
        this.setupEventListeners();
    }
    
    initializeUI() {
        // Create modal for profile management
        const modal = document.createElement('div');
        modal.id = 'speaker-profile-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Speaker Profiles</h2>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="profile-list">
                        <h3>Existing Profiles</h3>
                        <div id="profile-cards"></div>
                        <button id="new-profile-btn" class="primary-btn">New Profile</button>
                    </div>
                    <div class="profile-details hidden">
                        <form id="profile-form">
                            <div class="form-group">
                                <label for="profile-name">Name</label>
                                <input type="text" id="profile-name" required>
                            </div>
                            <div class="form-group">
                                <label for="profile-role">Role</label>
                                <input type="text" id="profile-role" required>
                            </div>
                            <div class="voice-samples">
                                <h4>Voice Samples</h4>
                                <div id="samples-list"></div>
                                <div class="recording-controls">
                                    <button type="button" id="record-btn" class="secondary-btn">
                                        Record Sample
                                    </button>
                                    <button type="button" id="upload-btn" class="secondary-btn">
                                        Upload Sample
                                    </button>
                                    <input type="file" id="sample-upload" accept="audio/*" hidden>
                                </div>
                            </div>
                            <div class="voice-characteristics hidden">
                                <h4>Voice Analysis</h4>
                                <div class="characteristics-grid">
                                    <div class="characteristic-card">
                                        <h5>Pitch</h5>
                                        <canvas id="pitch-chart"></canvas>
                                    </div>
                                    <div class="characteristic-card">
                                        <h5>Speech Rate</h5>
                                        <canvas id="rate-chart"></canvas>
                                    </div>
                                    <div class="characteristic-card">
                                        <h5>Voice Quality</h5>
                                        <canvas id="quality-chart"></canvas>
                                    </div>
                                    <div class="characteristic-card">
                                        <h5>Articulation</h5>
                                        <canvas id="articulation-chart"></canvas>
                                    </div>
                                </div>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="primary-btn">Save Profile</button>
                                <button type="button" class="secondary-btn" id="cancel-btn">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    setupEventListeners() {
        // Modal controls
        document.querySelector('#speaker-profile-modal .close-btn')
            .addEventListener('click', () => this.closeModal());
        
        // Profile form
        document.getElementById('profile-form')
            .addEventListener('submit', (e) => this.handleProfileSubmit(e));
        
        // Recording controls
        document.getElementById('record-btn')
            .addEventListener('click', () => this.toggleRecording());
        
        document.getElementById('upload-btn')
            .addEventListener('click', () => 
                document.getElementById('sample-upload').click()
            );
        
        document.getElementById('sample-upload')
            .addEventListener('change', (e) => this.handleFileUpload(e));
        
        // New profile button
        document.getElementById('new-profile-btn')
            .addEventListener('click', () => this.showProfileForm());
        
        // Cancel button
        document.getElementById('cancel-btn')
            .addEventListener('click', () => this.cancelProfileEdit());
    }
    
    async loadProfiles() {
        try {
            const response = await fetch('/api/speakers/profiles');
            const profiles = await response.json();
            
            this.profiles.clear();
            profiles.forEach(profile => {
                this.profiles.set(profile.id, profile);
            });
            
            this.renderProfileCards();
        } catch (error) {
            console.error('Failed to load profiles:', error);
            this.showError('Failed to load speaker profiles');
        }
    }
    
    renderProfileCards() {
        const container = document.getElementById('profile-cards');
        container.innerHTML = '';
        
        this.profiles.forEach((profile, id) => {
            const card = document.createElement('div');
            card.className = 'profile-card';
            card.innerHTML = `
                <div class="profile-info">
                    <h4>${profile.name}</h4>
                    <p>${profile.role}</p>
                    <p class="sample-count">${profile.sample_count} samples</p>
                </div>
                <div class="profile-actions">
                    <button class="edit-btn" data-id="${id}">Edit</button>
                    <button class="delete-btn" data-id="${id}">Delete</button>
                </div>
            `;
            
            // Add event listeners
            card.querySelector('.edit-btn')
                .addEventListener('click', () => this.editProfile(id));
            card.querySelector('.delete-btn')
                .addEventListener('click', () => this.deleteProfile(id));
            
            container.appendChild(card);
        });
    }
    
    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }
    
    async startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioRecorder = new MediaRecorder(stream);
            this.recordedChunks = [];
            
            this.audioRecorder.addEventListener('dataavailable', (e) => {
                if (e.data.size > 0) {
                    this.recordedChunks.push(e.data);
                }
            });
            
            this.audioRecorder.addEventListener('stop', () => {
                const blob = new Blob(this.recordedChunks, { type: 'audio/wav' });
                this.addSample(blob);
            });
            
            this.audioRecorder.start();
            this.isRecording = true;
            
            const recordBtn = document.getElementById('record-btn');
            recordBtn.textContent = 'Stop Recording';
            recordBtn.classList.add('recording');
            
        } catch (error) {
            console.error('Failed to start recording:', error);
            this.showError('Failed to access microphone');
        }
    }
    
    async stopRecording() {
        if (this.audioRecorder && this.isRecording) {
            this.audioRecorder.stop();
            this.isRecording = false;
            
            const recordBtn = document.getElementById('record-btn');
            recordBtn.textContent = 'Record Sample';
            recordBtn.classList.remove('recording');
        }
    }
    
    addSample(blob) {
        const samplesList = document.getElementById('samples-list');
        const sample = document.createElement('div');
        sample.className = 'voice-sample';
        
        const audio = document.createElement('audio');
        audio.controls = true;
        audio.src = URL.createObjectURL(blob);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'delete-sample-btn';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', () => sample.remove());
        
        sample.appendChild(audio);
        sample.appendChild(deleteBtn);
        samplesList.appendChild(sample);
    }
    
    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (file) {
            try {
                const blob = await file.arrayBuffer();
                this.addSample(new Blob([blob], { type: file.type }));
            } catch (error) {
                console.error('Failed to load audio file:', error);
                this.showError('Failed to load audio file');
            }
        }
    }
    
    async handleProfileSubmit(event) {
        event.preventDefault();
        
        const formData = new FormData();
        formData.append('name', document.getElementById('profile-name').value);
        formData.append('role', document.getElementById('profile-role').value);
        
        // Add voice samples
        const samples = document.querySelectorAll('#samples-list audio');
        for (let i = 0; i < samples.length; i++) {
            const response = await fetch(samples[i].src);
            const blob = await response.blob();
            formData.append('audio_samples', blob, `sample_${i}.wav`);
        }
        
        try {
            const url = this.currentProfile ? 
                `/api/speakers/profiles/${this.currentProfile}` :
                '/api/speakers/profiles';
            
            const response = await fetch(url, {
                method: this.currentProfile ? 'PUT' : 'POST',
                body: formData
            });
            
            if (!response.ok) throw new Error('Failed to save profile');
            
            const profile = await response.json();
            this.profiles.set(profile.id, profile);
            this.renderProfileCards();
            this.showProfileList();
            
        } catch (error) {
            console.error('Failed to save profile:', error);
            this.showError('Failed to save speaker profile');
        }
    }
    
    async deleteProfile(id) {
        if (!confirm('Are you sure you want to delete this profile?')) return;
        
        try {
            await fetch(`/api/speakers/profiles/${id}`, { method: 'DELETE' });
            this.profiles.delete(id);
            this.renderProfileCards();
        } catch (error) {
            console.error('Failed to delete profile:', error);
            this.showError('Failed to delete speaker profile');
        }
    }
    
    editProfile(id) {
        const profile = this.profiles.get(id);
        if (!profile) return;
        
        this.currentProfile = id;
        this.showProfileForm();
        
        // Fill form with profile data
        document.getElementById('profile-name').value = profile.name;
        document.getElementById('profile-role').value = profile.role;
        
        // Show voice characteristics if available
        if (profile.voice_characteristics) {
            this.renderVoiceCharacteristics(profile.voice_characteristics);
        }
    }
    
    renderVoiceCharacteristics(characteristics) {
        const container = document.querySelector('.voice-characteristics');
        container.classList.remove('hidden');
        
        // Render pitch chart
        this.renderPitchChart(characteristics.pitch);
        
        // Render speech rate chart
        this.renderSpeechRateChart(characteristics.speech_rate);
        
        // Render voice quality chart
        this.renderVoiceQualityChart(characteristics.voice_quality);
        
        // Render articulation chart
        this.renderArticulationChart(characteristics.articulation);
    }
    
    renderPitchChart(pitchData) {
        const ctx = document.getElementById('pitch-chart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Min', 'Mean', 'Max'],
                datasets: [{
                    label: 'Pitch (Hz)',
                    data: [pitchData.min, pitchData.mean, pitchData.max],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    renderSpeechRateChart(rateData) {
        const ctx = document.getElementById('rate-chart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Syllables/s', 'Articulation Rate'],
                datasets: [{
                    label: 'Speech Rate',
                    data: [
                        rateData.syllables_per_second,
                        rateData.articulation_rate
                    ],
                    backgroundColor: 'rgb(54, 162, 235)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    renderVoiceQualityChart(qualityData) {
        const ctx = document.getElementById('quality-chart').getContext('2d');
        new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Harmonicity', 'Jitter', 'Shimmer'],
                datasets: [{
                    label: 'Voice Quality',
                    data: [
                        qualityData.harmonicity.mean,
                        qualityData.jitter,
                        qualityData.shimmer
                    ],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    renderArticulationChart(articulationData) {
        const ctx = document.getElementById('articulation-chart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Clarity Score'],
                datasets: [{
                    data: [
                        articulationData.clarity_score,
                        1 - articulationData.clarity_score
                    ],
                    backgroundColor: [
                        'rgb(75, 192, 192)',
                        'rgb(201, 203, 207)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    showProfileForm() {
        document.querySelector('.profile-list').classList.add('hidden');
        document.querySelector('.profile-details').classList.remove('hidden');
    }
    
    showProfileList() {
        document.querySelector('.profile-list').classList.remove('hidden');
        document.querySelector('.profile-details').classList.add('hidden');
        this.currentProfile = null;
        
        // Clear form
        document.getElementById('profile-form').reset();
        document.getElementById('samples-list').innerHTML = '';
        document.querySelector('.voice-characteristics').classList.add('hidden');
    }
    
    showError(message) {
        // Implement error notification
        alert(message);
    }
    
    closeModal() {
        document.getElementById('speaker-profile-modal').style.display = 'none';
    }
    
    open() {
        document.getElementById('speaker-profile-modal').style.display = 'block';
    }
}

// Initialize the manager
const speakerProfileManager = new SpeakerProfileManager();
