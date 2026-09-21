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


// ===== 1분 자격진단 — 분기형 =====
function initQuiz() {
  var quiz = document.getElementById('quiz');
  if (!quiz) return;

  var num = quiz.querySelector('.qnum');
  var bar = quiz.querySelector('.bar i');
  var title = quiz.querySelector('h3');
  var opts = quiz.querySelector('.opts');

  var fmt = function (n) { return (n || 0).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ','); };
  var toNum = function (v) { return parseInt(String(v).replace(/[^0-9]/g, ''), 10) || 0; };

  var A = {};
  var queue = [];
  var count = 0;

  function stepChoice(key, q, note, list, onPick) {
    return { type: 'choice', key: key, q: q, note: note, list: list, onPick: onPick };
  }
  function stepNumber(key, q, note, placeholder) {
    return { type: 'number', key: key, q: q, note: note, ph: placeholder };
  }

  function startRehabTrack() {
    queue = [
      stepNumber('income', '월평균 실수령액은 얼마인가요?', '세후 기준, 대략적인 금액이면 됩니다.', '예: 3,200,000'),
      stepNumber('repay', '매달 대출·카드 등으로 상환하는 금액은 얼마인가요?', '이자·원금·카드값을 합친 대략적인 금액.', '예: 1,850,000'),
      stepChoice('debt', '현재 갚아야 할 전체 채무는 어느 정도인가요?', '대출·카드·대부업·개인채무 등을 모두 포함해 주세요.',
        ['3천만 원 이하', '3천만~1억 원', '1억~5억 원', '5억 원 이상']),
      { type: 'multi', key: 'assets', q: '보유하신 재산이 있나요? (해당하는 항목 모두 선택)', note: '선택한 항목에 따라 확인 질문이 이어집니다.',
        list: ['자동차', '임차보증금', '부동산', '보험해약환급금', '예·적금', '기타', '특별한 재산 없다'] },
      stepChoice('loan', '최근 1년 이내 새로 받은 대출이 있나요?', null,
        ['거의 없다', '생활비 등으로 일부 받았다', '여러 차례 추가대출을 받았다', '최근 대출 비중이 상당히 높다'],
        function (idx) {
          if (idx > 0) {
            queue.unshift(
              stepChoice('loanWhen', '대략 언제 받으셨나요?', null,
                ['3개월 이내', '3~6개월 전', '6개월~1년 전']),
              stepChoice('loanUse', '최근 대출의 주요 사용처는 무엇인가요?', null,
                ['생활비·생계비', '기존 채무를 갚기 위한 상환', '사업 또는 자영업 운영', '투자·주식·코인 등', '기타'])
            );
          }
        }),
      stepChoice('overdue', '현재 채무 상환 상태는 어떠신가요?', null,
        ['아직 연체 전이지만 상환이 부담된다', '이미 연체가 시작됐다', '독촉·추심 연락을 받고 있다', '압류·지급명령 등 법적 절차가 진행 중이다']),
      stepChoice('family', '현재 함께 생활비를 부담하고 있는 가족이 있나요?', null,
        ['없다', '미성년 자녀가 있다', '배우자와 함께 생활한다', '부모님 등을 부양하고 있다'])
    ];
  }

  function startBankruptcyTrack() {
    queue = [
      stepChoice('debt', '현재 갚아야 할 전체 채무는 어느 정도인가요?', '대출·카드·대부업·개인채무 등을 모두 포함해 주세요.',
        ['3천만 원 이하', '3천만~1억 원', '1억~5억 원', '5억 원 이상']),
      { type: 'multi', key: 'assets', q: '보유하신 재산이 있나요? (해당하는 항목 모두 선택)', note: null,
        list: ['자동차', '임차보증금', '부동산', '보험해약환급금', '예·적금', '기타', '특별한 재산 없다'] },
      stepChoice('overdue', '현재 채무 상환 상태는 어떠신가요?', null,
        ['아직 연체 전이지만 상환이 부담된다', '이미 연체가 시작됐다', '독촉·추심 연락을 받고 있다', '압류·지급명령 등 법적 절차가 진행 중이다'])
    ];
  }

  function assetFollowups(selected) {
    var f = [];
    if (selected.indexOf('부동산') > -1) f.push(stepNumber('assetHome', '부동산의 대략적인 예상가액은 얼마인가요?', '남은 담보대출이 있다면 상담에서 함께 확인합니다.', '예: 250,000,000'));
    if (selected.indexOf('자동차') > -1) f.push(stepNumber('assetCar', '차량의 대략적인 현재 가치는 얼마인가요?', '중고 시세 기준, 대략이면 됩니다.', '예: 8,000,000'));
    return f;
  }

  function render(step) {
    count += 1;
    num.textContent = '질문 ' + count;
    bar.style.width = Math.min(count / 9, 0.95) * 100 + '%';
    title.textContent = step.q;
    opts.innerHTML = '';
    if (step.note) {
      var nt = document.createElement('p');
      nt.className = 'qnote';
      nt.textContent = step.note;
      opts.appendChild(nt);
    }

    if (step.type === 'choice') {
      step.list.forEach(function (label, idx) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = label;
        b.addEventListener('click', function () {
          A[step.key] = idx; A[step.key + 'Label'] = label;
          if (step.onPick) step.onPick(idx);
          next();
        });
        opts.appendChild(b);
      });
    } else if (step.type === 'number') {
      var row = document.createElement('div');
      row.className = 'inp';
      var input = document.createElement('input');
      input.type = 'text'; input.inputMode = 'numeric'; input.placeholder = step.ph || '';
      input.addEventListener('input', function () {
        var v = toNum(input.value);
        input.value = v ? fmt(v) : '';
      });
      var unit = document.createElement('span'); unit.className = 'unit'; unit.textContent = '원';
      var go = document.createElement('button');
      go.type = 'button'; go.className = 'btn gold'; go.textContent = '다음';
      go.addEventListener('click', function () {
        A[step.key] = toNum(input.value);
        next();
      });
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') go.click(); });
      row.appendChild(input); row.appendChild(unit); row.appendChild(go);
      opts.appendChild(row);
      setTimeout(function () { input.focus(); }, 50);
    } else if (step.type === 'multi') {
      var wrap = document.createElement('div');
      wrap.className = 'multi';
      var picked = [];
      step.list.forEach(function (label) {
        var b = document.createElement('button');
        b.type = 'button'; b.textContent = label;
        if (label === '특별한 재산 없다') b.classList.add('none-opt');
        b.addEventListener('click', function () {
          if (label === '특별한 재산 없다') {
            picked = ['특별한 재산 없다'];
            wrap.querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); });
            b.classList.add('on');
          } else {
            var noneBtn = wrap.querySelector('button.none-opt');
            if (noneBtn) noneBtn.classList.remove('on');
            picked = picked.filter(function (x) { return x !== '특별한 재산 없다'; });
            var i = picked.indexOf(label);
            if (i > -1) { picked.splice(i, 1); b.classList.remove('on'); }
            else { picked.push(label); b.classList.add('on'); }
          }
        });
        wrap.appendChild(b);
      });
      var go = document.createElement('button');
      go.type = 'button'; go.className = 'btn gold nextbtn'; go.textContent = '다음';
      go.addEventListener('click', function () {
        if (!picked.length) picked = ['특별한 재산 없다'];
        A[step.key] = picked.slice();
        var fu = assetFollowups(picked);
        for (var i = fu.length - 1; i >= 0; i--) queue.unshift(fu[i]);
        next();
      });
      opts.appendChild(wrap);
      opts.appendChild(go);
    }
  }

  function next() {
    if (queue.length) render(queue.shift());
    else result();
  }

  function row(label, value) {
    return value ? '<li><b>' + label + '</b><span>' + value + '</span></li>' : '';
  }

  function result() {
    bar.style.width = '100%';
    num.textContent = '진단 결과';

    var bankruptcy = A.track === 'bankruptcy';
    var burden = (A.income && A.repay) ? Math.round(A.repay / A.income * 100) : null;
    var overdueIdx = A.overdue || 0;
    var hasAssets = (A.assets || []).length && (A.assets || [])[0] !== '특별한 재산 없다';
    var recentLoan = (A.loan || 0) > 0;

    var verdict, why;
    if (bankruptcy) {
      verdict = '현재 입력하신 내용으로는 개인파산을 우선 검토해볼 수 있는 상황입니다.';
      why = '개인회생은 계속적인 소득이 필요한 제도입니다. 현재 소득이 거의 없다고 답하셨기 때문에, 재산을 정리하고 잔여 채무를 면책받는 개인파산을 먼저 살펴보는 것이 일반적입니다. 소득이 생길 예정이라면 개인회생도 다시 검토할 수 있습니다.';
    } else if (burden !== null && burden < 30 && overdueIdx === 0) {
      verdict = '상환 부담이 아직 크지 않아, 신용회복(워크아웃)부터 개인회생까지 폭넓게 검토해볼 수 있습니다.';
      why = '월 소득 대비 상환 비중이 약 ' + burden + '%로 아직 감당 범위에 있고 연체 전이기 때문에, 이자 조정 중심의 신용회복과 원금 조정이 가능한 개인회생을 나란히 놓고 비교해보는 단계입니다.';
    } else {
      verdict = '현재 입력하신 내용으로는 개인회생을 우선 검토해볼 수 있는 상황입니다.';
      why = '계속적인 소득이 있다고 답하셨고'
        + (burden !== null ? ', 월 소득 대비 상환 부담이 약 ' + burden + '%로 높은 편입니다' : '')
        + (overdueIdx >= 1 ? '. 이미 연체 또는 독촉·법적 절차 단계에 있어 금지명령으로 추심을 멈추는 것이 우선일 수 있습니다' : '')
        + '. 이 조합에서는 갚을 수 있는 만큼만 갚고 나머지를 면책받는 개인회생이 일반적으로 먼저 검토됩니다.';
    }

    var html = '<div class="result">';
    html += '<div class="rcard"><p class="rtitle">나의 채무상황 분석</p><ul class="rgrid">';
    html += row('월 소득', A.income ? fmt(A.income) + '원' : (bankruptcy ? '거의 없음' : null));
    html += row('월 상환액', A.repay ? fmt(A.repay) + '원' : null);
    html += row('상환 부담', burden !== null ? '소득 대비 약 ' + burden + '%' : null);
    html += row('전체 채무', A.debtLabel);
    html += row('연체 상태', A.overdueLabel);
    html += row('재산', (A.assets || []).join(' · ') || null);
    html += row('최근 대출', A.loanLabel ? (recentLoan ? '있음 (' + (A.loanWhenLabel || '') + (A.loanUseLabel ? ' · ' + A.loanUseLabel : '') + ')' : '거의 없음') : null);
    html += row('부양가족', A.familyLabel);
    html += '</ul></div>';
    html += '<p class="verdict">' + verdict + '</p>';

    html += '<div class="v3">';
    if (bankruptcy) {
      html += '<div class="vc warn"><b>! 소득 조건</b><span>현재 소득이 거의 없음</span></div>';
      html += '<div class="vc ok"><b>✓ 검토 방향</b><span>개인파산·면책 우선</span></div>';
      html += '<div class="vc warn"><b>! 추가 확인</b><span>' + (hasAssets ? '재산가치 확인 필요' : '면책 요건 확인 필요') + '</span></div>';
    } else {
      html += '<div class="vc ok"><b>✓ 소득 조건</b><span>지속적인 소득 있음</span></div>';
      html += '<div class="vc ' + (burden !== null && burden >= 50 ? 'warn' : 'ok') + '"><b>' + (burden !== null && burden >= 50 ? '! ' : '✓ ') + '상환 부담</b><span>' + (burden !== null ? '소득 대비 약 ' + burden + '%' + (burden >= 50 ? ' — 높은 편' : '') : '입력 기준 확인') + '</span></div>';
      html += '<div class="vc ' + ((hasAssets || recentLoan) ? 'warn' : 'ok') + '"><b>' + ((hasAssets || recentLoan) ? '! ' : '✓ ') + '추가 확인</b><span>' + ((hasAssets || recentLoan) ? [hasAssets ? '재산가치' : null, recentLoan ? '최근대출' : null].filter(Boolean).join('·') + ' 확인 필요' : '특이사항 없음') + '</span></div>';
    }
    html += '</div>';

    html += '<details class="rwhy"><summary>왜 이런 결과가 나왔나요?</summary><p>' + why + '</p></details>';
    html += '<p class="rnote">자가진단은 여기까지입니다. 실제 진행 가능 여부는 채무·재산 내역을 조금 더 확인해야 판단할 수 있습니다.</p>';
    html += '</div>';

    title.textContent = '진단이 완료되었습니다';
    opts.innerHTML = html;

    var acts = document.createElement('div');
    acts.className = 'racts';
    var a1 = document.createElement('a');
    a1.className = 'btn gold'; a1.href = quiz.getAttribute('data-contact-url') || '/contact/'; a1.textContent = '상담 신청';
    var a2 = document.createElement('a');
    a2.className = 'btn line'; a2.href = 'tel:' + (quiz.getAttribute('data-tel') || ''); a2.textContent = '전화상담';
    var re = document.createElement('button');
    re.type = 'button'; re.className = 'restart'; re.textContent = '다시 진단하기';
    re.addEventListener('click', start);
    acts.appendChild(a1); acts.appendChild(a2);
    opts.appendChild(acts);
    opts.appendChild(re);
  }

  function start() {
    A = {}; queue = []; count = 0;
    render(stepChoice('incomeType', '현재 정기적으로 발생하는 소득이 있으신가요?', '급여·사업·프리랜서·일용 소득 모두 포함됩니다.',
      ['매월 일정한 소득이 있다', '월마다 차이가 있지만 계속 소득이 있다', '현재 소득이 거의 없다'],
      function (idx) {
        if (idx === 2) { A.track = 'bankruptcy'; startBankruptcyTrack(); }
        else { A.track = 'rehab'; startRehabTrack(); }
      }));
  }

  start();
}
