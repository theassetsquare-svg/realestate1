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
      {name:'공덕역자이르네',meta:'서울 마포구 도화동 · 178세대 · 쿼드러플 역세권',url:'/property/gongdeok-xi-lene.html'},
      {name:'장위푸르지오마크원',meta:'서울 성북구 장위동 · 2,004세대 · 장위뉴타운 최대',url:'/property/jangwi-prugio.html'},
      {name:'덕수궁 롯데캐슬 136',meta:'서울 중구 순화동 · 136세대 · 비규제 도심 희소',url:'/property/deoksugung-lottecastle.html'},
      {name:'온천장 하늘채 엘리시움',meta:'부산 동래구 · 436세대 · 청약중 4/13~15',url:'/property/oncheonjang-hanulchae.html'},
      {name:'업성 푸르지오 레이크시티',meta:'충남 천안시 · 1,908세대 · 청약중 4/13~15',url:'/property/upseong-prugio.html'},
      {name:'풍무역세권 수자인 그라센트 2차',meta:'경기 김포 · 639세대 · 84㎡ 7.1억~',url:'/property/pungmu-sujain.html'},
      {name:'힐스테이트 안양펠루스',meta:'경기 안양 · 198세대 · 후분양 즉시입주',url:'/property/hillstate-anyang.html'},
      {name:'검단호수공원역 파라곤',meta:'인천 검단신도시 · 569세대 · 84㎡ 5.9억~',url:'/property/geomdan-paragon.html'},
      {name:'의정부역 센트럴 아이파크',meta:'경기 의정부 · 556세대 · 47층 GTX-C',url:'/property/uijeongbu-ipark.html'},
      {name:'범어역 파크드림 디아르',meta:'대구 수성구 · 158세대 · 일반분양 47세대',url:'/property/beomeo-parkdream.html'},
      {name:'왕십리역 어반홈스',meta:'서울 성동구 · 84실 · 쿼드러플역세권 5억대',url:'/property/wangsimni-urbanhomes.html'},
      {name:'청량리역 요진 와이시티',meta:'서울 동대문구 · 155세대 · 멀티역세권',url:'/property/cheongnyangni-ycity.html'},
      {name:'당산역 더클래스 한강',meta:'서울 영등포구 · 116세대 · 즉시입주 4~5억대',url:'/property/dangsan-theclass.html'},
      {name:'철산자이 더 헤리티지 상가',meta:'광명 철산동 · 46호실 · 7호선 철산역',url:'/store.html'},
      {name:'영등포자이타워',meta:'서울 영등포구 · 지식산업센터 · 평당 2,050만',url:'/knowledge-center.html'},
      {name:'인천남동 도시첨단산업단지',meta:'인천 남동구 · 3차분양 · 남동산단 대비 35% 저렴',url:'/industrial.html'},
      {name:'하남감일 단독주택용지',meta:'경기 하남시 · LH · 단독주택용지',url:'/land.html'},
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


});
