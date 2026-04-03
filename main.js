// ===== TheAssetSquare Sub-site JS =====
document.addEventListener('DOMContentLoaded', function() {

  // ===== Internal Search =====
  var searchInput = document.getElementById('site-search');
  var searchResults = document.getElementById('search-results');
  if (searchInput && searchResults) {
    var properties = [
      {name:'오티에르 반포',meta:'서울 서초구 잠원동 · 251세대 · 청약중 4/10~15',url:'/property/otier-banpo.html'},
      {name:'이촌 르엘',meta:'서울 용산구 이촌동 · 750세대 · 청약중 4/9~14',url:'/property/ichon-lel.html'},
      {name:'라클라체자이드파인',meta:'서울 동작구 노량진동 · 1,499세대 · 청약중 4/13~16',url:'/property/laclache-zaide-fine.html'},
      {name:'공덕역자이르네',meta:'서울 마포구 도화동 · 178세대 · 4월 분양예정',url:'/apartment.html'},
      {name:'장위푸르지오마크원',meta:'서울 성북구 장위동 · 1,931세대 · 4월 분양예정',url:'/apartment.html'},
      {name:'덕수궁 롯데캐슬 136',meta:'서울 중구 순화동 · 102세대 · 4월 분양예정',url:'/apartment.html'},
      {name:'온천장 하늘채 엘리시움',meta:'부산 · 청약중 4/13~15',url:'/apartment.html'},
      {name:'업성 푸르지오 레이크시티',meta:'충남 · 청약중 4/13~15',url:'/apartment.html'},
      {name:'풍무역세권 수자인 그라센트 2차',meta:'경기 김포 · 청약중 4/13~15',url:'/apartment.html'},
      {name:'힐스테이트 안양펠루스',meta:'경기 안양 · 청약중 4/6~8',url:'/apartment.html'},
      {name:'검단호수공원역 파라곤',meta:'인천 · 청약중 4/6~8',url:'/apartment.html'},
      {name:'의정부역 센트럴 아이파크',meta:'경기 의정부 · 청약중 4/7~9',url:'/apartment.html'},
      {name:'범어역 파크드림 디아르',meta:'대구 · 청약중 4/6~8',url:'/apartment.html'},
      {name:'왕십리역 어반홈스',meta:'서울 성동구 · 오피스텔 · 청약중 4/8~14',url:'/officetel.html'},
      {name:'청량리역 요진 와이시티',meta:'서울 동대문구 · 오피스텔 · 청약중 4/7~8',url:'/officetel.html'},
      {name:'당산역 더클래스 한강',meta:'서울 영등포구 · 오피스텔',url:'/officetel.html'},
      {name:'아파트분양',meta:'2026년 4월 청약 가능한 실제 현장',url:'/apartment.html'},
      {name:'오피스텔분양',meta:'2026년 4월 역세권 오피스텔 청약',url:'/officetel.html'},
      {name:'상가분양',meta:'역세권 핵심 상권 투자 가치 비교',url:'/store.html'},
      {name:'지식산업센터분양',meta:'수도권 입주 가능한 곳 총정리',url:'/knowledge-center.html'},
      {name:'토지분양',meta:'개발 호재 지역 엄선 분석',url:'/land.html'},
      {name:'산업단지분양',meta:'기업 입주 조건 비교 분석',url:'/industrial.html'}
    ];

    searchInput.addEventListener('input', function() {
      var q = this.value.trim().toLowerCase();
      if (q.length < 1) { searchResults.classList.remove('show'); return; }
      var matches = properties.filter(function(p) {
        return p.name.toLowerCase().indexOf(q) > -1 || p.meta.toLowerCase().indexOf(q) > -1;
      });
      if (matches.length === 0) {
        searchResults.innerHTML = '<div class="sr-empty">검색 결과가 없습니다</div>';
      } else {
        searchResults.innerHTML = matches.map(function(p) {
          return '<a href="' + p.url + '" class="sr-item"><span class="sr-name">' + p.name + '</span><span class="sr-meta">' + p.meta + '</span></a>';
        }).join('');
      }
      searchResults.classList.add('show');
    });

    document.addEventListener('click', function(e) {
      if (!e.target.closest('.search-box')) searchResults.classList.remove('show');
    });
  }

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
