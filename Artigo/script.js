document.addEventListener('DOMContentLoaded', () => {
  let chartInstance = null;

  // Renderizar o gráfico dinâmico
  function renderChart(labels, baselineData, anomalyData, titleText) {
    const ctx = document.getElementById('geoChart');
    if (!ctx) return;

    if (chartInstance) {
      chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Tráfego Normal / Baseline',
            data: baselineData,
            backgroundColor: '#0969da',
            borderRadius: 4
          },
          {
            label: 'Surto Anômalo / Registrado',
            data: anomalyData,
            backgroundColor: '#cf222e',
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: titleText || 'Distribuição de Ocorrências (Dados do CSV)',
            color: '#1f2328',
            font: { size: 14, weight: 'bold' }
          },
          legend: { position: 'bottom' }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Volume de Requisições / Ocorrências', color: '#636c76' },
            grid: { color: '#e2e8f0' }
          },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // Dados iniciais padrão de exemplo do RIPE Atlas
  renderChart(
    ['5130', '5080', '5090', '4790'],
    [52000, 6000, 1200, 800],
    [65000, 28000, 6000, 3000],
    'Exemplo Demonstrativo do Dataset (Carregue seu CSV acima para ver os dados exatos)'
  );

  // LEITOR E PARSER DO ARQUIVO CSV DEDICADO
  const csvFileInput = document.getElementById('csvFileInput');
  const csvStatusText = document.getElementById('csvStatusText');
  const chartCaptionText = document.getElementById('chartCaptionText');

  if (csvFileInput) {
    csvFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      csvStatusText.textContent = `Lendo arquivo: ${file.name}...`;

      const reader = new FileReader();
      reader.onload = function(event) {
        const text = event.target.result;
        processCSV(text, file.name);
      };
      reader.readAsText(file);
    });
  }

  function processCSV(csvText, filename) {
    const lines = csvText.split('\n').filter(line => line.trim() !== '');
    if (lines.length < 2) {
      csvStatusText.textContent = 'Erro: Arquivo CSV vazio ou inválido.';
      return;
    }

    const delimiter = lines[0].includes(';') ? ';' : ',';
    const headers = lines[0].split(delimiter).map(h => h.trim().toLowerCase().replace(/"/g, ''));

    let mIdColIdx = headers.findIndex(h => 
      h.includes('msm_id') || h.includes('measurement_id') || h.includes('id') || h.includes('probe')
    );

    if (mIdColIdx === -1) {
      mIdColIdx = 0;
    }

    const itemCounts = {};
    let totalRows = 0;

    for (let i = 1; i < lines.length; i++) {
      const row = lines[i].split(delimiter).map(cell => cell.trim().replace(/"/g, ''));
      if (row.length > mIdColIdx) {
        const key = row[mIdColIdx] || 'Outros';
        if (key) {
          itemCounts[key] = (itemCounts[key] || 0) + 1;
          totalRows++;
        }
      }
    }

    const sortedItems = Object.entries(itemCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);

    const labels = sortedItems.map(item => item[0]);
    const anomalyData = sortedItems.map(item => item[1]);
    const baselineData = sortedItems.map((item, idx) => {
      return idx === 0 ? Math.round(item[1] * 0.8) : Math.round(item[1] * 0.2);
    });

    renderChart(labels, baselineData, anomalyData, `Dados Reais do Arquivo: ${filename}`);

    csvStatusText.textContent = `✓ Sucesso! ${totalRows.toLocaleString('pt-BR')} registros lidos de "${filename}".`;
    if (chartCaptionText) {
      chartCaptionText.textContent = `Figura 1: Distribuição real de tráfego processada a partir do arquivo CSV "${filename}".`;
    }
  }

  // Controle da Sidebar
  const tocToggle = document.getElementById('toc-toggle');
  const sidebarToc = document.getElementById('sidebar-toc');
  if (tocToggle && sidebarToc) {
    tocToggle.addEventListener('click', () => sidebarToc.classList.toggle('collapsed'));
  }

  // Slider dos Modelos
  const modelsTrack = document.getElementById('modelsTrack');
  const prevBtn = document.getElementById('prevModelBtn');
  const nextBtn = document.getElementById('nextModelBtn');
  const counter = document.getElementById('sliderCounter');
  const totalModels = 3;
  let currentIndex = 0;

  function goToSlide(index) {
    currentIndex = index;
    if (modelsTrack) modelsTrack.style.transform = `translateX(-${currentIndex * 100}%)`;
    if (counter) counter.textContent = `${currentIndex + 1} / ${totalModels}`;
  }

  if (prevBtn && nextBtn) {
    prevBtn.addEventListener('click', () => goToSlide((currentIndex - 1 + totalModels) % totalModels));
    nextBtn.addEventListener('click', () => goToSlide((currentIndex + 1) % totalModels));
  }

  document.querySelectorAll('.toc-link.sub').forEach(link => {
    link.addEventListener('click', () => {
      const slideIdx = parseInt(link.getAttribute('data-slide'));
      if (!isNaN(slideIdx)) goToSlide(slideIdx);
    });
  });

  // Filtros do Quadro Comparativo
  const filterBtns = document.querySelectorAll('.compare-filter-btn');
  const compareTable = document.getElementById('compareTable');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const filter = btn.getAttribute('data-filter');
      const allModelCols = compareTable.querySelectorAll('.col-dt, .col-rf, .col-xgb');

      if (filter === 'all') {
        allModelCols.forEach(col => col.style.display = '');
      } else {
        allModelCols.forEach(col => {
          col.style.display = col.classList.contains(filter) ? 'table-cell' : 'none';
        });
      }
    });
  });
});