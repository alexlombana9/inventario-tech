/**
 * TechStock — Dashboard Charts
 * Reads data from window.dashboardData (set by the template).
 */
document.addEventListener('DOMContentLoaded', function() {
  var D = window.dashboardData;
  if (!D) return;

  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = '#6c757d';

  // ── Palette ──
  var GREEN  = 'rgba(25, 135, 84, 0.85)';
  var RED    = 'rgba(220, 53, 69, 0.85)';
  var BLUE   = 'rgba(13, 110, 253, 0.85)';
  var YELLOW = 'rgba(255, 193, 7, 0.85)';
  var PALETTE = [
    '#0d6efd','#198754','#fd7e14','#6f42c1',
    '#20c997','#dc3545','#ffc107','#0dcaf0',
    '#6c757d','#d63384'
  ];

  // ── 1. Movimientos 7 días (line) ──
  new Chart(document.getElementById('chartMovimientos'), {
    type: 'line',
    data: {
      labels: D.labels7d,
      datasets: [
        {
          label: 'Entradas',
          data: D.entradas7d,
          borderColor: GREEN,
          backgroundColor: 'rgba(25,135,84,0.1)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: GREEN,
        },
        {
          label: 'Salidas',
          data: D.salidas7d,
          borderColor: RED,
          backgroundColor: 'rgba(220,53,69,0.08)',
          borderWidth: 2.5,
          fill: true,
          tension: 0.35,
          pointRadius: 4,
          pointHoverRadius: 6,
          pointBackgroundColor: RED,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 12, padding: 14 } },
        tooltip: { backgroundColor: '#1a1a2e', padding: 10, cornerRadius: 8 }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, precision: 0 },
          grid: { color: 'rgba(0,0,0,0.05)' }
        }
      }
    }
  });

  // ── 2. Ventas 7 días (bar) ──
  new Chart(document.getElementById('chartVentas7d'), {
    type: 'bar',
    data: {
      labels: D.labels7d,
      datasets: [{
        label: 'Ventas ($)',
        data: D.ventas7d,
        backgroundColor: 'rgba(25, 135, 84, 0.7)',
        borderColor: GREEN,
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a2e', padding: 10, cornerRadius: 8,
          callbacks: {
            label: function(ctx) { return ' $' + ctx.parsed.y.toLocaleString('es-CO'); }
          }
        }
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { callback: function(v) { return '$' + v.toLocaleString('es-CO'); } }
        }
      }
    }
  });

  // ── 3. Inventario por categoría (doughnut) ──
  if (D.catLabels.length > 0) {
    new Chart(document.getElementById('chartCategorias'), {
      type: 'doughnut',
      data: {
        labels: D.catLabels,
        datasets: [{
          data: D.catValores,
          backgroundColor: PALETTE.slice(0, D.catLabels.length),
          borderWidth: 2,
          borderColor: '#fff',
          hoverOffset: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              boxWidth: 12, padding: 10,
              font: { size: 11 },
              generateLabels: function(chart) {
                var ds = chart.data.datasets[0];
                var total = ds.data.reduce(function(a, b) { return a + b; }, 0);
                return chart.data.labels.map(function(lbl, i) {
                  var pct = total > 0 ? ((ds.data[i] / total) * 100).toFixed(1) : 0;
                  return {
                    text: lbl + ' (' + pct + '%)',
                    fillStyle: ds.backgroundColor[i],
                    strokeStyle: '#fff',
                    lineWidth: 2,
                    index: i
                  };
                });
              }
            }
          },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                var total = ctx.dataset.data.reduce(function(a, b) { return a + b; }, 0);
                var pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return ' $' + ctx.parsed.toLocaleString('es', {minimumFractionDigits: 2}) + ' (' + pct + '%)';
              }
            }
          }
        }
      }
    });
  }

  // ── 4. Estado de Deudas (bar horizontal) ──
  new Chart(document.getElementById('chartDeudas'), {
    type: 'bar',
    data: {
      labels: ['Pendiente', 'Parcial', 'Pagado'],
      datasets: [{
        data: D.deudas,
        backgroundColor: [YELLOW, BLUE, GREEN],
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1a1a2e' } },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: 'rgba(0,0,0,0.05)' } },
        y: { grid: { display: false } }
      }
    }
  });

  // ── 5. Estado de Facturas (bar horizontal) ──
  new Chart(document.getElementById('chartFacturas'), {
    type: 'bar',
    data: {
      labels: ['Pendiente', 'Parcial', 'Cobrada'],
      datasets: [{
        data: D.facturas,
        backgroundColor: [YELLOW, BLUE, GREEN],
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { backgroundColor: '#1a1a2e' } },
      scales: {
        x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: 'rgba(0,0,0,0.05)' } },
        y: { grid: { display: false } }
      }
    }
  });
});
