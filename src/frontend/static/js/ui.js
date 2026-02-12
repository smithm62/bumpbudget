document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("spendingChart");
  if (!canvas) return;

  new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Housing", "Baby", "Food", "Transport"],
      datasets: [{
        data: [900, 350, 450, 250],
        backgroundColor: ["#5c7069", "#7d9088", "#a2b3ac", "#d5ded9"],
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
});
