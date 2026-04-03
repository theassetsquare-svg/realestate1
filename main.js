// ===== TheAssetSquare Sub-site JS =====
document.addEventListener('DOMContentLoaded', function() {

  // Mobile hamburger toggle
  var burger = document.querySelector('.hamburger');
  var nav = document.querySelector('.nav-links');
  if (burger && nav) {
    burger.addEventListener('click', function() {
      nav.classList.toggle('show');
    });
  }

  // Active nav link highlight
  var currentPath = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(function(link) {
    var href = link.getAttribute('href').split('/').pop();
    if (href === currentPath) link.classList.add('active');
  });

  // ===== Price Simulator =====
  var simForm = document.getElementById('sim-form');
  if (simForm) {
    var priceInput = simForm.querySelector('[name="price"]');
    var downInput = simForm.querySelector('[name="down"]');
    var rateInput = simForm.querySelector('[name="rate"]');
    var yearInput = simForm.querySelector('[name="years"]');
    var resultEl = document.getElementById('sim-amount');
    var totalEl = document.getElementById('sim-total');

    function calcMonthly() {
      var price = parseFloat(priceInput.value) * 10000 || 0;
      var downPct = parseFloat(downInput.value) || 20;
      var rate = parseFloat(rateInput.value) || 3.5;
      var years = parseInt(yearInput.value) || 30;

      var loan = price * (1 - downPct / 100);
      var monthlyRate = rate / 100 / 12;
      var months = years * 12;
      var monthly = 0;

      if (monthlyRate > 0 && months > 0 && loan > 0) {
        monthly = loan * (monthlyRate * Math.pow(1 + monthlyRate, months)) /
                  (Math.pow(1 + monthlyRate, months) - 1);
      }

      if (resultEl) resultEl.textContent = Math.round(monthly).toLocaleString('ko-KR') + '원';
      if (totalEl) totalEl.textContent = '대출금 ' + (loan / 10000).toLocaleString('ko-KR') + '만원 / ' + years + '년 원리금균등';
    }

    [priceInput, downInput, rateInput, yearInput].forEach(function(el) {
      if (el) el.addEventListener('input', calcMonthly);
    });
    calcMonthly();
  }

  // ===== FAQ Accordion =====
  document.querySelectorAll('.faq-q').forEach(function(q) {
    q.addEventListener('click', function() {
      var item = this.closest('.faq-item');
      var wasOpen = item.classList.contains('open');
      // Close all
      document.querySelectorAll('.faq-item').forEach(function(i) {
        i.classList.remove('open');
      });
      // Toggle clicked
      if (!wasOpen) item.classList.add('open');
    });
  });

  // ===== Alert Email =====
  var alertForm = document.getElementById('alert-form');
  if (alertForm) {
    alertForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var emailInput = this.querySelector('input[type="email"]');
      var msg = document.getElementById('alert-msg');
      if (emailInput && emailInput.value) {
        if (msg) {
          msg.style.display = 'block';
          msg.textContent = emailInput.value + '로 알림이 등록되었습니다.';
        }
        emailInput.value = '';
      }
    });
  }

});
