/* ═══════════════════════════════════════════════════════════════════════════
   SonoLit — JavaScript
   Particles · Scroll Reveal · Form Handling · Mobile Menu
   ═══════════════════════════════════════════════════════════════════════════ */

// ── Floating Particles ──────────────────────────────────────────────────────
(function initParticles() {
  const container = document.getElementById("particle-container");
  if (!container) return;

  const PARTICLE_COUNT = 15;

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const particle = document.createElement("div");
    particle.className = "floating-particle";

    const size = Math.random() * 200 + 50;
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${Math.random() * 100}%`;
    particle.style.top = `${Math.random() * 100}%`;

    const duration = Math.random() * 20 + 10;
    particle.style.transition = `all ${duration}s linear`;

    container.appendChild(particle);

    // Continuous drift
    setInterval(() => {
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.top = `${Math.random() * 100}%`;
    }, duration * 1000);
  }
})();

// ── Scroll Reveal ───────────────────────────────────────────────────────────
(function initReveal() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.remove("opacity-0");
          entry.target.classList.add("reveal");
          observer.unobserve(entry.target); // animate once
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll("section").forEach((section) => {
    section.classList.add("opacity-0");
    observer.observe(section);
  });
})();

// ── Mobile Menu Toggle ──────────────────────────────────────────────────────
(function initMobileMenu() {
  const btn = document.getElementById("mobile-menu-btn");
  const menu = document.getElementById("mobile-menu");
  if (!btn || !menu) return;

  btn.addEventListener("click", () => {
    menu.classList.toggle("hidden");
  });

  // Close on link click
  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => menu.classList.add("hidden"));
  });
})();

// ── Registration Form ───────────────────────────────────────────────────────
(function initForm() {
  const form = document.getElementById("registration-form");
  const emailInput = document.getElementById("email-input");
  const submitBtn = document.getElementById("submit-btn");
  const successMsg = document.getElementById("success-message");
  const errorMsg = document.getElementById("error-message");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    if (!email) return;

    // Reset messages
    errorMsg.classList.add("hidden");
    errorMsg.textContent = "";

    // Loading state
    submitBtn.disabled = true;
    submitBtn.innerText = "Procesando...";

    try {
      const response = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        // Success
        form.style.display = "none";
        successMsg.classList.remove("hidden");
      } else {
        // Server validation error
        errorMsg.textContent = data.detail || "Error al registrar. Intenta de nuevo.";
        errorMsg.classList.remove("hidden");
        submitBtn.disabled = false;
        submitBtn.innerText = "Notificarme del Lanzamiento";
      }
    } catch (err) {
      errorMsg.textContent = "Error de conexión. Verifica tu internet e intenta de nuevo.";
      errorMsg.classList.remove("hidden");
      submitBtn.disabled = false;
      submitBtn.innerText = "Notificarme del Lanzamiento";
    }
  });
})();
