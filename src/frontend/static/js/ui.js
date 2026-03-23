document.addEventListener("DOMContentLoaded", () => {
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
