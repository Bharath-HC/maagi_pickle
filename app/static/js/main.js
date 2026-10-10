document.addEventListener("DOMContentLoaded", function () {
  // Dashboard sidebar toggle (mobile)
  var sidebarToggle = document.getElementById("dashSidebarToggle");
  var sidebar = document.getElementById("dashSidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      sidebar.classList.toggle("open");
    });
    document.addEventListener("click", function (e) {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
        sidebar.classList.remove("open");
      }
    });
  }

  // Flash toast auto-dismiss
  document.querySelectorAll(".app-toast").forEach(function (toast) {
    var closeBtn = toast.querySelector(".app-toast__close");
    var remove = function () {
      toast.style.opacity = "0";
      setTimeout(function () { toast.remove(); }, 200);
    };
    if (closeBtn) closeBtn.addEventListener("click", remove);
    setTimeout(remove, 5000);
  });

  // Generic quantity stepper
  document.querySelectorAll(".qty-stepper").forEach(function (stepper) {
    var input = stepper.querySelector(".qty-input");
    var dec = stepper.querySelector('[data-action="decrease"]');
    var inc = stepper.querySelector('[data-action="increase"]');
    if (dec) dec.addEventListener("click", function () {
      input.value = Math.max(parseInt(input.value || "1", 10) - 1, parseInt(input.min || "1", 10));
    });
    if (inc) inc.addEventListener("click", function () {
      input.value = parseInt(input.value || "1", 10) + 1;
    });
  });

  // Product detail: pack-size option switching
  var packOptions = document.querySelectorAll(".pack-size-option");
  if (packOptions.length) {
    var priceEl = document.getElementById("selectedPrice");
    var mrpEl = document.getElementById("selectedMrp");
    var savingsEl = document.getElementById("savingsText");
    var skuEl = document.getElementById("selectedSku");
    var variantInput = document.getElementById("variantIdInput");
    var stockStatus = document.getElementById("stockStatus");
    var addToCartBtn = document.getElementById("addToCartBtn");
    var mainImage = document.getElementById("mainProductImage");

    packOptions.forEach(function (btn) {
      btn.addEventListener("click", function () {
        packOptions.forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");

        var price = parseFloat(btn.dataset.price);
        var mrp = parseFloat(btn.dataset.mrp);
        var stock = parseInt(btn.dataset.stock, 10);

        if (priceEl) priceEl.textContent = "₹" + price.toFixed(2).replace(".00", "");
        if (mrpEl) {
          if (mrp > price) {
            mrpEl.textContent = "₹" + mrp.toFixed(2).replace(".00", "");
            mrpEl.style.display = "";
          } else {
            mrpEl.style.display = "none";
          }
        }
        if (savingsEl) {
          if (mrp > price) {
            var pct = Math.round(((mrp - price) / mrp) * 100);
            savingsEl.textContent = pct + "% off";
          } else {
            savingsEl.textContent = "";
          }
        }
        if (skuEl) skuEl.textContent = btn.dataset.sku;
        if (variantInput) variantInput.value = btn.dataset.variantId;
        if (stockStatus) {
          stockStatus.innerHTML = stock > 0
            ? '<span class="badge bg-success-subtle text-success">In Stock</span>'
            : '<span class="badge bg-danger-subtle text-danger">Out of Stock</span>';
        }
        if (addToCartBtn) addToCartBtn.disabled = stock <= 0;
        if (mainImage && btn.dataset.image) mainImage.src = btn.dataset.image;
      });
    });
  }

  // Product detail: gallery thumbnail click
  document.querySelectorAll(".product-gallery__thumbs .thumb").forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      document.querySelectorAll(".product-gallery__thumbs .thumb").forEach(function (t) { t.classList.remove("active"); });
      thumb.classList.add("active");
      var main = document.getElementById("mainProductImage");
      if (main) main.src = thumb.dataset.full;
    });
  });
});
