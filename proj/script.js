// Общие функции для всех страниц

// Работа с куки
function setCookie(name, value, days) {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}

function getCookie(name) {
    let nameEQ = name + "=";
    let ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Инициализация куки-баннера
function initCookieBanner() {
    const cookieBanner = document.getElementById('cookieBanner');
    const acceptBtn = document.getElementById('acceptCookieBtn');

    if (!cookieBanner) return;

    const consent = getCookie('cookies_consent');
    if (consent === 'true') {
        cookieBanner.classList.add('hidden');
    }

    if (acceptBtn) {
        acceptBtn.addEventListener('click', () => {
            setCookie('cookies_consent', 'true', 365);
            cookieBanner.classList.add('hidden');
        });
    }
}

// Подсветка активной страницы в меню
function highlightActivePage() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = {
        'index.html': 'nav-landing',
        'tariffs.html': 'nav-subs',
        'account.html': 'nav-account',
        'promotions.html': 'nav-promo',
        'faq.html': 'nav-faq',
        'tips.html': 'nav-tips'
    };

    const activeId = navLinks[currentPage];
    if (activeId) {
        const activeLink = document.getElementById(activeId);
        if (activeLink) activeLink.classList.add('active-page');
    }
}

// Анимация при скролле
function initScrollAnimation() {
    const fadeElements = document.querySelectorAll('.fade-on-scroll');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-up');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    fadeElements.forEach(el => observer.observe(el));
}

// Запуск при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    initCookieBanner();
    highlightActivePage();
    initScrollAnimation();
});