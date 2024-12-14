class SocialShare {
    constructor(options = {}) {
        this.networks = {
            facebook: {
                name: 'Facebook',
                shareUrl: 'https://www.facebook.com/sharer/sharer.php?u={url}&quote={text}',
                icon: 'fab fa-facebook'
            },
            twitter: {
                name: 'Twitter',
                shareUrl: 'https://twitter.com/intent/tweet?url={url}&text={text}',
                icon: 'fab fa-twitter'
            },
            linkedin: {
                name: 'LinkedIn',
                shareUrl: 'https://www.linkedin.com/sharing/share-offsite/?url={url}',
                icon: 'fab fa-linkedin'
            },
            whatsapp: {
                name: 'WhatsApp',
                shareUrl: 'https://api.whatsapp.com/send?text={text}%20{url}',
                icon: 'fab fa-whatsapp'
            },
            email: {
                name: 'Email',
                shareUrl: 'mailto:?subject={title}&body={text}%20{url}',
                icon: 'fas fa-envelope'
            }
        };

        this.options = {
            containerClass: 'social-share-buttons',
            buttonClass: 'share-button',
            iconOnly: false,
            networks: ['facebook', 'twitter', 'linkedin', 'whatsapp', 'email'],
            ...options
        };
    }

    createShareButtons(container, data) {
        const shareContainer = document.createElement('div');
        shareContainer.className = this.options.containerClass;

        this.options.networks.forEach(network => {
            if (this.networks[network]) {
                const button = this.createButton(network, data);
                shareContainer.appendChild(button);
            }
        });

        container.appendChild(shareContainer);
    }

    createButton(network, data) {
        const button = document.createElement('button');
        button.className = `${this.options.buttonClass} ${network}`;
        button.setAttribute('data-network', network);
        
        const icon = document.createElement('i');
        icon.className = this.networks[network].icon;
        button.appendChild(icon);

        if (!this.options.iconOnly) {
            const text = document.createElement('span');
            text.textContent = ` Share on ${this.networks[network].name}`;
            button.appendChild(text);
        }

        button.addEventListener('click', (e) => {
            e.preventDefault();
            this.share(network, data);
        });

        return button;
    }

    async share(network, data) {
        const { url, title, text, image } = data;
        
        // Track share attempt
        this.trackShare(network, url);

        try {
            // Try native share API first on mobile
            if (navigator.share && this.isMobile()) {
                await navigator.share({
                    title: title,
                    text: text,
                    url: url
                });
                this.onShareSuccess(network, url);
                return;
            }

            // Fallback to network-specific sharing
            const shareUrl = this.buildShareUrl(network, {
                url: encodeURIComponent(url),
                title: encodeURIComponent(title),
                text: encodeURIComponent(text),
                image: encodeURIComponent(image || '')
            });

            const windowOptions = {
                width: 600,
                height: 400,
                left: (window.innerWidth - 600) / 2,
                top: (window.innerHeight - 400) / 2
            };

            if (network === 'email') {
                window.location.href = shareUrl;
            } else {
                window.open(
                    shareUrl,
                    `share_${network}`,
                    Object.keys(windowOptions)
                        .map(key => `${key}=${windowOptions[key]}`)
                        .join(',')
                );
            }

            this.onShareSuccess(network, url);
        } catch (error) {
            console.error('Share failed:', error);
            this.onShareError(network, url, error);
        }
    }

    buildShareUrl(network, data) {
        let shareUrl = this.networks[network].shareUrl;
        
        Object.keys(data).forEach(key => {
            shareUrl = shareUrl.replace(`{${key}}`, data[key]);
        });
        
        return shareUrl;
    }

    trackShare(network, url) {
        // Send share attempt to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'share', {
                method: network,
                content_type: 'episode',
                content_id: url
            });
        }
    }

    onShareSuccess(network, url) {
        // Track successful share
        if (typeof gtag !== 'undefined') {
            gtag('event', 'share_complete', {
                method: network,
                content_type: 'episode',
                content_id: url
            });
        }

        // Update share count on server
        this.updateShareCount(url);

        // Dispatch success event
        document.dispatchEvent(new CustomEvent('shareSuccess', {
            detail: { network, url }
        }));
    }

    onShareError(network, url, error) {
        console.error(`Share failed on ${network}:`, error);
        
        // Track share error
        if (typeof gtag !== 'undefined') {
            gtag('event', 'share_error', {
                method: network,
                content_type: 'episode',
                content_id: url,
                error_message: error.message
            });
        }

        // Dispatch error event
        document.dispatchEvent(new CustomEvent('shareError', {
            detail: { network, url, error }
        }));
    }

    async updateShareCount(url) {
        try {
            const response = await fetch('/api/share-count', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update share count');
            }
            
            const data = await response.json();
            this.updateShareCountDisplay(data.count);
        } catch (error) {
            console.error('Failed to update share count:', error);
        }
    }

    updateShareCountDisplay(count) {
        const countElement = document.querySelector('.share-count');
        if (countElement) {
            countElement.textContent = count;
        }
    }

    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    addCopyLinkButton(container, data) {
        const button = document.createElement('button');
        button.className = `${this.options.buttonClass} copy-link`;
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-link';
        button.appendChild(icon);

        if (!this.options.iconOnly) {
            const text = document.createElement('span');
            text.textContent = ' Copy Link';
            button.appendChild(text);
        }

        button.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await navigator.clipboard.writeText(data.url);
                
                // Show success feedback
                const originalText = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                
                setTimeout(() => {
                    button.innerHTML = originalText;
                }, 2000);
                
                // Track copy
                if (typeof gtag !== 'undefined') {
                    gtag('event', 'share', {
                        method: 'copy_link',
                        content_type: 'episode',
                        content_id: data.url
                    });
                }
            } catch (error) {
                console.error('Failed to copy link:', error);
            }
        });

        container.querySelector(`.${this.options.containerClass}`).appendChild(button);
    }
}

// Example usage:
/*
const shareButtons = new SocialShare({
    iconOnly: true,
    networks: ['facebook', 'twitter', 'linkedin', 'whatsapp']
});

shareButtons.createShareButtons(document.getElementById('shareContainer'), {
    url: window.location.href,
    title: 'Check out this amazing episode!',
    text: 'I just listened to this great podcast episode about spiritual business practices.',
    image: 'path/to/episode/image.jpg'
});

// Add copy link button
shareButtons.addCopyLinkButton(document.getElementById('shareContainer'), {
    url: window.location.href
});

// Listen for share events
document.addEventListener('shareSuccess', (e) => {
    console.log(`Successfully shared on ${e.detail.network}`);
});

document.addEventListener('shareError', (e) => {
    console.log(`Failed to share on ${e.detail.network}:`, e.detail.error);
});
*/
