document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.auth-form');
  const passwordToggles = Array.from(document.querySelectorAll('.password-toggle'));
  const inputs = Array.from(document.querySelectorAll('.field-group input'));

  passwordToggles.forEach((toggle) => {
    const field = toggle.closest('.field-group').querySelector('input');
    if (!field) return;

    toggle.addEventListener('click', () => {
      const isPassword = field.type === 'password';
      field.type = isPassword ? 'text' : 'password';
      toggle.textContent = isPassword ? 'Hide' : 'Show';
      toggle.setAttribute('aria-pressed', String(isPassword));
    });
  });

  inputs.forEach((input) => {
    input.addEventListener('focus', () => input.parentElement.classList.add('focused'));
    input.addEventListener('blur', () => {
      if (!input.value) {
        input.parentElement.classList.remove('focused');
      }
    });
  });

  if (form) {
    form.addEventListener('submit', (event) => {
      const button = form.querySelector('.submit-button');
      if (!button) return;
      button.classList.add('is-loading');
      button.disabled = true;
      button.querySelector('.button-text').textContent = 'Signing in...';
    });
  }

  const heroCard = document.querySelector('.hero-card');
  if (heroCard) {
    heroCard.addEventListener('mousemove', (event) => {
      const rect = heroCard.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      heroCard.style.transform = `perspective(700px) rotateY(${x * 9}deg) rotateX(${y * -8}deg)`;
    });

    heroCard.addEventListener('mouseleave', () => {
      heroCard.style.transform = 'perspective(700px) rotateY(0deg) rotateX(0deg)';
    });
  }
});
