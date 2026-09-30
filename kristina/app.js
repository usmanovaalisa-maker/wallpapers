/* Кристина — карточка товара. Без сборки и зависимостей. */
(function () {
  'use strict';

  var $ = function (id) { return document.getElementById(id); };
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Картинки: сначала JPG, затем PNG, иначе аккуратная заглушка ──
     Пути относительные, поэтому страница работает и во вложенном
     адресе вида https://<логин>.github.io/<репозиторий>/kristina/. */
  function wireImages() {
    var imgs = document.querySelectorAll('.frame__img[data-src]');
    Array.prototype.forEach.call(imgs, function (img) {
      var list = img.getAttribute('data-src').split('|').filter(Boolean);
      var i = 0;
      var frame = img.closest('[data-frame]');

      function step() {
        if (i < list.length) {
          img.setAttribute('src', list[i++]);
        } else {
          img.removeAttribute('src');
          img.style.display = 'none';
          if (frame) { frame.classList.add('is-missing'); }
        }
      }

      img.addEventListener('error', step);
      img.addEventListener('load', function () {
        if (frame) { frame.classList.remove('is-missing'); }
      });
      step();
    });
  }

  /* ── Галерея ─────────────────────────────────────────────────── */
  function wireGallery() {
    var track = $('track');
    if (!track) { return; }

    var slides = track.querySelectorAll('.slide');
    var total = slides.length;
    var counter = $('counter');
    var dotsBox = $('dots');
    var prev = $('prev');
    var next = $('next');
    var index = 0;
    var dots = [];

    for (var n = 0; n < total; n++) {
      var d = document.createElement('button');
      d.type = 'button';
      d.className = 'dot';
      d.setAttribute('role', 'tab');
      d.setAttribute('aria-label', 'Слайд ' + (n + 1) + ' из ' + total);
      d.setAttribute('aria-selected', n === 0 ? 'true' : 'false');
      d.addEventListener('click', (function (k) {
        return function () { go(k); };
      })(n));
      dotsBox.appendChild(d);
      dots.push(d);
    }

    function step() {
      // Ширина одного слайда — считаем по факту, а не по константе.
      return slides.length > 1
        ? Math.abs(slides[1].offsetLeft - slides[0].offsetLeft)
        : track.clientWidth;
    }

    function go(k) {
      k = Math.max(0, Math.min(total - 1, k));
      track.scrollTo({ left: k * step(), behavior: calm ? 'auto' : 'smooth' });
    }

    function paint() {
      var w = step();
      var k = w ? Math.round(track.scrollLeft / w) : 0;
      k = Math.max(0, Math.min(total - 1, k));
      if (k === index) { return sync(); }
      index = k;
      sync();
    }

    function sync() {
      counter.textContent = (index + 1) + ' / ' + total;
      for (var n = 0; n < dots.length; n++) {
        dots[n].setAttribute('aria-selected', n === index ? 'true' : 'false');
      }
      prev.disabled = index === 0;
      next.disabled = index === total - 1;
    }

    var ticking = false;
    track.addEventListener('scroll', function () {
      if (ticking) { return; }
      ticking = true;
      requestAnimationFrame(function () { ticking = false; paint(); });
    }, { passive: true });

    prev.addEventListener('click', function () { go(index - 1); });
    next.addEventListener('click', function () { go(index + 1); });

    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); go(index - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); go(index + 1); }
    });

    window.addEventListener('resize', function () { go(index); });

    sync();
  }

  /* ── Тост ────────────────────────────────────────────────────── */
  var toastTimer;
  function toast(message) {
    var box = $('toast');
    box.textContent = message;
    box.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { box.classList.remove('is-on'); }, 3200);
  }

  /* ── Финальный экран ─────────────────────────────────────────── */
  var finale = $('finale');
  var lastFocus = null;

  function openFinale() {
    lastFocus = document.activeElement;
    finale.hidden = false;
    document.body.classList.add('is-locked');
    requestAnimationFrame(function () { finale.classList.add('is-on'); });
    $('finaleClose').focus();
  }

  function closeFinale() {
    finale.classList.remove('is-on');
    var done = function () {
      finale.hidden = true;
      document.body.classList.remove('is-locked');
      if (lastFocus && lastFocus.focus) { lastFocus.focus(); }
    };
    if (calm) { done(); } else { setTimeout(done, 260); }
  }

  /* ── Сценарий заказа ─────────────────────────────────────────── */
  function wireOrder() {
    var btn = $('order');
    var status = $('status');
    var opened = false;
    var running = false;
    var pace = calm ? 350 : 1000;

    function say(text) {
      status.textContent = text;
      status.classList.add('is-on');
    }

    btn.addEventListener('click', function () {
      if (running) { return; }

      if (opened) { openFinale(); return; }

      running = true;
      btn.disabled = true;
      btn.classList.add('is-busy');

      say('Оформляем заказ…');
      btn.textContent = 'Оформляем заказ…';

      setTimeout(function () {
        say('Проверяем остатки…');
        btn.textContent = 'Проверяем остатки…';

        setTimeout(function () {
          status.classList.remove('is-on');
          status.textContent = '';
          btn.disabled = false;
          btn.classList.remove('is-busy');
          btn.textContent = 'Открыть поздравление снова';
          opened = true;
          running = false;
          openFinale();
        }, pace);
      }, pace);
    });
  }

  /* ── Остальные кнопки ────────────────────────────────────────── */
  function wireButtons() {
    $('toCart').addEventListener('click', function () {
      toast('Этот товар уже работает в нашей команде');
    });

    $('gift').addEventListener('click', function () {
      toast('Подарок ждёт тебя в реальной жизни :)');
    });

    $('finaleClose').addEventListener('click', closeFinale);

    finale.addEventListener('click', function (e) {
      if (e.target === finale) { closeFinale(); }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !finale.hidden) { closeFinale(); }
    });
  }

  wireImages();
  wireGallery();
  wireOrder();
  wireButtons();
})();
