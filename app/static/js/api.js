/**
 * CineConnect Client API Helper
 */

const CineAPI = {
  getToken() {
    return localStorage.getItem("cc_token");
  },

  getUser() {
    try {
      return JSON.parse(localStorage.getItem("cc_user"));
    } catch {
      return null;
    }
  },

  setAuth(token, user) {
    localStorage.setItem("cc_token", token);
    localStorage.setItem("cc_user", JSON.stringify(user));
  },

  clearAuth() {
    localStorage.removeItem("cc_token");
    localStorage.removeItem("cc_user");
  },

  async request(endpoint, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(endpoint, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  initNav() {
    const user = this.getUser();
    const guestLinks = document.getElementById("nav-guest-links");
    const userLinks = document.getElementById("nav-user-links");
    const roleLinks = document.getElementById("nav-role-links");
    const userNameSpan = document.getElementById("nav-user-name");
    const userRoleBadge = document.getElementById("nav-user-role");

    if (user && guestLinks && userLinks) {
      guestLinks.style.display = "none";
      userLinks.style.display = "flex";

      if (userNameSpan) userNameSpan.textContent = user.name;
      if (userRoleBadge) userRoleBadge.textContent = user.role;

      if (roleLinks) {
        let roleHtml = "";
        if (user.role === "FILMMAKER") {
          roleHtml += `<a class="nav-link" href="/filmmaker/dashboard">🎬 My Films</a>`;
        } else if (user.role === "CINEMA") {
          roleHtml += `<a class="nav-link" href="/cinema/dashboard">🏢 Cinema Manager</a>`;
        } else if (user.role === "ADMIN") {
          roleHtml += `<a class="nav-link" href="/admin/dashboard">🛡️ Admin Portal</a>`;
        }
        roleLinks.innerHTML = roleHtml;
      }
    } else if (guestLinks && userLinks) {
      guestLinks.style.display = "flex";
      userLinks.style.display = "none";
    }
  },

  logout() {
    this.clearAuth();
    window.location.href = "/login";
  }
};

document.addEventListener("DOMContentLoaded", () => {
  CineAPI.initNav();
});
