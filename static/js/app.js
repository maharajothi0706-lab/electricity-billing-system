/**
 * Electricity Billing and Consumption Management System
 * Global Application Interactivity (app.js)
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Mobile Sidebar Toggle
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  const sidebar = document.querySelector(".sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // 2. Alert Dismissal
  document.querySelectorAll(".alert-close").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const alert = e.target.closest(".alert");
      if (alert) alert.remove();
    });
  });

  // 3. Modal Opening & Closing
  document.querySelectorAll("[data-modal-target]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = btn.getAttribute("data-modal-target");
      const modal = document.getElementById(targetId);
      if (modal) {
        modal.classList.add("active");
        
        // Pass contextual data attributes if present
        if (btn.dataset.billId) {
          const billInput = modal.querySelector('input[name="bill_id"]');
          if (billInput) billInput.value = btn.dataset.billId;
        }
        if (btn.dataset.paymentId) {
          const payInput = modal.querySelector('input[name="payment_id"]');
          if (payInput) payInput.value = btn.dataset.paymentId;
        }
        if (btn.dataset.outstanding) {
          const amountInput = modal.querySelector('input[name="amount"]');
          if (amountInput) {
            amountInput.value = btn.dataset.outstanding;
            amountInput.max = btn.dataset.outstanding;
          }
          const maxSpan = modal.querySelector('#modalMaxOutstanding');
          if (maxSpan) maxSpan.textContent = `₹${parseFloat(btn.dataset.outstanding).toFixed(2)}`;
        }
      }
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach(btn => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-overlay");
      if (modal) modal.classList.remove("active");
    });
  });

  // Close modal when clicking outside box
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.remove("active");
    });
  });

  // 4. Meter Reading Auto-Calculator
  const prevInput = document.getElementById("prevReadingInput");
  const currInput = document.getElementById("currReadingInput");
  const unitsDisplay = document.getElementById("unitsConsumedPreview");

  function updateUnitsPreview() {
    if (!prevInput || !currInput || !unitsDisplay) return;
    const prev = parseFloat(prevInput.value) || 0;
    const curr = parseFloat(currInput.value) || 0;
    const units = Math.max(0, curr - prev);
    unitsDisplay.textContent = units.toFixed(2);
    if (curr < prev) {
      unitsDisplay.style.color = "#dc2626";
      unitsDisplay.textContent += " (Invalid: Current < Previous)";
    } else {
      unitsDisplay.style.color = "#059669";
    }
  }

  if (prevInput && currInput) {
    prevInput.addEventListener("input", updateUnitsPreview);
    currInput.addEventListener("input", updateUnitsPreview);
  }

  // 5. Auto-fetch Consumer's Previous Reading on Selection
  const consumerSelect = document.getElementById("readingConsumerSelect");
  if (consumerSelect) {
    consumerSelect.addEventListener("change", async (e) => {
      const consumerId = e.target.value;
      if (!consumerId) return;

      try {
        const res = await fetch(`/readings/api/consumer-latest-reading/${consumerId}`);
        if (res.ok) {
          const data = await res.json();
          if (prevInput) {
            prevInput.value = data.previous_reading;
            updateUnitsPreview();
          }
        }
      } catch (err) {
        console.error("Could not fetch previous reading:", err);
      }
    });
  }

  // 6. Generic confirmation for destructive buttons
  document.querySelectorAll(".confirm-action").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const msg = btn.getAttribute("data-confirm") || "Are you sure you want to perform this operation?";
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });
});
