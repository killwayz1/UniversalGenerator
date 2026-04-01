window.scrollToStart = function () {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
};

document.addEventListener('DOMContentLoaded', function () {
  const body = document.body;
  const preloader = document.getElementById('page-preloader');
  const goTopBtn = document.getElementById('go-top-elem');
  const burgerBtns = document.querySelectorAll('.burger-menu');
  const closeBtn = document.getElementById('close');
  const asideLinks = document.querySelectorAll('.e7cb498 a');
  const navBtn = document.querySelector('.x30f2c');
  const navContent = document.querySelector('.y101aefa5');
  const navList = document.querySelector('.dd912b9');
  const headings = document.querySelectorAll('main section h2');

  if (preloader) {
    window.addEventListener('load', () => {
      setTimeout(() => {
        preloader.style.opacity = '0';
        setTimeout(() => {
          preloader.style.display = 'none';
        }, 600);
      }, 500);
    });
  }

  const toggleMenu = () => {
    if (body.hasAttribute('data-menu-open')) {
      body.removeAttribute('data-menu-open');
    } else {
      body.setAttribute('data-menu-open', '');
    }
  };

  burgerBtns.forEach(btn => btn.onclick = toggleMenu);
  if (closeBtn) closeBtn.onclick = toggleMenu;

  asideLinks.forEach(link => {
    link.onclick = () => body.removeAttribute('data-menu-open');
  });

  if (navBtn && navContent) {
    navBtn.onclick = () => {
      const isOpen = navContent.classList.toggle('active');
      navBtn.classList.toggle('is-open', isOpen);
    };
  }

  if (navList && headings.length > 0) {
    navList.innerHTML = '';
    headings.forEach((heading) => {
      if (heading.closest('#nav') || heading.textContent.toLowerCase().includes('navigation')) return;
      let id = heading.id;
      if (!id) {
        id = heading.textContent.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
        heading.id = id;
      }
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = `#${id}`;
      a.textContent = heading.textContent;
      a.onclick = () => {
        if (window.innerWidth < 1024 && navContent) {
          navContent.classList.remove('active');
          navBtn.classList.remove('is-open');
        }
      };
      li.appendChild(a);
      navList.appendChild(li);
    });
  }

  const faqSection = document.getElementById('faq');
  if (faqSection) {
    const faqQuestions = faqSection.querySelectorAll('h3');

    faqQuestions.forEach(h3 => {
      if (h3.parentNode.getAttribute('data-item') !== 'faq-item') {
        const wrapper = document.createElement('div');
        wrapper.setAttribute('data-item', 'faq-item');

        h3.parentNode.insertBefore(wrapper, h3);
        wrapper.appendChild(h3);

        while (wrapper.nextSibling && wrapper.nextSibling.nodeName !== 'H3') {
          wrapper.appendChild(wrapper.nextSibling);
        }
      }
    });
  }

  const faqItems = document.querySelectorAll('[data-item="faq-item"]');
  faqItems.forEach(item => {
    item.onclick = function () {
      const active = this.classList.contains('active');
      faqItems.forEach(el => el.classList.remove('active'));
      if (!active) this.classList.add('active');
    };
  });

  const tables = document.querySelectorAll('table');

  tables.forEach(table => {
    const wrapper = document.createElement('div');
    wrapper.classList.add('table');

    table.parentNode.insertBefore(wrapper, table);

    wrapper.appendChild(table);
  });
});


const headerMenu = document.querySelector('.hf0d9');

if (headerMenu) {
    const maxItems = 4;
    const menuItems = Array.from(headerMenu.children);

    if (menuItems.length > maxItems) {
        const moreLi = document.createElement('li');
        moreLi.className = 'lb98aa16';

        moreLi.innerHTML = `
        <a href="#" class="he0a1e52" onclick="event.preventDefault()">
          More
          <svg class="r5446d154" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </a>
        <ul class="o9e1ae md90f6"></ul>
      `;

        const dropDown = moreLi.querySelector('ul');

        for (let i = maxItems; i < menuItems.length; i++) {
            dropDown.appendChild(menuItems[i]);
        }

        headerMenu.appendChild(moreLi);
    }
}