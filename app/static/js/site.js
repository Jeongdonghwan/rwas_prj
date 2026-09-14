(function () {
  'use strict';

  // 모바일 메뉴
  var btn = document.querySelector('.menu-btn');
  var nav = document.querySelector('.gnb');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // 스크롤 진행바
  var prog = document.createElement('div');
  prog.id = 'progress';
  document.body.appendChild(prog);
  var onProg = function () {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    prog.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + '%';
  };
  window.addEventListener('scroll', onProg, { passive: true });
  window.addEventListener('resize', onProg);
  onProg();

  // 헤더 스크롤 그림자
  var hdr = document.querySelector('.hdr');
  if (hdr) {
    var onScroll = function () {
      hdr.classList.toggle('scrolled', window.scrollY > 10);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // 플로팅 TOP 버튼
  var topBtn = document.querySelector('.float .top');
  if (topBtn) {
    topBtn.addEventListener('click', function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // 등장 모션
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var revealEls = document.querySelectorAll('.reveal, .stagger');
  if (revealEls.length && 'IntersectionObserver' in window && !reduced) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0, rootMargin: '0px 0px -60px 0px' });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('in'); });
  }

  // 숫자 카운트업 (data-count)
  var counters = document.querySelectorAll('[data-count]');
  if (counters.length && 'IntersectionObserver' in window && !reduced) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        cio.unobserve(e.target);
        var el = e.target;
        var target = parseInt(el.getAttribute('data-count'), 10);
        var suffix = el.getAttribute('data-suffix') || '';
        var start = null;
        var dur = 1100;
        function step(ts) {
          if (!start) start = ts;
          var p = Math.min((ts - start) / dur, 1);
          var eased = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(target * eased) + suffix;
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { cio.observe(el); });
  } else {
    counters.forEach(function (el) {
      el.textContent = el.getAttribute('data-count') + (el.getAttribute('data-suffix') || '');
    });
  }

  // FAQ 아코디언 (.qa 중 .static 제외; 콘텐츠는 DOM에 항상 존재)
  document.querySelectorAll('dl.qa:not(.static)').forEach(function (dl) {
    var dts = dl.querySelectorAll('dt');
    dts.forEach(function (dt, i) {
      var dd = dt.nextElementSibling;
      if (!dd || dd.tagName !== 'DD') return;
      dt.setAttribute('role', 'button');
      dt.setAttribute('tabindex', '0');
      function toggle() {
        var open = dt.classList.toggle('open');
        dd.classList.toggle('open', open);
      }
      dt.addEventListener('click', toggle);
      dt.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
      });
      if (i === 0) { dt.classList.add('open'); dd.classList.add('open'); }
    });
  });

  // 제도 비교 탭
  document.querySelectorAll('[data-tabs]').forEach(function (group) {
    var btns = group.querySelectorAll('button[data-target]');
    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) { b.classList.remove('on'); });
        btn.classList.add('on');
        var box = group.closest('.tabbox') || document;
        box.querySelectorAll('.tabpanel').forEach(function (p) { p.classList.remove('on'); });
        var target = document.getElementById(btn.getAttribute('data-target'));
        if (target) target.classList.add('on');
      });
    });
  });

  // 자가진단
  var quiz = document.getElementById('quiz');
  if (quiz) {
    var QUESTIONS = [
      { q: '매달 들어오는 소득이 있으신가요? (급여·사업·프리랜서·일용 모두 포함)',
        opts: ['네, 정기적으로 있습니다', '수입이 불규칙하지만 있습니다', '현재 소득이 없습니다'] },
      { q: '전체 채무는 어느 정도인가요?',
        opts: ['3천만 원 이하', '3천만~1억 원', '1억~10억 원', '10억 원 초과'] },
      { q: '현재 상황과 가장 가까운 것은?',
        opts: ['아직 연체 전이지만 이자 갚기가 벅차다', '연체가 시작됐고 독촉 연락이 온다', '압류·지급명령 등 법적 조치를 받았다'] },
      { q: '월 소득에서 대출 상환이 차지하는 비중은?',
        opts: ['절반 이하', '절반 이상', '소득 대부분 또는 그 이상'] }
    ];
    var answers = [];
    var step = 0;
    var num = quiz.querySelector('.qnum');
    var bar = quiz.querySelector('.bar i');
    var title = quiz.querySelector('h3');
    var opts = quiz.querySelector('.opts');

    function renderQ() {
      var item = QUESTIONS[step];
      num.textContent = '질문 ' + (step + 1) + ' / ' + QUESTIONS.length;
      bar.style.width = (step / QUESTIONS.length) * 100 + '%';
      title.textContent = item.q;
      opts.innerHTML = '';
      item.opts.forEach(function (label, idx) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = label;
        b.addEventListener('click', function () {
          answers[step] = idx;
          step += 1;
          if (step < QUESTIONS.length) renderQ();
          else renderResult();
        });
        opts.appendChild(b);
      });
    }

    function renderResult() {
      bar.style.width = '100%';
      num.textContent = '진단 결과';
      var noIncome = answers[0] === 2;
      var overLimit = answers[1] === 3;
      var msg, sub;
      if (noIncome) {
        msg = '개인파산 쪽을 먼저 검토해보시는 것이 좋겠습니다.';
        sub = '개인회생은 정기 소득이 필요한 제도입니다. 소득이 없는 경우 개인파산·면책으로 정리하는 방법이 있으며, 상담에서 두 제도를 비교해 안내드립니다.';
      } else if (overLimit) {
        msg = '채무 규모상 일반회생 등 다른 절차 검토가 필요합니다.';
        sub = '개인회생은 무담보 10억 원 이하가 대상입니다. 채무 구성에 따라 이용 가능한 절차가 달라지므로 상담에서 정확히 확인해드립니다.';
      } else {
        msg = '개인회생 검토 대상에 해당할 가능성이 있습니다.';
        sub = '정확한 신청 가능 여부와 예상 월 변제금은 채무·소득·재산을 확인해야 계산됩니다. 상담은 무료이며, 전화 10분이면 예상 변제금까지 안내드립니다.';
      }
      title.textContent = msg;
      opts.innerHTML = '';
      var wrapEl = document.createElement('div');
      wrapEl.className = 'result';
      var p = document.createElement('p');
      p.textContent = sub + ' 본 결과는 참고용이며 법적 판단이 아닙니다.';
      wrapEl.appendChild(p);
      var a1 = document.createElement('a');
      a1.className = 'btn gold';
      a1.href = quiz.getAttribute('data-contact-url') || '/contact/';
      a1.textContent = '무료 상담 신청';
      var a2 = document.createElement('a');
      a2.className = 'btn line';
      a2.href = 'tel:' + (quiz.getAttribute('data-tel') || '');
      a2.textContent = '전화 상담';
      wrapEl.appendChild(a1);
      wrapEl.appendChild(a2);
      var re = document.createElement('button');
      re.type = 'button';
      re.className = 'restart';
      re.textContent = '다시 진단하기';
      re.addEventListener('click', function () { answers = []; step = 0; renderQ(); });
      wrapEl.appendChild(re);
      opts.appendChild(wrapEl);
    }

    renderQ();
  }
})();
