document.addEventListener('DOMContentLoaded', () => {
  // Controle da Sidebar Recolhível
  const tocToggle = document.getElementById('toc-toggle');
  const sidebarToc = document.getElementById('sidebar-toc');

  if (tocToggle && sidebarToc) {
    tocToggle.addEventListener('click', () => {
      sidebarToc.classList.toggle('collapsed');
    });
  }

  // Controle do Slider da Seção 3 (Modelos)
  const modelsTrack = document.getElementById('modelsTrack');
  const prevBtn = document.getElementById('prevModelBtn');
  const nextBtn = document.getElementById('nextModelBtn');
  const counter = document.getElementById('sliderCounter');
  const totalModels = 3;
  let currentIndex = 0;

  function goToSlide(index) {
    currentIndex = index;
    modelsTrack.style.transform = `translateX(-${currentIndex * 100}%)`;
    if (counter) {
      counter.textContent = `${currentIndex + 1} / ${totalModels}`;
    }
  }

  if (prevBtn && nextBtn) {
    prevBtn.addEventListener('click', () => {
      const newIdx = (currentIndex - 1 + totalModels) % totalModels;
      goToSlide(newIdx);
    });

    nextBtn.addEventListener('click', () => {
      const newIdx = (currentIndex + 1) % totalModels;
      goToSlide(newIdx);
    });
  }

  // Links do menu lateral direcionando diretamente ao slide correto
  document.querySelectorAll('.toc-link.sub').forEach(link => {
    link.addEventListener('click', () => {
      const slideIdx = parseInt(link.getAttribute('data-slide'));
      if (!isNaN(slideIdx)) {
        goToSlide(slideIdx);
      }
    });
  });

  // Filtros da Tabela Comparativa (Seção 4)
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
          if (col.classList.contains(filter)) {
            col.style.display = 'table-cell';
          } else {
            col.style.display = 'none';
          }
        });
      }
    });
  });
});