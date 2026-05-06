const API_BASE_URL = 'http://127.0.0.1:5000';
class UrbanWearApi {
    constructor(baseUrl) { this.baseUrl = baseUrl; this.apiUrl = baseUrl; }
    getImageUrl(path) {
        if (!path) return 'https://via.placeholder.com/600x800?text=No+Image';
        if (path.startsWith('http') || path.startsWith('//')) return path;
        return `${this.baseUrl}/${path.startsWith('/') ? path.substring(1) : path}`;
    }
    getAuthToken() { return localStorage.getItem('auth_token'); }
    setAuthToken(token, user) { localStorage.setItem('auth_token', token); localStorage.setItem('user_info', JSON.stringify(user)); }
    clearAuth() { localStorage.removeItem('auth_token'); localStorage.removeItem('user_info'); }
    isLoggedIn() { return !!this.getAuthToken(); }
    getUser() { try { return JSON.parse(localStorage.getItem('user_info')); } catch { return null; } }
    isAdmin() { const u = this.getUser(); return u && u.role && u.role.toLowerCase() === 'admin'; }
    async request(method, endpoint, data = null, token = null) {
        const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
        const t = token || this.getAuthToken();
        if (t) headers['Authorization'] = `Bearer ${t}`;
        const opts = { method, headers };
        if (data && ['POST','PUT','PATCH'].includes(method)) opts.body = JSON.stringify(data);
        try { const res = await fetch(this.baseUrl + endpoint, opts); return await res.json(); }
        catch(e) { return { success: false, message: e.message }; }
    }
    get(ep, token) { return this.request('GET', ep, null, token); }
    post(ep, data, token) { return this.request('POST', ep, data, token); }
    put(ep, data, token) { return this.request('PUT', ep, data, token); }
    patch(ep, data, token) { return this.request('PATCH', ep, data, token); }
    delete(ep, token) { return this.request('DELETE', ep, null, token); }
}
window.API = new UrbanWearApi(API_BASE_URL);
window.IS_LOGGED_IN = window.API.isLoggedIn();
window.AUTH_TOKEN = window.API.getAuthToken() || '';
