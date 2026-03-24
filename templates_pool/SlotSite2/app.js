(function () {
    var originalConsoleError = console.error;
    var originalConsoleWarn = console.warn;
    console.error = function () { };
    console.warn = function () { };
    window.onerror = function (message, source, lineno, colno, error) { return true; };
    window.addEventListener('unhandledrejection', function (event) {
        event.preventDefault();
        event.stopPropagation();
    }, true);

    window.ElementorProFrontendConfig = {
        ajaxurl: "",
        nonce: "",
        urls: { assets: "wp-content/plugins/elementor-pro/assets/", rest: "" },
        shareButtonsNetworks: {
            facebook: { title: "Facebook", has_counter: true },
            twitter: { title: "Twitter", has_counter: false },
            linkedin: { title: "LinkedIn", has_counter: true },
            pinterest: { title: "Pinterest", has_counter: true }
        },
        facebook_sdk: { lang: "ru_RU", app_id: "" },
        lottie: { defaultAnimationUrl: "" },
        popup: { hasPopUps: false },
        woocommerce: { menu_cart: { cart_page_url: "", checkout_page_url: "" } }
    };

})();

(function () {
    window.addEventListener('load', function () {
        var currentLang = document.documentElement.lang || 'en';
        var langKey = currentLang.split('-')[0].toLowerCase();

        var translations = {
            'en': {
                main: "Main",
            },
        };

        var t = translations[langKey] || translations['en'];

        const subFolders = ['/about/', '/no-deposit/', '/terms/', '/responsible/', '/privacy/', '/cookies/', '/demo-play/'];
        let pathPrefix = '/';

        subFolders.forEach(folder => {
            if (window.location.pathname.includes(folder)) {
                pathPrefix = '../';
            }
        });

        const baseUrl = '';

        const config = {
            menuSelector: 'ul.hfe-nav-menu',
            add: [],

            remove: []
        };

        const menus = document.querySelectorAll(config.menuSelector);

        if (menus.length === 0) {
            const fallbackMenu = document.getElementById('menu-1-198384a3');
            if (fallbackMenu) {
                processMenu(fallbackMenu);
            } else {
                console.log('Menu Manager: Menu not found.');
            }
        } else {
            menus.forEach(menu => processMenu(menu));
        }

        function processMenu(menu) {
    // 1. Нормализуем текущий URL один раз (выносим из цикла для производительности)
    const normalizeUrl = (url) => url.split(/[?#]/)[0].replace(/\/index\.html$/, '').replace(/\/$/, '');
    const currentUrl = normalizeUrl(window.location.href);

    // 2. Удаление ненужных пунктов
    if (config.remove.length > 0) {
        const existingItems = menu.querySelectorAll('li a.hfe-menu-item');
        existingItems.forEach(link => {
            if (config.remove.includes(link.innerText.trim())) {
                const li = link.closest('li');
                if (li) li.remove();
            }
        });
    }

    // 3. Добавление новых пунктов
    config.add.forEach(item => {
        const li = document.createElement('li');
        li.className = 'menu-item menu-item-type-custom menu-item-object-custom parent hfe-creative-menu';

        const a = document.createElement('a');
        a.href = item.url;
        a.className = 'hfe-menu-item';
        a.innerText = item.text;

        // Сравниваем нормализованные URL
        const linkUrl = normalizeUrl(a.href);

        if (currentUrl === linkUrl) {
            // ВАЖНО: Если этот пункт активен, убираем подсветку со ВСЕХ других пунктов в меню
            menu.querySelectorAll('.current-menu-item, .elementor-item-active').forEach(activeEl => {
                activeEl.classList.remove('current-menu-item', 'elementor-item-active');
            });

            // Добавляем подсветку нашему новому пункту
            li.classList.add('current-menu-item');
            a.classList.add('elementor-item-active');
        }

        li.appendChild(a);

        // Вставка в начало или конец
        if (item.position === 'start') {
            menu.insertBefore(li, menu.firstChild);
        } else {
            menu.appendChild(li);
        }
    });
}

    });
})();

document.addEventListener("DOMContentLoaded", function () {
    const links = document.querySelectorAll('a[href="#"]');

    links.forEach(link => {
        if (link.innerText.trim() === "" && link.children.length === 0) {
            link.style.display = "none";
        }
    });

    const faqContainer = document.querySelector('.auto-faq');

    if (faqContainer) {
        const questions = faqContainer.querySelectorAll('h3');

        questions.forEach(question => {
            question.addEventListener('click', function () {
                this.classList.toggle('active');

                const answer = this.nextElementSibling;
                if (answer && answer.tagName === 'P') {
                    if (answer.style.display === 'block') {
                        answer.style.display = 'none';
                    } else {
                        answer.style.display = 'block';
                    }
                }
            });
        });
    }
});