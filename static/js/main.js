document.addEventListener('DOMContentLoaded', () => {
    // Mobile Menu Toggle
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const nav = document.querySelector('.main-nav');

    function closeMobileMenu() {
        if (nav) nav.classList.remove('active');
        if (menuToggle) { menuToggle.classList.remove('active'); menuToggle.setAttribute('aria-expanded', 'false'); menuToggle.setAttribute('aria-label', 'Open navigation'); }
        document.body.classList.remove('mobile-nav-open');
        document.querySelectorAll('.nav-item-has-dropdown').forEach(el => el.classList.remove('nav-open'));
    }

    if (menuToggle && nav) {
        menuToggle.addEventListener('click', () => {
            const opening = !nav.classList.contains('active');
            nav.classList.toggle('active');
            menuToggle.classList.toggle('active');
            menuToggle.setAttribute('aria-expanded', String(opening));
            menuToggle.setAttribute('aria-label', opening ? 'Close navigation' : 'Open navigation');
            document.body.classList.toggle('mobile-nav-open', opening);
            if (!nav.classList.contains('active')) {
                document.body.classList.remove('mobile-nav-open');
                document.querySelectorAll('.nav-item-has-dropdown').forEach(el => el.classList.remove('nav-open'));
            }
        });
        const backdrop = document.getElementById('mobileNavBackdrop');
        if (backdrop) backdrop.addEventListener('click', closeMobileMenu);
        // Close menu when a real nav link is clicked (navigate)
        nav.querySelectorAll('a[href]').forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                if (href === '#' || href === '') {
                    e.preventDefault();
                    const parent = link.closest('.nav-item-has-dropdown');
                    if (parent) parent.classList.toggle('nav-open');
                    return;
                }
                closeMobileMenu();
            });
        });
    }

    // Mobile Dropdown Toggle
    const dropdownToggles = document.querySelectorAll('.nav-item-has-dropdown > a');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const parent = toggle.parentElement;
                parent.classList.toggle('active');
            }
        });
    });

    // Smooth Scroll for anchor links (skip href="#" which is not a valid selector)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        const href = anchor.getAttribute('href');
        if (!href || href === '#') return;
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(href);
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: 'smooth' });
        });
    });

    // Intersection Observer for fade-in animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, {
        threshold: 0.1
    });

    document.querySelectorAll('.animate-on-scroll').forEach((el) => {
        observer.observe(el);
    });

    // Profile Dropdown Toggle
    const profileMenu = document.querySelector('.profile-menu');
    const profileIcon = document.querySelector('.profile-icon');

    if (profileIcon) {
        profileIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            profileMenu.classList.toggle('active');
        });

        document.addEventListener('click', (e) => {
            if (profileMenu && !profileMenu.contains(e.target)) {
                profileMenu.classList.remove('active');
            }
        });
    }

    const demoLoginForm = document.querySelector('.profile-dropdown form');
    if (demoLoginForm) {
        demoLoginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(demoLoginForm);
            await fetch(demoLoginForm.action, {method:'POST', body:formData, credentials:'same-origin', redirect:'follow'});
            window.location.reload();
        });
    }



    // Chatbot Widget Logic
    const chatFab = document.getElementById('chatFab');
    const chatWindow = document.getElementById('chatWindow');
    const closeChat = document.getElementById('closeChat');
    const chatInput = document.querySelector('.chat-input-area input');
    const sendBtn = document.querySelector('.chat-input-area button');
    const chatBody = document.getElementById('chatBody');
    const optionBtns = document.querySelectorAll('.chat-option-btn');

    if (chatFab && chatWindow && closeChat) {
        // Enable input
        if (chatInput) chatInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;

        const STORAGE_KEY_STATE = 'chat_is_open';
        const STORAGE_KEY_HISTORY = 'chat_history';

        function saveChatState(isOpen) {
            localStorage.setItem(STORAGE_KEY_STATE, isOpen);
        }

        function saveMessage(type, data) {
            const history = JSON.parse(localStorage.getItem(STORAGE_KEY_HISTORY) || '[]');
            history.push({ type, data });
            localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(history));
        }

        function toggleChat() {
            chatWindow.classList.toggle('active');
            const isOpen = chatWindow.classList.contains('active');
            saveChatState(isOpen);
            if (isOpen && chatInput) {
                chatInput.focus();
            }
        }

        chatFab.addEventListener('click', toggleChat);
        closeChat.addEventListener('click', toggleChat);

        // Chat Logic
        function addMessage(text, isUser = false, save = true) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message');
            msgDiv.classList.add(isUser ? 'user-message' : 'bot-message');
            msgDiv.textContent = text;
            const opts = chatBody.querySelector('.chat-options');
            if (opts) chatBody.insertBefore(msgDiv, opts);
            else chatBody.appendChild(msgDiv);
            chatBody.scrollTop = chatBody.scrollHeight;
            if (save) saveMessage('text', { text, isUser });
        }

        function addSearchProductsLink(userQuery, save = true) {
            if (!userQuery || !chatBody) return;
            const wrap = document.createElement('div');
            wrap.classList.add('message', 'bot-message', 'chat-search-link-wrap');
            const link = document.createElement('a');
            link.href = '/products?search=' + encodeURIComponent(userQuery.trim());
            link.textContent = "Search products for \"" + userQuery.trim().replace(/"/g, '') + "\" \u2192";
            link.classList.add('chat-search-products-link');
            wrap.appendChild(link);
            const opts = chatBody.querySelector('.chat-options');
            if (opts) chatBody.insertBefore(wrap, opts);
            else chatBody.appendChild(wrap);
            chatBody.scrollTop = chatBody.scrollHeight;
            if (save) saveMessage('link', { userQuery });
        }

        // Load Persisted State
        const savedState = localStorage.getItem(STORAGE_KEY_STATE) === 'true';
        if (savedState) {
            chatWindow.classList.add('active');
        }

        const savedHistory = JSON.parse(localStorage.getItem(STORAGE_KEY_HISTORY) || '[]');
        savedHistory.forEach(item => {
            if (item.type === 'text') {
                addMessage(item.data.text, item.data.isUser, false);
            } else if (item.type === 'link') {
                addSearchProductsLink(item.data.userQuery, false);
            }
        });

        async function getBotResponse(input) {
            const url = (typeof window.CHAT_API_URL !== 'undefined' && window.CHAT_API_URL) || '/api/chat';
            try {
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: input })
                });

                const data = await resp.json();

                if (!resp.ok) {
                    // Try to show the specific error message from backend
                    return data.message || data.error || "The assistant is experiencing some technical difficulties. Please try again soon.";
                }

                return data.reply || "I couldn't process that. Please try again or contact support@deshkehaath.in.";
            } catch (e) {
                console.error("Chat API Error:", e);
                return "Connection failed. Please ensure you are logged in and the server is reachable, then try again.";
            }
        }

        async function handleSend() {
            const text = chatInput.value.trim();
            if (text) {
                addMessage(text, true);
                chatInput.value = '';

                const typingIndicator = document.createElement('div');
                typingIndicator.classList.add('message', 'bot-message');
                typingIndicator.textContent = '...';
                typingIndicator.dataset.typing = '1';
                chatBody.appendChild(typingIndicator);
                chatBody.scrollTop = chatBody.scrollHeight;

                const response = await getBotResponse(text);
                typingIndicator.remove();
                addMessage(response, false);
                addSearchProductsLink(text);
            }
        }

        if (sendBtn) {
            sendBtn.addEventListener('click', handleSend);
        }

        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleSend();
            });
        }

        // Handle Option Buttons
        optionBtns.forEach(btn => {
            btn.addEventListener('click', async () => {
                const text = btn.textContent;
                addMessage(text, true);
                const typingIndicator = document.createElement('div');
                typingIndicator.classList.add('message', 'bot-message');
                typingIndicator.textContent = '...';
                typingIndicator.dataset.typing = '1';
                chatBody.appendChild(typingIndicator);
                chatBody.scrollTop = chatBody.scrollHeight;
                const response = await getBotResponse(text);
                typingIndicator.remove();
                addMessage(response, false);
                addSearchProductsLink(text);
            });
        });

    }

    // Dark Mode Toggle
    const themeToggle = document.querySelector('.theme-toggle');
    const body = document.body;
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');

    // Check local storage (Default to Dark)
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark' || !currentTheme) {
        body.classList.add('dark-mode');
        document.documentElement.classList.add('dark-mode');
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            document.documentElement.classList.toggle('dark-mode');

            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            } else {
                localStorage.setItem('theme', 'light');
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            }
        });
    }
});
