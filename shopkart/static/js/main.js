// ── Flash auto-dismiss ────────────────────
document.querySelectorAll(".flash").forEach(el => {
  setTimeout(() => el.remove(), 4000);
});

// ── Password toggle ────────────────────────
function togglePw(id, btn) {
  const input = document.getElementById(id);
  const icon  = btn.querySelector("i");
  if (input.type === "password") {
    input.type = "text";
    icon.className = "fa fa-eye-slash";
  } else {
    input.type = "password";
    icon.className = "fa fa-eye";
  }
}

// ── Cart quantity +/- buttons ─────────────
function changeQty(btn, delta) {
  const form  = btn.closest("form");
  const input = form.querySelector("input[name='quantity']");
  let val = parseInt(input.value) + delta;
  if (val < 0) val = 0;
  input.value = val;
  form.submit();
}

// ── Star picker ────────────────────────────
const stars = document.querySelectorAll(".star-pick");
const ratingInput = document.getElementById("ratingInput");

stars.forEach((star, idx) => {
  star.addEventListener("mouseenter", () => {
    stars.forEach((s, i) => s.classList.toggle("active", i <= idx));
  });
  star.addEventListener("mouseleave", () => {
    const current = ratingInput ? parseInt(ratingInput.value) : 0;
    stars.forEach((s, i) => s.classList.toggle("active", i < current));
  });
  star.addEventListener("click", () => {
    const val = idx + 1;
    if (ratingInput) ratingInput.value = val;
    stars.forEach((s, i) => s.classList.toggle("active", i < val));
  });
});

// ── Confirm add-to-cart animation ────────
document.querySelectorAll("form[action*='cart/add']").forEach(form => {
  form.addEventListener("submit", () => {
    const btn = form.querySelector("button[type=submit]");
    if (btn) {
      btn.innerHTML = '<i class="fa fa-check"></i> Added!';
      btn.style.background = "#10B981";
    }
  });
});