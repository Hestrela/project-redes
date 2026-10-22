document.addEventListener('DOMContentLoaded', () => {
  // 1. Controle da Sidebar (TOC Toggle)
  const tocToggle = document.getElementById('toc-toggle');
  const sidebarToc = document.getElementById('sidebar-toc');
  if (tocToggle && sidebarToc) {
    tocToggle.addEventListener('click', () => {
      sidebarToc.classList.toggle('collapsed');
    });
  }

  // 2. Slider dos Modelos Avaliados (Seção 2)
  const modelsTrack = document.getElementById('modelsTrack');
  const prevBtn = document.getElementById('prevModelBtn');
  const nextBtn = document.getElementById('nextModelBtn');
  const counter = document.getElementById('sliderCounter');
  const totalModels = 3;
  let currentIndex = 0;

  function goToSlide(index) {
    currentIndex = index;
    if (modelsTrack) {
      modelsTrack.style.transform = `translateX(-${currentIndex * 100}%)`;
    }
    if (counter) {
      counter.textContent = `${currentIndex + 1} / ${totalModels}`;
    }
  }

  if (prevBtn && nextBtn) {
    prevBtn.addEventListener('click', () => {
      goToSlide((currentIndex - 1 + totalModels) % totalModels);
    });
    nextBtn.addEventListener('click', () => {
      goToSlide((currentIndex + 1) % totalModels);
    });
  }

  // Sublinks da Sidebar para acionar o slider diretamente
  document.querySelectorAll('.toc-link.sub').forEach(link => {
    link.addEventListener('click', () => {
      const slideIdx = parseInt(link.getAttribute('data-slide'), 10);
      if (!isNaN(slideIdx)) {
        goToSlide(slideIdx);
      }
    });
  });

  // 3. Filtros do Quadro Comparativo (Seção 3)
  const filterBtns = document.querySelectorAll('.compare-filter-btn');
  const compareTable = document.getElementById('compareTable');

  if (compareTable) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const filter = btn.getAttribute('data-filter');
        const allModelCols = compareTable.querySelectorAll('.col-dt, .col-rf, .col-xgb');

        if (filter === 'all') {
          allModelCols.forEach(col => (col.style.display = ''));
        } else {
          allModelCols.forEach(col => {
            col.style.display = col.classList.contains(filter) ? 'table-cell' : 'none';
          });
        }
      });
    });
  }
});