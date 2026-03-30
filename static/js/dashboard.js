/**
 * TechStock — Dashboard Charts
 * Reads data from window.dashboardData (set by the template).
 * Supports dark mode, animated counters, and live theme switching.
 */
document.addEventListener('DOMContentLoaded', function() {
  var D = window.dashboardData;

  // ── Dark Mode Detection ──
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';

  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.font.size   = 12;
  Chart.defaults.color       = isDark ? '#9ca3b4' : '#6c757d';
  Chart.defaults.borderColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

  // ── Theme-aware helpers ──
  function tooltipBg()    { return isDark ? '#353b50' : '#1a1a2e'; }
  function tooltipTitle()  { return isDark ? '#dce1eb' : '#fff'; }
  function tooltipBody()   { return isDark ? '#dce1eb' : '#fff'; }
  function gridColor()     { return isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)'; }
  function doughnutBorder(){ return isDark ? '#232839' : '#fff'; }

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

  // ── Initialize charts only if data exists ──
  if (D) {

    // ── 1. Movimientos 7 días (line) ──
    if (document.getElementById('chartMovimientos')) {
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
            tooltip: {
              backgroundColor: tooltipBg(),
              titleColor: tooltipTitle(),
              bodyColor: tooltipBody(),
              padding: 10,
              cornerRadius: 8
            }
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 11 } } },
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, precision: 0 },
              grid: { color: gridColor() }
            }
          }
        }
      });
    }

    // ── 2. Ventas 7 días (bar) ──
    if (document.getElementById('chartVentas7d')) {
      new Chart(document.getElementById('chartVentas7d'), {
        type: 'bar',
        data: {
          labels: D.labels7d,
          datasets: [{
            label: 'Ventas ($)',
            data: D.ventas7d,
            backgroundColor: isDark ? 'rgba(25, 135, 84, 0.8)' : 'rgba(25, 135, 84, 0.7)',
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
              backgroundColor: tooltipBg(),
              titleColor: tooltipTitle(),
              bodyColor: tooltipBody(),
              padding: 10,
              cornerRadius: 8,
              callbacks: {
                label: function(ctx) { return ' $' + ctx.parsed.y.toLocaleString('es-CO'); }
              }
            }
          },
          scales: {
            x: { grid: { display: false } },
            y: {
              beginAtZero: true,
              grid: { color: gridColor() },
              ticks: { callback: function(v) { return '$' + v.toLocaleString('es-CO'); } }
            }
          }
        }
      });
    }

    // ── 3. Inventario por categoría (doughnut) ──
    if (D.catLabels && D.catLabels.length > 0 && document.getElementById('chartCategorias')) {
      new Chart(document.getElementById('chartCategorias'), {
        type: 'doughnut',
        data: {
          labels: D.catLabels,
          datasets: [{
            data: D.catValores,
            backgroundColor: PALETTE.slice(0, D.catLabels.length),
            borderWidth: 2,
            borderColor: doughnutBorder(),
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
                      strokeStyle: doughnutBorder(),
                      lineWidth: 2,
                      index: i
                    };
                  });
                }
              }
            },
            tooltip: {
              backgroundColor: tooltipBg(),
              titleColor: tooltipTitle(),
              bodyColor: tooltipBody(),
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
    if (document.getElementById('chartDeudas')) {
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
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: tooltipBg(),
              titleColor: tooltipTitle(),
              bodyColor: tooltipBody()
            }
          },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor() } },
            y: { grid: { display: false } }
          }
        }
      });
    }

    // ── 5. Estado de Facturas (bar horizontal) ──
    if (document.getElementById('chartFacturas')) {
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
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: tooltipBg(),
              titleColor: tooltipTitle(),
              bodyColor: tooltipBody()
            }
          },
          scales: {
            x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor() } },
            y: { grid: { display: false } }
          }
        }
      });
    }

  } // end if (D)

  // ── Animated Number Counters ──
  function animateCounters() {
    document.querySelectorAll('[data-count-to]').forEach(function(el) {
      var target = parseFloat(el.dataset.countTo);
      var isMoney = el.dataset.countMoney === 'true';
      var prefix = el.dataset.countPrefix || '';
      var duration = 800;
      var start = performance.now();

      function formatNum(n) {
        if (isMoney) {
          return prefix + Math.round(n).toLocaleString('es-CO');
        }
        return prefix + Math.round(n).toLocaleString('es-CO');
      }

      function step(ts) {
        var progress = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        el.textContent = formatNum(target * eased);
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = formatNum(target);
      }

      // Only animate if element is visible (IntersectionObserver)
      if (window.IntersectionObserver) {
        var observer = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting) {
              requestAnimationFrame(step);
              observer.unobserve(el);
            }
          });
        }, { threshold: 0.1 });
        observer.observe(el);
      } else {
        requestAnimationFrame(step);
      }
    });
  }

  animateCounters();

  // ── Theme Change Listener (MutationObserver) ──
  var themeObserver = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      if (m.attributeName === 'data-theme') {
        var nowDark = document.documentElement.getAttribute('data-theme') === 'dark';
        Chart.defaults.color = nowDark ? '#9ca3b4' : '#6c757d';
        Chart.defaults.borderColor = nowDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
        // Update all existing chart instances
        Object.keys(Chart.instances).forEach(function(key) {
          var chart = Chart.instances[key];
          if (chart.options.scales) {
            Object.keys(chart.options.scales).forEach(function(scaleKey) {
              if (chart.options.scales[scaleKey].grid) {
                chart.options.scales[scaleKey].grid.color = nowDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
              }
              if (chart.options.scales[scaleKey].ticks) {
                chart.options.scales[scaleKey].ticks.color = nowDark ? '#9ca3b4' : '#6c757d';
              }
            });
          }
          if (chart.options.plugins && chart.options.plugins.tooltip) {
            chart.options.plugins.tooltip.backgroundColor = nowDark ? '#353b50' : '#1a1a2e';
            chart.options.plugins.tooltip.titleColor = nowDark ? '#dce1eb' : '#fff';
            chart.options.plugins.tooltip.bodyColor = nowDark ? '#dce1eb' : '#fff';
          }
          // For doughnut/pie charts — update border colors
          if (chart.config.type === 'doughnut' || chart.config.type === 'pie') {
            chart.data.datasets.forEach(function(ds) {
              ds.borderColor = nowDark ? '#232839' : '#fff';
            });
          }
          chart.update('none');
        });
      }
    });
  });
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
});
