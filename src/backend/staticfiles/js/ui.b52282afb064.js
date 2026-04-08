document.addEventListener("DOMContentLoaded", () => {
  // Mobile menu functionality
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.querySelector('.sidebar');
  
  if (mobileMenuBtn && sidebar) {
    function closeSidebar() {
      mobileMenuBtn.classList.remove('open');
      sidebar.classList.remove('mobile-open');
      document.body.style.overflow = '';
    }

    mobileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (sidebar.classList.contains('mobile-open')) {
        closeSidebar();
      } else {
        mobileMenuBtn.classList.add('open');
        sidebar.classList.add('mobile-open');
        if (window.innerWidth <= 768) document.body.style.overflow = 'hidden';
      }
    });

    // Close when clicking outside the sidebar on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 768 && sidebar.classList.contains('mobile-open')) {
        if (!sidebar.contains(e.target) && e.target !== mobileMenuBtn) {
          closeSidebar();
        }
      }
    });

    // Close when clicking a nav link on mobile
    sidebar.querySelectorAll('.sidebar-nav a').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 768) closeSidebar();
      });
    });

    // Re-enable scroll if window is resized above mobile breakpoint
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768) {
        document.body.style.overflow = '';
      }
    });
  }

  const canvas = document.getElementById("spendingChart");
  if (canvas) {
    const dataElement = document.getElementById("spending-data");

    let labels = ["No expenses yet"];
    let values = [1];

    if (dataElement) {
      const payload = JSON.parse(dataElement.textContent);
      if (payload.labels.length > 0) {
        labels = payload.labels;
        values = payload.values;
      }
    }

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: ["#5c7069", "#7d9088", "#a2b3ac", "#d5ded9", "#e8b4a0", "#c4956a", "#8fb8ad", "#b07d62", "#d4c5b0"],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        }
      }
    });
  }

  document.querySelectorAll(".progress-fill[data-width]").forEach((el) => {
    const width = el.dataset.width || 30;
    el.style.width = `${width}%`;
  });
});


let lastUnreadCount = 0;

function ensureToastContainer() {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  return container;
}

function showInboxToast(message) {
  const container = ensureToastContainer();

  const toast = document.createElement("div");
  toast.className = "toast toast-info";
  toast.innerHTML = `
    <img src="/static/images/favicon.png" alt="" style="width:28px;height:28px;object-fit:contain;flex-shrink:0;border-radius:6px;">
    <span class="toast-text">${message}</span>
    <button class="toast-close">✕</button>
  `;

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast-fade");
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

function updateUnreadBadge(count) {
  const badge = document.getElementById("inbox-unread-badge");
  if (!badge) return;

  if (count > 0) {
    badge.textContent = count;
    badge.style.display = "inline-flex";
  } else {
    badge.style.display = "none";
  }
}

function checkUnreadMessages() {
  if (!window.unreadMessageUrl) return;

  fetch(window.unreadMessageUrl, {
    headers: {
      "X-Requested-With": "XMLHttpRequest"
    }
  })
    .then(response => response.json())
    .then(data => {
      const newCount = data.unread_count || 0;

      if (lastUnreadCount !== 0 && newCount > lastUnreadCount) {
        showInboxToast("You have a new message");
      }

      lastUnreadCount = newCount;
      updateUnreadBadge(newCount);
    })
    .catch(error => {
      console.log("Unread check failed:", error);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  checkUnreadMessages();
  setInterval(checkUnreadMessages, 5000);
});