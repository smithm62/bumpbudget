document.addEventListener("DOMContentLoaded", () => {
  const ctx = document.getElementById("spendingChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Housing", "Baby", "Food", "Transport"],
      datasets: [{
        data: [900, 350, 450, 250],
        backgroundColor: [
          "#5c7069",  
          "#7d9088",  
          "#a2b3ac",  
          "#d5ded9"  
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom"
        }
      }
    }
  });
});