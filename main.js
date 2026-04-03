// ===== TheAssetSquare Sub-site JS =====

// Mobile hamburger toggle
document.addEventListener('DOMContentLoaded', function() {
  var burger = document.querySelector('.hamburger');
  var nav = document.querySelector('.nav-links');
  if (burger && nav) {
    burger.addEventListener('click', function() {
      nav.classList.toggle('show');
      burger.classList.toggle('open');
    });
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Active nav link highlight
  var currentPath = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(function(link) {
    var href = link.getAttribute('href').split('/').pop();
    if (href === currentPath) {
      link.classList.add('active');
    }
  });
});
