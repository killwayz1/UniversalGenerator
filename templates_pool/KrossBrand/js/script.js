window.addEventListener('load', () => {
  const preloader = document.getElementById('site-preloader');
  setTimeout(() => {
    preloader.classList.add('hidden');
  }, 500);
});
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.providers-list, .winners-list').forEach(list => {
    const items = Array.from(list.children);
    items.forEach(item => {
      const clone = item.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      list.appendChild(clone);
    });
  });


  const menuToggler = document.querySelector('.navbar-toggler');
  const navMenu = document.querySelector('#navbarNav');

  if (menuToggler && navMenu) {
    menuToggler.addEventListener('click', () => {
      navMenu.classList.toggle('show');
      menuToggler.classList.toggle('collapsed');

      if (navMenu.classList.contains('show')) {
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
      }
    });

    const navLinks = navMenu.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        navMenu.classList.remove('show');
        menuToggler.classList.add('collapsed');
        document.body.style.overflow = '';
      });
    });
  }

  const accordionButtons = document.querySelectorAll('.accordion-button');

  accordionButtons.forEach(button => {
    button.addEventListener('click', function () {
      const targetId = this.getAttribute('data-bs-target');
      const targetContent = document.querySelector(targetId);
      const isExpanded = this.getAttribute('aria-expanded') === 'true';

      document.querySelectorAll('.accordion-collapse.show').forEach(content => {
        if (content !== targetContent) {
          content.classList.remove('show');
          const relatedBtn = document.querySelector(`[data-bs-target="#${content.id}"]`);
          if (relatedBtn) {
            relatedBtn.classList.add('collapsed');
            relatedBtn.setAttribute('aria-expanded', 'false');
          }
        }
      });

      if (!isExpanded) {
        this.classList.remove('collapsed');
        this.setAttribute('aria-expanded', 'true');
        targetContent.classList.add('show');
      } else {
        this.classList.add('collapsed');
        this.setAttribute('aria-expanded', 'false');
        targetContent.classList.remove('show');
      }
    });
  });

  const scrollBtn = document.getElementById('scrollToTopBtn');

  if (scrollBtn) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 300) {
        scrollBtn.style.display = 'block';
        scrollBtn.style.opacity = '1';
      } else {
        scrollBtn.style.opacity = '0';
        setTimeout(() => {
          if (window.scrollY <= 300) scrollBtn.style.display = 'none';
        }, 200);
      }
    });

    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }


  const track = document.querySelector('.gallery-track');
  const slides = Array.from(document.querySelectorAll('.gallery-slide'));
  const nextButton = document.querySelector('.gallery-next');
  const prevButton = document.querySelector('.gallery-prev');
  const dotsNav = document.querySelector('.gallery-dots');

  if (track && slides.length > 0) {
    slides.forEach((_, index) => {
      const dot = document.createElement('button');
      dot.classList.add('dot');
      if (index === 0) dot.classList.add('active');
      dot.dataset.index = index;
      if (dotsNav) dotsNav.appendChild(dot);
    });

    const dots = dotsNav ? Array.from(dotsNav.children) : [];
    let currentIndex = 0;

    const updateGallery = (index) => {
      track.style.transform = `translateX(-${index * 100}%)`;
      dots.forEach(dot => dot.classList.remove('active'));
      if (dots[index]) dots[index].classList.add('active');
      currentIndex = index;
    };

    if (nextButton) {
      nextButton.addEventListener('click', () => {
        let nextIndex = currentIndex + 1;
        if (nextIndex >= slides.length) nextIndex = 0;
        updateGallery(nextIndex);
      });
    }

    if (prevButton) {
      prevButton.addEventListener('click', () => {
        let prevIndex = currentIndex - 1;
        if (prevIndex < 0) prevIndex = slides.length - 1;
        updateGallery(prevIndex);
      });
    }

    if (dotsNav) {
      dotsNav.addEventListener('click', e => {
        const targetDot = e.target.closest('button');
        if (!targetDot) return;
        const targetIndex = parseInt(targetDot.dataset.index);
        updateGallery(targetIndex);
      });
    }

    setInterval(() => {
      let nextIndex = currentIndex + 1;
      if (nextIndex >= slides.length) nextIndex = 0;
      updateGallery(nextIndex);
    }, 4000);
  }




  const shapes = ['/images/shape1.webp', '/images/shape2.webp'];
  const sections = document.querySelectorAll('section.wrapper, .hero-section, main > section:not(.hero-section)');
  const allIcons = [];

  sections.forEach(section => {
    // Случайное количество иконок от 3 до 4
    const iconCount = Math.floor(Math.random() * 2) + 3;

    for (let i = 0; i < iconCount; i++) {
      const icon = document.createElement('img');

      icon.src = shapes[i % shapes.length];
      icon.className = 'bg-decoration-icon';

      if (i % 2 === 0) {
        icon.style.left = Math.floor(Math.random() * 5 + 1) + '%';
      } else {
        icon.style.right = Math.floor(Math.random() * 5 + 1) + '%';
      }

      icon.style.top = Math.floor(Math.random() * 80 + 10) + '%';

      icon.dataset.depth = (Math.random() * 0.03 + 0.01).toFixed(3);

      section.appendChild(icon);
      allIcons.push(icon);
    }
  });

  document.addEventListener('mousemove', (e) => {
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;

    const mouseX = e.clientX - centerX;
    const mouseY = e.clientY - centerY;

    allIcons.forEach((icon) => {
      const depth = parseFloat(icon.dataset.depth);
      const moveX = mouseX * depth;
      const moveY = mouseY * depth;
      const rotate = mouseX * 0.05;

      icon.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotate}deg)`;
    });
  });


  const tocList = document.getElementById('toc-list');
  const tocContainer = document.getElementById('toc-container');
  const toggleBtn = document.getElementById('toc-toggle');
  const tocHeader = document.getElementById('toc-header');
  const h2Elements = document.querySelectorAll('main h2');

  if (h2Elements.length > 0 && tocList) {
    h2Elements.forEach((h2, index) => {
      let id = h2.getAttribute('id');
      if (!id) {
        id = 'section-' + index;
        h2.setAttribute('id', id);
      }
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.textContent = h2.textContent;
      a.setAttribute('href', '#' + id);
      a.onclick = function (e) {
        e.preventDefault();
        const target = document.getElementById(id);
        if (target) {
          const headerOffset = 100;
          const elementPosition = target.getBoundingClientRect().top;
          const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

          window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
          });
        }
      };
      li.appendChild(a);
      tocList.appendChild(li);
    });
  } else if (tocContainer) {
    tocContainer.style.display = 'none';
  }

  function toggleToc() {
    if (tocContainer) {
      const isCollapsed = tocContainer.classList.toggle('toc-collapsed');
      if (toggleBtn) {
        toggleBtn.textContent = isCollapsed ? 'Mostrar' : 'Ocultar';
      }
    }
  }

  if (toggleBtn) toggleBtn.onclick = (e) => { e.stopPropagation(); toggleToc(); };
  if (tocHeader) tocHeader.onclick = toggleToc;


  const galleryItems = document.querySelectorAll('.providers-list__item, .games-list__item, .games-list-v2__item, .winners-list__item');


  galleryItems.forEach(item => {
    item.style.cursor = 'pointer';

    item.addEventListener('click', (e) => {
      e.preventDefault();
      window.open('{{AFF_URL}}', '_blank');
    });
  });
});