class BlogAPI {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async getPosts(options = {}) {
        const {
            page = 1,
            limit = 10,
            category = null,
            tag = null,
            search = null
        } = options;

        let url = `${this.baseUrl}/api/posts?page=${page}&limit=${limit}`;
        if (category) url += `&category=${category}`;
        if (tag) url += `&tag=${tag}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch posts');
            return await response.json();
        } catch (error) {
            console.error('Error fetching posts:', error);
            throw error;
        }
    }

    async getPost(slug) {
        try {
            const response = await fetch(`${this.baseUrl}/api/post/${slug}`);
            if (!response.ok) throw new Error('Failed to fetch post');
            return await response.json();
        } catch (error) {
            console.error('Error fetching post:', error);
            throw error;
        }
    }

    async incrementShare(postId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/post/${postId}/share`, {
                method: 'POST'
            });
            if (!response.ok) throw new Error('Failed to increment share count');
            return await response.json();
        } catch (error) {
            console.error('Error incrementing share count:', error);
            throw error;
        }
    }
}

class BlogUI {
    constructor(api) {
        this.api = api;
        this.currentPage = 1;
        this.postsPerPage = 6;
        this.totalPosts = 0;
        this.loading = false;
    }

    async initialize() {
        this.setupEventListeners();
        await this.loadPosts();
    }

    setupEventListeners() {
        // Search
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => {
                this.currentPage = 1;
                this.loadPosts();
            }, 300));
        }

        // Category filters
        const categoryFilters = document.querySelectorAll('.category-filter');
        categoryFilters.forEach(filter => {
            filter.addEventListener('click', () => {
                this.currentPage = 1;
                this.loadPosts({ category: filter.dataset.category });
            });
        });

        // Load more button
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.currentPage++;
                this.loadPosts({ append: true });
            });
        }
    }

    async loadPosts(options = {}) {
        if (this.loading) return;
        this.loading = true;

        try {
            const searchQuery = document.getElementById('searchInput')?.value || '';
            const posts = await this.api.getPosts({
                page: this.currentPage,
                limit: this.postsPerPage,
                search: searchQuery,
                category: options.category
            });

            this.renderPosts(posts, options.append);
            this.updatePagination(posts.total);
        } catch (error) {
            this.showError('Failed to load posts');
        } finally {
            this.loading = false;
        }
    }

    renderPosts(posts, append = false) {
        const container = document.getElementById('blogGrid');
        if (!container) return;

        if (!append) container.innerHTML = '';

        posts.data.forEach(post => {
            container.appendChild(this.createPostCard(post));
        });

        this.updateLoadMoreButton(posts.total);
    }

    createPostCard(post) {
        const card = document.createElement('article');
        card.className = 'blog-card';
        card.innerHTML = `
            <img src="${post.featured_image}" alt="${post.title}">
            <div class="blog-card-content">
                <h3>${post.title}</h3>
                <p>${post.excerpt}</p>
                <div class="blog-meta">
                    <span class="date">${new Date(post.created_at).toLocaleDateString()}</span>
                    <div>
                        ${post.tags.map(tag => `
                            <span class="category-tag">${tag}</span>
                        `).join('')}
                    </div>
                </div>
                <a href="/blog/${post.slug}" class="read-more">Read More →</a>
            </div>
        `;
        return card;
    }

    updateLoadMoreButton(total) {
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            const shouldShow = this.currentPage * this.postsPerPage < total;
            loadMoreBtn.style.display = shouldShow ? 'block' : 'none';
        }
    }

    showError(message) {
        const container = document.getElementById('blogGrid');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger">
                    ${message}
                </div>
            `;
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the blog functionality
document.addEventListener('DOMContentLoaded', () => {
    const api = new BlogAPI();
    const ui = new BlogUI(api);
    ui.initialize();
});
