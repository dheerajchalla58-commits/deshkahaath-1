/**
 * Client-side auth via localStorage (no external auth provider).
 * Session key: desh_ke_haath_session
 * Users registry: desh_ke_haath_users
 */
(function (global) {
    const USERS_KEY = 'desh_ke_haath_users';
    const SESSION_KEY = 'desh_ke_haath_session';

    function getUsers() {
        try {
            return JSON.parse(localStorage.getItem(USERS_KEY) || '{}');
        } catch {
            return {};
        }
    }

    function saveUsers(users) {
        localStorage.setItem(USERS_KEY, JSON.stringify(users));
    }

    function getSession() {
        try {
            const raw = localStorage.getItem(SESSION_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    }

    function setSession(user) {
        const session = {
            email: user.email,
            name: user.name,
            id: user.id || user.email,
        };
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        return session;
    }

    function clearSession() {
        localStorage.removeItem(SESSION_KEY);
    }

    function isLoggedIn() {
        return !!getSession();
    }

    function signup(name, email, password) {
        email = (email || '').trim().toLowerCase();
        name = (name || '').trim();
        if (!email || !name || !password) {
            return { ok: false, error: 'All fields are required.' };
        }
        if (password.length < 6) {
            return { ok: false, error: 'Password must be at least 6 characters.' };
        }
        const users = getUsers();
        if (users[email]) {
            return { ok: false, error: 'An account with this email already exists.' };
        }
        users[email] = { email, name, password, id: email };
        saveUsers(users);
        setSession(users[email]);
        return { ok: true, user: getSession() };
    }

    function login(email, password) {
        email = (email || '').trim().toLowerCase();
        const users = getUsers();
        const user = users[email];
        if (!user || user.password !== password) {
            return { ok: false, error: 'Invalid email or password.' };
        }
        setSession(user);
        return { ok: true, user: getSession() };
    }

    function logout() {
        clearSession();
    }

    async function syncWithServer() {
        const session = getSession();
        if (!session) {
            return { ok: false };
        }
        try {
            const res = await fetch('/api/auth/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ email: session.email, name: session.name }),
            });
            return await res.json();
        } catch (e) {
            console.warn('Server auth sync failed:', e);
            return { ok: false };
        }
    }

    async function logoutAll() {
        logout();
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                credentials: 'same-origin',
            });
        } catch (e) {
            console.warn('Server logout failed:', e);
        }
    }

    function applyHeaderUI(session) {
        if (!session) return;
        const dropdown = document.querySelector('.profile-dropdown');
        if (!dropdown) return;

        const initial = (session.name || session.email || '?').charAt(0).toUpperCase();
        const profileBtn = document.querySelector('.profile-icon');
        if (profileBtn) {
            profileBtn.innerHTML =
                '<span class="profile-avatar-local" style="width:28px;height:28px;border-radius:50%;background:var(--accent-color,#c45c26);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.85rem;">' +
                initial +
                '</span>';
        }

        dropdown.innerHTML =
            '<span class="dropdown-user">Hello, ' +
            escapeHtml(session.name) +
            '</span>' +
            '<hr style="margin:8px 0;border:0;border-top:1px solid var(--border-color);">' +
            '<a href="/profile" class="dropdown-item">My Profile</a>' +
            '<hr style="margin:8px 0;border:0;border-top:1px solid var(--border-color);">' +
            '<a href="#" class="dropdown-item" id="local-auth-logout">Log Out</a>';

        const logoutLink = document.getElementById('local-auth-logout');
        if (logoutLink) {
            logoutLink.addEventListener('click', async (e) => {
                e.preventDefault();
                await logoutAll();
                window.location.href = '/entry';
            });
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('span');
        div.textContent = text;
        return div.innerHTML;
    }

    async function initPageAuth() {
        // Public project demo: browse first, sign in only when a protected account action is added.
        if (window.location.pathname !== '/profile') return;
        const serverAuth = document.body?.dataset?.serverAuth === 'true';
        if (serverAuth) return;

        if (!isLoggedIn()) return;

        const sync = await syncWithServer();
        if (sync?.ok) {
            document.body.dataset.serverAuth = 'true';
            return;
        }

        applyHeaderUI(getSession());
    }

    global.DeshAuth = {
        getUsers,
        getSession,
        setSession,
        isLoggedIn,
        signup,
        login,
        logout,
        logoutAll,
        syncWithServer,
        applyHeaderUI,
        initPageAuth,
    };
})(window);
