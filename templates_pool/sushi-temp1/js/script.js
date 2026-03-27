window.addEventListener('load', function () {
    initPreloader();
});

document.addEventListener('DOMContentLoaded', function () {
    initHeader();
    initMobileMenu();
    initMobileDropdown();
    initAutoFAQ();
    initFAQ();
    initSmoothScroll();
    initScrollAnimations();
    initGameCardHover();
    initScrollToTop();
    initSectionShapes();
    initTableOfContents();
    initDynamicNav();
});

function initHeader() {
    const header = document.querySelector('.header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll > 50) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }

        if (document.body.classList.contains('menu-open')) {
            header.style.transform = 'translateY(0)';
            lastScroll = currentScroll;
            return;
        }

        if (currentScroll > lastScroll && currentScroll > 200) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }

        lastScroll = currentScroll;
    });
}

function initMobileMenu() {
    const menuToggle = document.querySelector('.mobile-menu-toggle');
    const mainNav = document.querySelector('.main-nav');

    if (!menuToggle || !mainNav) return;

    menuToggle.addEventListener('click', () => {
        menuToggle.classList.toggle('active');
        mainNav.classList.toggle('mobile-open');
        document.body.classList.toggle('menu-open');
    });

    mainNav.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            if (e.target.closest('.nav-dropdown')) return;

            menuToggle.classList.remove('active');
            mainNav.classList.remove('mobile-open');
            document.body.classList.remove('menu-open');
        });
    });
}

function initFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');

        question.addEventListener('click', () => {
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });

            item.classList.toggle('active');
        });
    });
}

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');

            if (href === '#') return;

            e.preventDefault();

            const target = document.querySelector(href);
            if (target) {
                const headerOffset = 100;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function initScrollAnimations() {
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Группа 1: Карточки и промо
    const animateElements = document.querySelectorAll('.game-card, .promo-card, .feature-item, .step');
    animateElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = `opacity 0.3s ease ${index * 0.1}s, transform 0.3s ease ${index * 0.1}s`;
        observer.observe(el);
    });

    // Группа 2: Элементы FAQ
    const faqElements = document.querySelectorAll('.faq-item');
    faqElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        // Максимальная задержка ограничена, чтобы избежать слишком долгого ожидания при большом количестве вопросов
        const delay = Math.min(index * 0.1, 0.5); 
        el.style.transition = `opacity 0.3s ease ${delay}s, transform 0.3s ease ${delay}s`;
        observer.observe(el);
    });

    animateElements.forEach((el, index) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
        observer.observe(el);
    });
}

function initGameCardHover() {
    const gameCards = document.querySelectorAll('.game-card');

    gameCards.forEach(card => {
        card.addEventListener('mouseenter', function (e) {
            if (!this.querySelector('.play-overlay')) {
                const overlay = document.createElement('div');
                overlay.className = 'play-overlay';
                overlay.innerHTML = `
                    <button class="play-btn">
                        <span>▶</span>
                        Play Now
                    </button>
                `;
                this.querySelector('.game-image').appendChild(overlay);
            }
        });
    });
}

document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function (e) {
        const rect = this.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';

        this.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    });
});

function initCountdown() {
    const countdownElements = document.querySelectorAll('[data-countdown]');

    countdownElements.forEach(el => {
        const endDate = new Date(el.dataset.countdown).getTime();

        const updateCountdown = () => {
            const now = new Date().getTime();
            const distance = endDate - now;

            if (distance < 0) {
                el.innerHTML = 'Offer Expired';
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            el.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        };

        updateCountdown();
        setInterval(updateCountdown, 1000);
    });
}

function initLazyLoading() {
    const lazyImages = document.querySelectorAll('img[data-src]');

    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });

    lazyImages.forEach(img => imageObserver.observe(img));
}

function initAutoFAQ() {
    const containers = document.querySelectorAll('.auto-faq-container');

    containers.forEach(container => {
        const h2 = container.querySelector('h2');
        if (h2) {
            h2.classList.add('section-title');
        }

        const headings = container.querySelectorAll('h3');
        if (headings.length === 0) return;

        const faqList = document.createElement('div');
        faqList.className = 'faq-list';

        headings.forEach(h3 => {
            const faqItem = document.createElement('div');
            faqItem.className = 'faq-item';

            const button = document.createElement('button');
            button.className = 'faq-question';
            button.innerHTML = `<span>${h3.textContent}</span><span class="faq-icon">+</span>`;

            const answerDiv = document.createElement('div');
            answerDiv.className = 'faq-answer';

            let nextEl = h3.nextElementSibling;
            while (nextEl && nextEl.tagName !== 'H3' && nextEl.tagName !== 'H2') {
                const currentEl = nextEl;
                nextEl = nextEl.nextElementSibling;
                answerDiv.appendChild(currentEl);
            }

            faqItem.appendChild(button);
            faqItem.appendChild(answerDiv);
            faqList.appendChild(faqItem);
            h3.remove();
        });

        container.appendChild(faqList);
    });
}

function initParallax() {
    const heroImage = document.querySelector('.hero-bg img');

    if (!heroImage) return;

    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * 0.3;

        heroImage.style.transform = `translateY(${rate}px)`;
    });
}

initParallax();

console.log(
    '%c🎰 %c Welcome to the code!',
    'background: linear-gradient(90deg, #E91E8C, #00D4D4); color: white; padding: 10px 20px; font-size: 20px; font-weight: bold; border-radius: 5px;',
    'color: #E91E8C; font-size: 14px; padding: 10px;'
);

function initMobileDropdown() {
    const dropdownToggle = document.querySelector('.dropdown-toggle');
    const dropdownMenu = document.querySelector('.dropdown-menu');

    if (!dropdownToggle || !dropdownMenu) return;

    dropdownToggle.addEventListener('click', function (e) {
        if (window.innerWidth <= 992) {
            e.preventDefault();
            dropdownMenu.classList.toggle('mobile-active');

            const icon = this.querySelector('small');
            if (icon) {
                const isActive = dropdownMenu.classList.contains('mobile-active');
                icon.style.transform = isActive ? 'rotate(180deg)' : 'rotate(0deg)';
                icon.style.transition = 'transform 0.3s ease';
            }
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 992) {
            dropdownMenu.classList.remove('mobile-active');
            const icon = dropdownToggle.querySelector('small');
            if (icon) icon.style.transform = '';
        }
    });
}

function initPreloader() {
    const preloader = document.getElementById('preloader');
    if (!preloader) return;

    preloader.classList.add('hidden');

    setTimeout(() => {
        preloader.remove();
    }, 500);
}

function initScrollToTop() {
    const scrollBtn = document.getElementById('scrollTopBtn');
    if (!scrollBtn) return;

    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 500) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });

    scrollBtn.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

function initSectionShapes() {
    // 1. Явно прописываем полные пути, чтобы Python-скрипт мог их найти и заменить
    const shapes = ['/images/shape1.webp', '/images/shape2.webp'];
    const sections = document.querySelectorAll('section');
    const iconsPerSection = 3;

    sections.forEach((section) => {
        for (let i = 0; i < iconsPerSection; i++) {
            const shapeImg = document.createElement('img');
            
            // 2. Берем уже готовый полный путь из массива
            const randomShape = shapes[Math.floor(Math.random() * shapes.length)];

            // 3. Просто присваиваем его, без склеивания
            shapeImg.src = randomShape;
            shapeImg.alt = '';
            shapeImg.className = 'section-shape';

            shapeImg.style.top = `${Math.random() * 80 + 10}%`;
            shapeImg.style.left = `${Math.random() * 80 + 10}%`;

            const delay = Math.random() * 5;
            const duration = 5 + Math.random() * 3;

            shapeImg.style.animationDelay = `${delay}s`;
            shapeImg.style.animationDuration = `${duration}s`;

            section.appendChild(shapeImg);
        }
    });
}

function initAgeVerification() {
    const ageOverlay = document.getElementById('ageVerification');
    if (!ageOverlay) return;

    const isVerified = localStorage.getItem('ageVerified');

    if (isVerified === 'true') {
        ageOverlay.classList.add('hidden');
        document.body.style.overflow = '';
    } else {
        document.body.style.overflow = 'hidden';
    }

    const btnYes = document.getElementById('btnAgeYes');
    const btnNo = document.getElementById('btnAgeNo');

    if (btnYes) {
        btnYes.addEventListener('click', () => {
            localStorage.setItem('ageVerified', 'true');
            ageOverlay.classList.add('hidden');
            document.body.style.overflow = '';
        });
    }

    if (btnNo) {
        btnNo.addEventListener('click', () => {
            ageOverlay.classList.add('hidden');
            document.body.style.overflow = '';
        });
    }
}

function initBonusPopup() {
    const popup = document.getElementById('bonusPopup');
    const closeBtn = document.getElementById('btnCloseBonus');

    if (!popup) return;

    const isBonusShown = sessionStorage.getItem('bonusPopupShown');

    if (!isBonusShown) {
        setTimeout(() => {
            popup.classList.add('visible');
            sessionStorage.setItem('bonusPopupShown', 'true');
        }, 10000);
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            popup.classList.remove('visible');
        });
    }

    popup.addEventListener('click', (e) => {
        if (e.target === popup) {
            popup.classList.remove('visible');
        }
    });
}
function initTableOfContents() {
    const tocContainer = document.getElementById('tocContainer');
    if (!tocContainer) return;

    const tocStyles = document.createElement('style');
    tocStyles.textContent = `
        .navigation-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; margin-bottom: 16px; transition: margin var(--transition-fast); }
        .content-navigation.collapsed .navigation-header { margin-bottom: 0; }
        .navigation-title { margin-bottom: 0; }
        .toc-toggle-icon { font-size: 12px; color: var(--primary); transition: transform var(--transition-normal); }
        .content-navigation.collapsed .toc-toggle-icon { transform: rotate(0deg); }
        .toc-list { display: block; transition: opacity var(--transition-normal); }
        .content-navigation.collapsed .toc-list { display: none; }
    `;
    document.head.appendChild(tocStyles);

    const headings = document.querySelectorAll('main h2');

    if (headings.length === 0) {
        const navBlock = tocContainer.closest('.content-navigation');
        if (navBlock) navBlock.style.display = 'none';
        return;
    }

    const titleSpan = tocContainer.querySelector('.navigation-title');
    if (titleSpan) {
        const headerDiv = document.createElement('div');
        headerDiv.className = 'navigation-header';

        titleSpan.parentNode.insertBefore(headerDiv, titleSpan);
        headerDiv.appendChild(titleSpan);

        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toc-toggle-icon';
        toggleIcon.innerHTML = '▼';
        headerDiv.appendChild(toggleIcon);

        headerDiv.addEventListener('click', () => {
            const parent = tocContainer.closest('.content-navigation');
            parent.classList.toggle('collapsed');
        });
    }

    const tocList = document.createElement('div');
    tocList.className = 'toc-list';
    tocContainer.appendChild(tocList);

    headings.forEach((heading, index) => {
        if (!heading.id) {
            const slug = heading.textContent
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/(^-|-$)/g, '');

            heading.id = slug || 'heading-' + index;
        }

        const link = document.createElement('a');
        link.href = '#' + heading.id;
        link.className = 'toc-link';
        link.textContent = heading.textContent;

        tocList.appendChild(link);
    });
}

function initDynamicNav() {
    const nav = document.querySelector('.main-nav');
    const dropdown = document.querySelector('.nav-dropdown');
    const dropdownMenu = document.querySelector('.dropdown-menu');

    if (!nav || !dropdown || !dropdownMenu) return;

    // Получаем только прямые ссылки, исключая саму кнопку "More"
    const allLinks = Array.from(nav.children).filter(el => el.tagName === 'A');
    const threshold = 4; // Максимум 4 ссылки в основном меню

    if (allLinks.length <= threshold) {
        // Скрываем подменю, если ссылок мало
        dropdown.style.display = 'none';
    } else {
        // Показываем подменю и перемещаем лишние элементы
        dropdown.style.display = 'block';
        allLinks.forEach((link, index) => {
            if (index >= threshold) {
                dropdownMenu.appendChild(link);
            }
        });
    }
}