// ===== TheAssetSquare Sub-site JS =====
document.addEventListener('DOMContentLoaded', function() {

  // ===== Internal Search =====
  var searchInput = document.getElementById('site-search');
  var searchResults = document.getElementById('search-results');
  if (searchInput && searchResults) {
    var properties = [
      {name:'서울원아이파크',meta:'서울 노원구 · 3,032세대 · 84㎡ 10.4~12.1억',url:'/property/seoul-one-ipark.html'},
      {name:'더샵신길센트럴시티',meta:'서울 영등포구 · 2,054세대 · 84㎡ 18.8억',url:'/property/thesharp-singil.html'},
      {name:'래미안엘라비네',meta:'서울 강서구 · 557세대 · 강서구 첫 래미안',url:'/property/raemian-elravine.html'},
      {name:'아크로드서초',meta:'서울 서초구 · 1,161세대 · 역대최고 1,099:1',url:'/property/acro-de-seocho.html'},
      {name:'더샵프리엘라',meta:'서울 영등포구 문래동 · 324세대 · 84㎡ 17억',url:'/property/thesharp-priella.html'},
      {name:'아크로리버스카이',meta:'서울 동작구 · 아크로 프리미엄',url:'/property/acro-river-sky.html'},
      {name:'써밋더힐',meta:'서울 동작구 흑석동 · 1,515세대 · 준강남',url:'/property/summit-thehill.html'},
      {name:'한화포레나부산당리',meta:'부산 사하구 · 543세대 · 더블역세권',url:'/property/forena-busan-dangri.html'},
      {name:'창원자이더스카이',meta:'경남 창원시 · 519세대 · 49층 초고층',url:'/property/changwon-xi-sky.html'},
      {name:'시흥거모호반써밋',meta:'경기 시흥시 · 353세대 · 분양가상한제',url:'/property/siheung-hoban.html'},
      {name:'해링턴플레이스오룡역',meta:'대전 중구 · 427세대 · 84㎡ 5.7~6.8억',url:'/property/harrington-oryong.html'},
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
      {name:'건대 프라하임',meta:'서울 광진구 · 오피스텔 · 건대입구역 인근',url:'/property/konkuk-prahime.html'},
      {name:'대방역 여의도 더로드캐슬',meta:'서울 동작구 · 오피스텔 · 대방역 역세권',url:'/property/daebang-roadcastle.html'},
      {name:'e편한세상 동탄역 어반원',meta:'경기 화성시 · 오피스텔 · 동탄역 SRT',url:'/property/dongtan-urbanone.html'},
      {name:'철산자이 더 헤리티지 상가',meta:'광명 철산동 · 46호실 · 7호선 철산역',url:'/property/cheolsan-xi-store.html'},
      {name:'라클라체자이드파인 상업시설',meta:'서울 동작구 · 노량진뉴타운 · 1,499세대 배후',url:'/property/noryangjin-store.html'},
      {name:'의왕초평 근린생활시설용지',meta:'경기 의왕시 · LH · 근린생활시설',url:'/property/uiwang-chopyeong.html'},
      {name:'구리갈매역세권 상업용지',meta:'경기 구리시 · LH · GTX-B 수혜',url:'/property/guri-galmae-store.html'},
      {name:'영등포자이타워',meta:'서울 영등포구 · 지식산업센터 · 평당 2,050만',url:'/property/ydp-xi-tower.html'},
      {name:'현대 테라타워 세마역',meta:'경기 오산시 · 지식산업센터 · 599실',url:'/property/terra-tower-sema.html'},
      {name:'디지털엠파이어 평촌 비즈밸리',meta:'경기 안양시 · 지식산업센터 · 681실',url:'/property/empire-pyeongchon.html'},
      {name:'오브코스 구로',meta:'서울 구로구 · 지식산업센터 · G밸리 584실',url:'/property/ofcourse-guro.html'},
      {name:'인천남동 도시첨단산업단지',meta:'인천 남동구 · 3차분양 · 남동산단 대비 35% 저렴',url:'/property/incheon-namdong.html'},
      {name:'경산4 일반산업단지',meta:'경북 경산시 · KICOX · 탄소융복합',url:'/property/gyeongsan4.html'},
      {name:'평택포승(BIX) 산업단지',meta:'경기 평택시 · GH · 평택항 인접',url:'/property/pyeongtaek-bix.html'},
      {name:'천안 수신 일반산업단지',meta:'충남 천안시 · 48만평 · 미래모빌리티',url:'/property/cheonan-susin.html'},
      {name:'하남감일 단독주택용지',meta:'경기 하남시 · LH · 3년 무이자',url:'/property/hanam-gamil.html'},
      {name:'고양창릉 3기 신도시',meta:'경기 고양시 · LH · GTX-A 강남 20분',url:'/property/goyang-changneung.html'},
      {name:'인천계양 3기 신도시',meta:'인천 계양구 · LH · GTX-D · 55㎡ 3.9억',url:'/property/incheon-gyeyang.html'},
      {name:'새만금 수변도시',meta:'전북 군산시 · 22필지 · 평당 200만원대',url:'/property/saemangeum-land.html'},
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
