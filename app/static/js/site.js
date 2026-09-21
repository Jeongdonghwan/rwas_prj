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

  // 자가진단 (분기형)
  initQuiz();
})();

// ===== 1분 자격진단 (9문항 고정 + 이전으로) =====
function initQuiz() {
  var quiz = document.getElementById('quiz');
  if (!quiz) return;

  var num = quiz.querySelector('.qnum');
  var bar = quiz.querySelector('.bar i');
  var title = quiz.querySelector('h3');
  var opts = quiz.querySelector('.opts');

  var Q = [
    { key: 'income', q: '현재 정기적으로 발생하는 소득이 있으신가요?',
      note: '급여·사업·프리랜서·일용 소득 모두 포함됩니다.',
      opts: ['매월 일정한 소득이 있다', '월마다 차이가 있지만 계속 소득이 있다', '현재 소득이 거의 없다'] },
    { key: 'debt', q: '현재 갚아야 할 전체 채무는 어느 정도인가요?',
      note: '대출·카드·대부업·개인채무 등을 모두 포함해 주세요.',
      opts: ['3천만 원 이하', '3천만~1억 원', '1억~5억 원', '5억 원 이상'] },
    { key: 'overdue', q: '현재 채무 상환 상태는 어떠신가요?',
      opts: ['아직 연체 전이지만 상환이 부담된다', '이미 연체가 시작됐다', '독촉·추심 연락을 받고 있다', '압류·지급명령 등 법적 절차가 진행 중이다'] },
    { key: 'burden', q: '매월 소득에서 빚을 갚는 데 사용하는 금액은 어느 정도인가요?',
      opts: ['소득의 30% 미만', '30~50%', '50~70%', '70% 이상'] },
    { key: 'assets', q: '현재 보유하고 있는 재산은 어느 정도인가요?',
      note: '재산이 있다고 개인회생을 신청할 수 없는 것은 아닙니다.',
      opts: ['특별한 재산이 없다', '임차보증금·자동차 등이 있다', '부동산을 보유하고 있다', '여러 종류의 재산을 보유하고 있다'] },
    { key: 'loan', q: '최근 1년 이내 새로 받은 대출이 있나요?',
      opts: ['거의 없다', '생활비 등으로 일부 받았다', '여러 차례 추가대출을 받았다', '최근 대출 비중이 상당히 높다'] },
    { key: 'reason', q: '채무가 늘어난 가장 큰 이유는 무엇인가요?',
      opts: ['생활비·생계비', '사업 또는 자영업 운영', '기존 채무를 갚기 위한 추가대출', '투자·주식·코인 등', '기타 사정'] },
    { key: 'afford', q: '현재 소득으로 생활비와 빚을 함께 감당할 수 있나요?',
      opts: ['아직은 감당할 수 있다', '매달 빠듯하지만 유지하고 있다', '대출이나 카드로 생활비를 메우고 있다', '사실상 정상적인 상환이 어렵다'] },
    { key: 'family', q: '현재 함께 생활비를 부담하고 있는 가족이 있나요?',
      opts: ['없다', '미성년 자녀가 있다', '배우자와 함께 생활한다', '부모님 등을 부양하고 있다'] }
  ];

  var A = {};
  var idx = 0;

  function render() {
    var step = Q[idx];
    num.textContent = '질문 ' + (idx + 1) + ' / ' + Q.length;
    bar.style.width = (idx / Q.length) * 100 + '%';
    title.textContent = step.q;
    opts.innerHTML = '';

    if (idx > 0) {
      var back = document.createElement('button');
      back.type = 'button';
      back.className = 'qback';
      back.textContent = '← 이전으로';
      back.addEventListener('click', function () { idx -= 1; render(); });
      opts.appendChild(back);
    }
    if (step.note) {
      var nt = document.createElement('p');
      nt.className = 'qnote';
      nt.textContent = step.note;
      opts.appendChild(nt);
    }
    step.opts.forEach(function (label, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      if (A[step.key] === i) b.classList.add('picked');
      b.addEventListener('click', function () {
        A[step.key] = i;
        A[step.key + 'Label'] = label;
        idx += 1;
        if (idx < Q.length) render();
        else result();
      });
      opts.appendChild(b);
    });
  }

  function row(label, value) {
    return value ? '<li><b>' + label + '</b><span>' + value + '</span></li>' : '';
  }

  function result() {
    bar.style.width = '100%';
    num.textContent = '진단 결과';

    var noIncome = A.income === 2;
    var burdenHigh = A.burden >= 2;      // 50% 이상
    var overdueOn = A.overdue >= 1;      // 연체 이상
    var affordHard = A.afford >= 2;      // 카드로 생활비 or 상환 불가
    var hasAssets = A.assets >= 1;
    var recentLoan = A.loan >= 1;

    var verdict, why, focus;
    if (noIncome) {
      verdict = '현재 입력하신 내용으로는 개인파산을 우선 검토해볼 수 있는 상황입니다.';
      why = '개인회생은 계속적인 소득이 필요한 제도입니다. 현재 소득이 거의 없다고 답하셨기 때문에, 재산을 정리하고 잔여 채무를 면책받는 개인파산을 먼저 살펴보는 것이 일반적입니다. 앞으로 소득이 생길 예정이라면 개인회생도 함께 검토할 수 있습니다.';
      focus = 'bankruptcy';
    } else if (burdenHigh || overdueOn || affordHard) {
      verdict = '현재 입력하신 내용으로는 개인회생을 우선 검토해볼 수 있는 상황입니다.';
      why = '계속적인 소득이 있다고 답하셨고, '
        + (burdenHigh ? '소득에서 상환이 차지하는 비중이 ' + A.burdenLabel + '로 높은 편이며, ' : '')
        + (overdueOn ? '이미 ' + A.overdueLabel.replace(/다$/, '') + ' 상태이고, ' : '')
        + (affordHard ? '현재 방식으로는 생활비와 상환을 함께 감당하기 어려운 단계입니다. ' : '')
        + '이 조합에서는 갚을 수 있는 만큼만 갚고 나머지를 면책받는 개인회생이 일반적으로 먼저 검토됩니다.';
      focus = 'rehab';
    } else {
      verdict = '상환 부담이 아직 크지 않아, 신용회복(워크아웃)부터 개인회생까지 폭넓게 검토해볼 수 있습니다.';
      why = '소득이 유지되고 있고 상환 비중(' + A.burdenLabel + ')이 아직 감당 범위에 있으며 연체 전 단계입니다. 이자 조정 중심의 신용회복과 원금 조정이 가능한 개인회생을 나란히 놓고 비교해보는 시점입니다.';
      focus = 'workout';
    }

    var html = '<div class="result">';
    html += '<div class="rcard"><p class="rtitle">나의 채무상황 분석</p><ul class="rgrid">';
    html += row('소득', A.incomeLabel);
    html += row('전체 채무', A.debtLabel);
    html += row('상환 상태', A.overdueLabel);
    html += row('상환 비중', A.burdenLabel);
    html += row('재산', A.assetsLabel);
    html += row('최근 대출', A.loanLabel);
    html += row('증가 원인', A.reasonLabel);
    html += row('감당 정도', A.affordLabel);
    html += row('부양가족', A.familyLabel);
    html += '</ul></div>';
    html += '<p class="verdict">' + verdict + '</p>';

    html += '<div class="v3">';
    html += '<div class="vc ' + (noIncome ? 'warn' : 'ok') + '"><b>' + (noIncome ? '! ' : '✓ ') + '소득 조건</b><span>' + (noIncome ? '현재 소득이 거의 없음' : '지속적인 소득 있음') + '</span></div>';
    html += '<div class="vc ' + (burdenHigh || affordHard ? 'warn' : 'ok') + '"><b>' + (burdenHigh || affordHard ? '! ' : '✓ ') + '상환 부담</b><span>' + (A.burdenLabel || '') + (affordHard ? ' · 생활비 압박' : '') + '</span></div>';
    html += '<div class="vc ' + (hasAssets || recentLoan ? 'warn' : 'ok') + '"><b>' + (hasAssets || recentLoan ? '! ' : '✓ ') + '추가 확인</b><span>' + (hasAssets || recentLoan ? [hasAssets ? '재산가치' : null, recentLoan ? '최근대출' : null].filter(Boolean).join('·') + ' 확인 필요' : '특이사항 없음') + '</span></div>';
    html += '</div>';

    html += '<details class="rwhy"><summary>왜 이런 결과가 나왔나요?</summary><p>' + why + '</p></details>';
    html += '<p class="rnote">자가진단은 여기까지입니다. 실제 진행 가능 여부는 채무·재산 내역을 조금 더 확인해야 판단할 수 있습니다.</p>';
    html += '</div>';

    title.textContent = '진단이 완료되었습니다';
    opts.innerHTML = html;

    var back = document.createElement('button');
    back.type = 'button'; back.className = 'qback'; back.textContent = '← 이전으로';
    back.addEventListener('click', function () { idx = Q.length - 1; render(); });
    opts.insertBefore(back, opts.firstChild);

    var acts = document.createElement('div');
    acts.className = 'racts';
    var a1 = document.createElement('a');
    a1.className = 'btn gold'; a1.href = quiz.getAttribute('data-contact-url') || '/contact/'; a1.textContent = '상담 신청';
    var a2 = document.createElement('a');
    a2.className = 'btn line'; a2.href = 'tel:' + (quiz.getAttribute('data-tel') || ''); a2.textContent = '전화상담';
    acts.appendChild(a1); acts.appendChild(a2);
    opts.appendChild(acts);

    var re = document.createElement('button');
    re.type = 'button'; re.className = 'restart'; re.textContent = '처음부터 다시 진단하기';
    re.addEventListener('click', function () { A = {}; idx = 0; render(); });
    opts.appendChild(re);
  }

  render();
}

