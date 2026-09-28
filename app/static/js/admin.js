/* 관리자 화면 동작.
   접수 목록은 평소 읽기 모드(상태 뱃지)로 두고, '편집'을 누른 행만 폼으로 바꾼다.
   폼은 처음부터 DOM에 있고 hidden 속성만 토글하므로 JS가 없어도 데이터는 살아 있다. */
(function () {
  'use strict';

  var openRow = null;

  function setMode(tr, editing) {
    tr.classList.toggle('editing', editing);
    tr.querySelectorAll('[data-view]').forEach(function (el) { el.hidden = editing; });
    tr.querySelectorAll('[data-edit]').forEach(function (el) { el.hidden = !editing; });
  }

  function close(tr) {
    if (!tr) return;
    setMode(tr, false);
    if (openRow === tr) openRow = null;
  }

  function open(tr) {
    if (openRow && openRow !== tr) close(openRow);   // 한 번에 한 행만
    setMode(tr, true);
    openRow = tr;
    var first = tr.querySelector('[data-edit] select, [data-edit] input');
    if (first) first.focus();
  }

  document.addEventListener('click', function (e) {
    var editBtn = e.target.closest('[data-editbtn]');
    if (editBtn) { open(editBtn.closest('tr')); return; }

    var cancel = e.target.closest('[data-cancel]');
    if (cancel) {
      var tr = cancel.closest('tr');
      var form = tr.querySelector('form[data-edit]');
      if (form) form.reset();
      close(tr);
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && openRow) {
      var form = openRow.querySelector('form[data-edit]');
      if (form) form.reset();
      close(openRow);
    }
  });
})();
