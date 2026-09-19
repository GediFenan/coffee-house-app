
// ═══════ UI INTERACTIONS BY FIKIR ═══════
document.addEventListener('click', function(e) {
    var btn = e.target.closest('.add, .btn');
    if (!btn) return;
    var rect = btn.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height);
    var ripple = document.createElement('span');
    var x = e.clientX - rect.left - size / 2;
    var y = e.clientY - rect.top - size / 2;
    ripple.style.cssText = 'position:absolute;width:' + size + 'px;height:' + size + 'px;border-radius:50%;background:rgba(255,255,255,.5);left:' + x + 'px;top:' + y + 'px;pointer-events:none;transform:scale(0);animation:ripple .6s ease-out;';
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    setTimeout(function() { ripple.remove(); }, 600);
});

document.addEventListener('click', function(e) {
    var btn = e.target.closest('.add');
    if (!btn || btn.disabled) return;
    var orig = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>';
    btn.disabled = true;
    setTimeout(function() { btn.textContent = orig; btn.disabled = false; }, 500);
});

document.querySelectorAll('a[href^="#"]').forEach(function(link) {
    link.addEventListener('click', function(e) {
        var target = document.querySelector(this.getAttribute('href'));
        if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    });
});
