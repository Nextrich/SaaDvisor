// Расширенная работа с куки для всех страниц

class CookieManager {
    static set(name, value, days = 365) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + (value || "") + expires + "; path=/";
    }

    static get(name) {
        let nameEQ = name + "=";
        let ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    static delete(name) {
        document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    }

    static saveUserPreferences(preferences) {
        this.set('user_preferences', JSON.stringify(preferences), 365);
    }

    static getUserPreferences() {
        const prefs = this.get('user_preferences');
        return prefs ? JSON.parse(prefs) : null;
    }

    static trackPageVisit(pageName) {
        let visits = this.get('page_visits');
        let visitsObj = visits ? JSON.parse(visits) : {};
        visitsObj[pageName] = (visitsObj[pageName] || 0) + 1;
        this.set('page_visits', JSON.stringify(visitsObj), 30);
    }
}

// Автоматическое отслеживание страниц
document.addEventListener('DOMContentLoaded', () => {
    const pageName = window.location.pathname.split('/').pop() || 'index.html';
    CookieManager.trackPageVisit(pageName);

    // Сохраняем информацию о первом визите
    if (!CookieManager.get('first_visit')) {
        CookieManager.set('first_visit', new Date().toISOString(), 365);
        console.log('Первый визит на сайт зафиксирован');
    }
});