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

        const subFolders = ['/about/', '/demo/', '/terms/', '/responsible/', '/privacy/', '/cookies/', '/demo-play/', '/no-deposit/'];
        let pathPrefix = '/';

        subFolders.forEach(folder => {
            if (window.location.pathname.includes(folder)) {
                pathPrefix = '../';
            }
        });

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
            if (config.remove.length > 0) {
                const existingItems = menu.querySelectorAll('li a.hfe-menu-item');
                existingItems.forEach(link => {
                    if (config.remove.includes(link.innerText.trim())) {
                        const li = link.closest('li');
                        if (li) li.remove();
                    }
                });
            }

            config.add.forEach(item => {
                const li = document.createElement('li');
                li.className = 'menu-item menu-item-type-custom menu-item-object-custom parent hfe-creative-menu';

                const a = document.createElement('a');
                a.className = 'hfe-menu-item';
                a.innerText = item.text;
                a.href = item.url;

                const normalizeUrl = (url) => {
                    return url.split(/[?#]/)[0]
                        .replace(/\/$/, "")
                        .replace('index.html', "");
                };

                const currentUrl = normalizeUrl(window.location.href);
                const linkUrl = normalizeUrl(a.href);

                if (currentUrl === linkUrl) {
                    li.classList.add('current-menu-item');
                    a.classList.add('elementor-item-active');
                    a.setAttribute('aria-current', 'page');
                }

                li.appendChild(a);

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
                    answer.style.display = (answer.style.display === 'block') ? 'none' : 'block';
                }
            });
        });
    }
});