/**
 * Electricity Billing and Consumption Management System
 * Dynamic Chart.js Visualizations (dashboard.js)
 */

document.addEventListener("DOMContentLoaded", async () => {
  const chartContainer = document.getElementById("monthlyConsumptionChart");
  if (!chartContainer) return;

  try {
    const res = await fetch("/api/dashboard-charts");
    if (!res.ok) throw new Error("Failed to load chart data");
    const data = await res.json();

    // -------------------------------------------------------------------------
    // CHART 1: Monthly Electricity Consumption (Bar Chart)
    // -------------------------------------------------------------------------
    const ctx1 = document.getElementById("monthlyConsumptionChart").getContext("2d");
    new Chart(ctx1, {
      type: "bar",
      data: {
        labels: data.consumption.labels,
        datasets: [{
          label: "Total Units Consumed (kWh)",
          data: data.consumption.data,
          backgroundColor: "rgba(16, 185, 129, 0.75)",
          borderColor: "#10b981",
          borderWidth: 1.5,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Units (kWh)" },
            grid: { color: "#f1f5f9" }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // CHART 2: Monthly Revenue Collected vs Billed
    // -------------------------------------------------------------------------
    const ctx2 = document.getElementById("revenueChart").getContext("2d");
    new Chart(ctx2, {
      type: "bar",
      data: {
        labels: data.revenue.labels,
        datasets: [
          {
            label: "Collected (₹)",
            data: data.revenue.collected,
            backgroundColor: "#10b981",
            borderRadius: 4
          },
          {
            label: "Billed Total (₹)",
            data: data.revenue.billed,
            backgroundColor: "#1e3a8a",
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => "₹" + val.toLocaleString()
            },
            grid: { color: "#f1f5f9" }
          },
          x: {
            grid: { display: false }
          }
        }
      }
    });

    // -------------------------------------------------------------------------
    // CHART 3: Paid vs Unpaid Bills (Doughnut)
    // -------------------------------------------------------------------------
    const ctx3 = document.getElementById("paymentStatusChart").getContext("2d");
    new Chart(ctx3, {
      type: "doughnut",
      data: {
        labels: data.status.labels,
        datasets: [{
          data: data.status.data,
          backgroundColor: ["#10b981", "#f59e0b", "#ef4444"],
          borderWidth: 2,
          borderColor: "#ffffff"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        },
        cutout: "65%"
      }
    });

    // -------------------------------------------------------------------------
    // CHART 4: Top 5 Consumers by Electricity Consumption (Horizontal Bar)
    // -------------------------------------------------------------------------
    const ctx4 = document.getElementById("topConsumersChart").getContext("2d");
    new Chart(ctx4, {
      type: "bar",
      data: {
        labels: data.top_consumers.labels,
        datasets: [{
          label: "Lifetime Consumption (kWh)",
          data: data.top_consumers.data,
          backgroundColor: "rgba(30, 58, 138, 0.85)",
          borderColor: "#1e3a8a",
          borderWidth: 1,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            beginAtZero: true,
            title: { display: true, text: "kWh" },
            grid: { color: "#f1f5f9" }
          },
          y: {
            grid: { display: false }
          }
        }
      }
    });

  } catch (err) {
    console.error("Dashboard charts error:", err);
  }
});
