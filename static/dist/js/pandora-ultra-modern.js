/**
 * Pandora ERP - Ultra Modern JavaScript Framework
 * Version: 5.1.0 (Fully Unified & Refactored)
 * Author: Pandora Team
 * Date: July 2025
 */

class PandoraUltraModern {
  constructor() {
    // Configuration
    this.config = {
      debug: true,
      animationDuration: 300,
      mobileBreakpoint: 768,
      apiTimeout: 30000,
      searchDebounceDelay: 300,
      toastDuration: 5000,
      autoSaveInterval: 30000
    };

    // State management
    this.state = {
      theme: localStorage.getItem('theme') || 'light',
      sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',
      isMobile: window.innerWidth <= this.config.mobileBreakpoint,
      sidebarMobileVisible: false,
      activeSubmenu: null,
      searchActive: false,
      calculatorVisible: false,
      notifications: [],
      user: null,
      realTimeConnection: null,
      // Form state
      currentSection: 0,
      totalSections: 0,
      formData: {},
      sectionValidation: {},
      autoSaveTimeout: null,
      formDirty: false
    };

    // DOM Elements cache
    this.elements = {
      body: document.body,
      sidebar: null,
      sidebarToggle: null,
      mobileSidebarToggle: null,
      mobileBackdrop: null,
      themeToggle: null,
      searchInput: null,
      searchResults: null,
      calculator: null,
      toastContainer: null,
      loadingOverlay: null,
      mainForm: null,
      formSections: null,
      formSteps: null,
      nextButtons: null,
      prevButtons: null,
      formProgress: null,
      autoSaveIndicator: null,
      // Dashboard elements will be cached in their setup method
      dashboardGrid: null,
      customizeToggle: null,
      customizationSidebar: null
    };

    // CSS Classes
    this.cssClasses = {
      sidebarCollapsed: 'collapsed',
      sidebarMobileVisible: 'mobile-visible',
      backdropShow: 'show',
      submenuShow: 'show',
      themeLight: 'light',
      themeDark: 'dark',
      loadingHidden: 'hidden',
      calculatorVisible: 'visible',
      searchResultsActive: 'active',
      sectionActive: 'active',
      sectionCompleted: 'completed',
      sectionHidden: 'hidden',
      slideInRight: 'slide-in-right',
      slideInLeft: 'slide-in-left',
      autoSaveVisible: 'visible'
    };

    this.eventListeners = new Map();
    this.activeTimers = new Set();
    this.performance = { metrics: new Map(), observers: new Map() };

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.init());
    } else {
      this.init();
    }
  }

  /**
   * Initialize application
   */
  async init() {
    try {
      this.log('Initializing Pandora Ultra Modern...');

      this.cacheGlobalElements();

      this.setupTheme();
      this.setupSidebar();
      this.setupSearch();
      this.setupCalculator();
      this.setupNotifications();
      this.setupKeyboardShortcuts();
      this.setupResponsive();
      this.setupRealTimeUpdates();
      this.setupPerformanceMonitoring();

      // MODULAR INITIALIZATION: Setup page-specific modules based on body class
      // To activate a module, add the corresponding class to the <body> tag in your Django template.
      if (this.elements.body.classList.contains('form-page') || this.elements.mainForm) {
        this.cacheFormElements();
        this.setupFormNavigation();
        this.setupFormHelpers(); // Initializes saveAnd... functions
      }
      if (this.elements.body.classList.contains('list-page')) {
        this.setupListView();
      }
      if (this.elements.body.classList.contains('detail-page')) {
        this.setupDetailView();
      }
      if (this.elements.body.classList.contains('delete-page')) {
        this.setupDeleteView();
      }
      if (this.elements.body.classList.contains('calendar-page')) {
        this.setupCalendarView();
      }
      if (this.elements.body.classList.contains('dashboard-page')) {
        this.setupDashboardWidgets();
      }

      this.hideLoadingOverlay();
      this.fireEvent('pandora:ready');
      this.log('Pandora Ultra Modern initialized successfully');
      // Integrar eventos externos (user_management) após ready
      this.integrateExternalModuleEvents();
    } catch (error) {
      this.logError('Failed to initialize:', error);
    }
  }

  /**
   * Integra eventos emitidos por módulos externos (ex: user_management/user_actions.js)
   */
  integrateExternalModuleEvents() {
    // 2FA toggled
    document.addEventListener('user:2faToggled', (e) => {
      const { enabled } = e.detail || {};
      this.showNotification({
        title: 'Segurança',
        message: enabled ? 'Autenticação de dois fatores ativada.' : 'Autenticação de dois fatores desativada.',
        type: enabled ? 'success' : 'warning'
      });
    });
    // Sessão terminada
    document.addEventListener('user:sessionTerminated', () => {
      this.showNotification({
        title: 'Sessões',
        message: 'Sessão encerrada com sucesso.',
        type: 'info'
      });
    });
    document.addEventListener('user:sessionsTerminatedAll', (e) => {
      const qtd = e.detail?.encerradas || 0;
      this.showNotification({
        title: 'Sessões',
        message: `${qtd} sessão(ões) encerradas.`,
        type: 'warning'
      });
    });
    // Eventos de WebSocket de sessões (criadas / atualizadas / terminadas)
    document.addEventListener('sessions:realtimeUpdate', (e) => {
      const { event, session } = e.detail || {};
      if (!session) return;
      if (event === 'created') {
        this.showNotification({ title: 'Sessões', message: `Nova sessão: ${session.user} (${session.ip_address || 'IP desconhecido'})`, type: 'info' });
      } else if (event === 'terminated') {
        this.showNotification({ title: 'Sessões', message: `Sessão encerrada: ${session.user}`, type: 'secondary' });
      }
      // Atualizar contador se presente
      try {
        const totalEl = document.getElementById('total-sessions');
        if (totalEl) {
          // Reconta baseado em linhas atuais (evita estado incorreto)
          const count = document.querySelectorAll('#sessions-table tbody tr[data-session-id]').length;
          totalEl.textContent = count;
        }
      } catch (_) { }
    });
    // Ações iniciais do módulo de usuário carregadas
    document.addEventListener('user:actionsInit', () => {
      this.log('User management actions initialized (event bridge ok)');
    });
    // Notificação genérica de UI (ex: ui:notify vindo de módulos externos)
    document.addEventListener('ui:notify', (e) => {
      const { type = 'info', title = 'Info', message = '' } = e.detail || {};
      this.showNotification({ title, message, type });
    });
  }

  /**
   * Cache global DOM elements (non-form related)
   */
  cacheGlobalElements() {
    this.elements.sidebar = document.querySelector('.app-sidebar');
    this.elements.sidebarToggle = document.querySelector('.sidebar-toggle');
    this.elements.mobileSidebarToggle = document.querySelector('.mobile-sidebar-toggle');
    this.elements.mobileBackdrop = document.querySelector('.mobile-backdrop');
    this.elements.themeToggle = document.querySelector('.theme-toggle');
    this.elements.searchInput = document.querySelector('#global-search');
    this.elements.searchResults = document.querySelector('#search-results');
    this.elements.calculator = document.querySelector('.floating-calculator');
    this.elements.toastContainer = document.querySelector('.toast-container');
    this.elements.loadingOverlay = document.querySelector('.loading-overlay');
    this.elements.mainForm = document.querySelector('#main-form, form, .main-form');
  }

  /**
   * Cache form-specific DOM elements, scoped to the main form for robustness.
   */
  cacheFormElements() {
    if (!this.elements.mainForm) return;
    this.elements.formSections = this.elements.mainForm.querySelectorAll('.form-section, .section-content, [data-section]');
    this.elements.formSteps = this.elements.mainForm.querySelectorAll('.step, .form-step, [data-step]');
    this.elements.nextButtons = this.elements.mainForm.querySelectorAll('.btn-next-section, [data-action="next-section"]');
    this.elements.prevButtons = this.elements.mainForm.querySelectorAll('.btn-prev-section, [data-action="prev-section"]');
    this.elements.formProgress = this.elements.mainForm.querySelector('.form-progress, .progress-container');
    this.elements.autoSaveIndicator = this.elements.mainForm.querySelector('.auto-save-indicator, .saving-indicator');
  }

  /**
   * Setup theme management
   */
  setupTheme() {
    document.documentElement.setAttribute('data-theme', this.state.theme);
    if (this.elements.themeToggle) {
      this.addEventListener(this.elements.themeToggle, 'click', () => this.toggleTheme());
    }
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    this.addEventListener(mediaQuery, 'change', (e) => {
      if (!localStorage.getItem('theme')) {
        this.state.theme = e.matches ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', this.state.theme);
      }
    });
  }

  toggleTheme() {
    this.state.theme = this.state.theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', this.state.theme);
    localStorage.setItem('theme', this.state.theme);
    this.fireEvent('pandora:themeChanged', { theme: this.state.theme });
  }

  /**
   * Setup sidebar functionality
   */
  setupSidebar() {
    if (!this.elements.sidebar) return;
    if (this.state.sidebarCollapsed && !this.state.isMobile) {
      this.elements.sidebar.classList.add(this.cssClasses.sidebarCollapsed);
    }
    if (this.elements.sidebarToggle) {
      this.addEventListener(this.elements.sidebarToggle, 'click', () => this.toggleSidebar());
    }
    if (this.elements.mobileSidebarToggle) {
      this.addEventListener(this.elements.mobileSidebarToggle, 'click', () => this.toggleMobileSidebar());
    }
    if (this.elements.mobileBackdrop) {
      this.addEventListener(this.elements.mobileBackdrop, 'click', () => this.closeMobileSidebar());
    }
    this.setupSubmenus(); // This is the modern and active method
    this.setupSwipeGestures();
  }

  toggleSidebar() {
    if (this.state.isMobile) return;
    this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
    this.elements.sidebar.classList.toggle(this.cssClasses.sidebarCollapsed);
    localStorage.setItem('sidebarCollapsed', this.state.sidebarCollapsed);
    this.fireEvent('pandora:sidebarToggled', { collapsed: this.state.sidebarCollapsed });
  }

  toggleMobileSidebar() {
    if (!this.state.isMobile) return;
    this.state.sidebarMobileVisible = !this.state.sidebarMobileVisible;
    if (this.state.sidebarMobileVisible) this.openMobileSidebar();
    else this.closeMobileSidebar();
  }

  openMobileSidebar() {
    this.elements.sidebar.classList.add(this.cssClasses.sidebarMobileVisible);
    this.elements.mobileBackdrop?.classList.add(this.cssClasses.backdropShow);
    document.body.style.overflow = 'hidden';
    this.state.sidebarMobileVisible = true;
    this.fireEvent('pandora:mobileSidebarOpened');
  }

  closeMobileSidebar() {
    this.elements.sidebar.classList.remove(this.cssClasses.sidebarMobileVisible);
    this.elements.mobileBackdrop?.classList.remove(this.cssClasses.backdropShow);
    document.body.style.overflow = '';
    this.state.sidebarMobileVisible = false;
    this.fireEvent('pandora:mobileSidebarClosed');
  }

  setupSubmenus() {
    const sidebarNav = this.elements.sidebar?.querySelector('.sidebar-nav');
    if (!sidebarNav) return;

    this.addEventListener(sidebarNav, 'click', (e) => {
      // Atualizado para trabalhar com o novo sistema de templates
      const link = e.target.closest('.nav-link[data-bs-toggle="collapse"]');
      if (!link) return;

      e.preventDefault();

      const parentLi = link.closest('.nav-item');
      const targetId = link.getAttribute('data-bs-target')?.substring(1); // Remove o #
      const submenu = targetId ? document.getElementById(targetId) : parentLi?.querySelector('.nav-submenu');

      if (!submenu) return;

      const collapseInstance = bootstrap.Collapse.getOrCreateInstance(submenu, {
        toggle: false,
        parent: '.nav-list' // Garante que apenas um submenu fique aberto por vez
      });

      // Fechar outros submenus abertos (accordion behavior)
      const openSubmenus = sidebarNav.querySelectorAll('.nav-submenu.show');
      openSubmenus.forEach(openSubmenu => {
        if (openSubmenu !== submenu) {
          const otherCollapse = bootstrap.Collapse.getInstance(openSubmenu);
          if (otherCollapse) otherCollapse.hide();
        }
      });

      collapseInstance.toggle();

      // Atualizar estado do ícone da seta
      const arrow = link.querySelector('.nav-arrow');
      if (arrow) {
        submenu.addEventListener('show.bs.collapse', () => {
          arrow.style.transform = 'rotate(180deg)';
        }, { once: true });

        submenu.addEventListener('hide.bs.collapse', () => {
          arrow.style.transform = 'rotate(0deg)';
        }, { once: true });
      }
    });

    sidebarNav.querySelectorAll('.nav-submenu').forEach(submenu => {
      this.addEventListener(submenu, 'show.bs.collapse', (e) => {
        const parentLi = e.target.closest('.nav-item');
        parentLi?.querySelector('.nav-link[data-bs-toggle="collapse"]')?.setAttribute('aria-expanded', 'true');
        parentLi?.classList.add('active');
      });
      this.addEventListener(submenu, 'hide.bs.collapse', (e) => {
        const parentLi = e.target.closest('.nav-item');
        parentLi?.querySelector('.nav-link[data-bs-toggle="collapse"]')?.setAttribute('aria-expanded', 'false');
        parentLi?.classList.remove('active');
      });
    });
  }

  toggleSubmenu(submenu, toggle) {
    this.log('Legacy toggleSubmenu called. Note: This method is deprecated.');
    const isOpen = submenu.classList.contains(this.cssClasses.submenuShow);

    const allSubmenus = toggle.closest('.sidebar-nav').querySelectorAll('.nav-submenu.show');
    allSubmenus.forEach(openSubmenu => {
      if (openSubmenu !== submenu) {
        openSubmenu.classList.remove(this.cssClasses.submenuShow);
        const otherToggle = openSubmenu.previousElementSibling;
        if (otherToggle) {
          otherToggle.setAttribute('aria-expanded', 'false');
          otherToggle.classList.add('collapsed');
        }
      }
    });

    submenu.classList.toggle(this.cssClasses.submenuShow, !isOpen);
    toggle.setAttribute('aria-expanded', String(!isOpen));
    toggle.classList.toggle('collapsed', isOpen);

    this.state.activeSubmenu = isOpen ? null : submenu;

    this.fireEvent('pandora:submenuToggled', { submenu, isOpen: !isOpen });
  }

  setupSwipeGestures() {
    if (!this.state.isMobile) return;
    let touchStartX = 0;
    this.addEventListener(document, 'touchstart', (e) => { touchStartX = e.changedTouches[0].screenX; }, { passive: true });
    this.addEventListener(document, 'touchend', (e) => {
      const touchEndX = e.changedTouches[0].screenX;
      const swipeThreshold = 50;
      const diff = touchEndX - touchStartX;
      if (Math.abs(diff) > swipeThreshold) {
        if (diff > 0 && touchStartX < 20) this.openMobileSidebar();
        else if (diff < 0 && this.state.sidebarMobileVisible) this.closeMobileSidebar();
      }
    }, { passive: true });
  }

  setupSearch() {
    if (!this.elements.searchInput) return;
    // Clear any prefilled/autofilled value from password managers or cached state
    try { if (this.elements.searchInput.value) this.elements.searchInput.value = ''; } catch (_) { }
    const debouncedSearch = this.debounce(this.performSearch.bind(this), this.config.searchDebounceDelay);
    this.addEventListener(this.elements.searchInput, 'input', debouncedSearch);
    this.addEventListener(this.elements.searchInput, 'focus', () => {
      this.state.searchActive = true;
      try { this.elements.searchInput.removeAttribute('readonly'); } catch (_) { }
      try { if (this.elements.searchInput.value) this.elements.searchInput.select(); } catch (_) { }
      this.elements.searchInput.parentElement.classList.add('focused');
    });
    this.addEventListener(this.elements.searchInput, 'blur', () => {
      setTimeout(() => {
        this.state.searchActive = false;
        this.elements.searchInput.parentElement.classList.remove('focused');
        this.hideSearchResults();
      }, 200);
    });
    this.addEventListener(this.elements.searchInput, 'keydown', (e) => this.handleSearchKeyboard(e));
  }

  async performSearch(e) {
    // Ignore programmatic inputs (e.g., password managers/autofill)
    try { if (e && e.isTrusted === false) return; } catch (_) { }
    const query = e.target.value.trim();
    if (query.length < 2) {
      this.hideSearchResults();
      return;
    }
    try {
      this.showSearchLoading();
      const results = await this.mockSearchAPI(query);
      this.displaySearchResults(results);
    } catch (error) {
      this.logError('Search failed:', error);
      this.showSearchError();
    }
  }

  async mockSearchAPI(query) {
    await new Promise(resolve => setTimeout(resolve, 300));
    const allItems = [
      { type: 'page', title: 'Dashboard', url: '/dashboard/', icon: 'fas fa-tachometer-alt' },
      { type: 'page', title: 'Clientes', url: '/clientes/', icon: 'fas fa-users' },
      { type: 'page', title: 'Produtos', url: '/produtos/', icon: 'fas fa-box' },
      { type: 'action', title: 'Nova Venda', action: 'newSale', icon: 'fas fa-plus' }
    ];
    return allItems.filter(item => item.title.toLowerCase().includes(query.toLowerCase()));
  }

  displaySearchResults(results) {
    if (!this.elements.searchResults) return;
    if (results.length === 0) {
      this.elements.searchResults.innerHTML = `<div class="search-no-results"><i class="fas fa-search"></i><p>Nenhum resultado encontrado</p></div>`;
    } else {
      this.elements.searchResults.innerHTML = results.map((result, index) => `
        <div class="search-result-item" role="option" tabindex="-1" data-index="${index}" data-type="${result.type}" data-action="${result.action || ''}" data-url="${result.url || ''}">
          <div class="search-result-icon"><i class="${result.icon}"></i></div>
          <div class="search-result-content">
            <div class="search-result-title">${result.title}</div>
            <div class="search-result-description">${result.type === 'page' ? 'PÃ¡gina' : 'AÃ§Ã£o'}</div>
          </div>
        </div>`).join('');
      this.elements.searchResults.querySelectorAll('.search-result-item').forEach(item => {
        this.addEventListener(item, 'click', () => this.handleSearchResultClick(item));
      });
    }
    this.elements.searchResults.style.display = 'block';
    this.elements.searchResults.classList.add(this.cssClasses.searchResultsActive);
  }

  handleSearchResultClick(item) {
    const { type, action, url } = item.dataset;
    if (type === 'page' && url) window.location.href = url;
    else if (type === 'action' && action) this.handleQuickAction(action);
    this.hideSearchResults();
    this.elements.searchInput.value = '';
  }

  handleSearchKeyboard(e) {
    const results = this.elements.searchResults?.querySelectorAll('.search-result-item');
    if (!results || results.length === 0) return;
    const currentIndex = Array.from(results).findIndex(r => r.classList.contains('active'));
    let nextIndex;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        nextIndex = currentIndex < results.length - 1 ? currentIndex + 1 : 0;
        this.highlightSearchResult(results, nextIndex);
        break;
      case 'ArrowUp':
        e.preventDefault();
        nextIndex = currentIndex > 0 ? currentIndex - 1 : results.length - 1;
        this.highlightSearchResult(results, nextIndex);
        break;
      case 'Enter':
        e.preventDefault();
        if (currentIndex >= 0) results[currentIndex].click();
        break;
      case 'Escape':
        e.preventDefault();
        this.hideSearchResults();
        this.elements.searchInput.blur();
        break;
    }
  }

  highlightSearchResult(results, index) {
    results.forEach((r, i) => r.classList.toggle('active', i === index));
    results[index]?.focus();
  }

  showSearchLoading() {
    if (!this.elements.searchResults) return;
    this.elements.searchResults.innerHTML = `<div class="search-loading"><div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Carregando...</span></div></div>`;
    this.elements.searchResults.style.display = 'block';
  }

  showSearchError() {
    if (!this.elements.searchResults) return;
    this.elements.searchResults.innerHTML = `<div class="search-error"><i class="fas fa-exclamation-triangle"></i><p>Erro ao buscar. Tente novamente.</p></div>`;
  }

  hideSearchResults() {
    if (!this.elements.searchResults) return;
    this.elements.searchResults.style.display = 'none';
    this.elements.searchResults.classList.remove(this.cssClasses.searchResultsActive);
  }

  setupCalculator() {
    if (!this.elements.calculator) return;
    const toggleBtn = document.querySelector('#calculator-toggle'); // Corrected selector
    if (toggleBtn) this.addEventListener(toggleBtn, 'click', () => this.toggleCalculator());
    const closeBtn = this.elements.calculator.querySelector('.close-calculator');
    if (closeBtn) this.addEventListener(closeBtn, 'click', () => this.hideCalculator());
    const buttons = this.elements.calculator.querySelectorAll('.calc-btn');
    buttons.forEach(btn => this.addEventListener(btn, 'click', (e) => this.handleCalculatorInput(e.currentTarget.dataset)));
    this.addEventListener(document, 'keydown', (e) => {
      if (this.state.calculatorVisible) this.handleCalculatorKeyboard(e);
    });
  }

  toggleCalculator() {
    this.state.calculatorVisible = !this.state.calculatorVisible;
    if (this.state.calculatorVisible) this.showCalculator();
    else this.hideCalculator();
  }

  showCalculator() {
    this.elements.calculator.classList.add(this.cssClasses.calculatorVisible);
    this.state.calculatorVisible = true;
    this.fireEvent('pandora:calculatorOpened');
  }

  hideCalculator() {
    this.elements.calculator.classList.remove(this.cssClasses.calculatorVisible);
    this.state.calculatorVisible = false;
    this.fireEvent('pandora:calculatorClosed');
  }

  safeCalculate(expression) {
    const sanitized = String(expression).replace(/[^0-9+\-*/().]/g, '');
    if (sanitized !== expression) return 'Erro';
    try {
      // Using a safer evaluation method
      return new Function(`return ${sanitized}`)() || '0';
    } catch (error) {
      this.logError('Safe calculation failed', error);
      return 'Erro';
    }
  }

  handleCalculatorInput(dataset) {
    const display = this.elements.calculator.querySelector('.calculator-display');
    if (!display) return;

    const action = dataset.action;
    const number = dataset.number;

    if (action) {
      switch (action) {
        case 'clear':
          display.value = '0';
          break;
        case 'calculate':
          display.value = this.safeCalculate(display.value);
          break;
        case 'delete':
          display.value = display.value.length > 1 ? display.value.slice(0, -1) : '0';
          break;
        case 'decimal':
          if (!display.value.includes('.')) display.value += '.';
          break;
        default: // operators
          if (display.value !== '0' && display.value !== 'Erro') display.value += ` ${action} `;
      }
    } else if (number) {
      if (display.value === '0' || display.value === 'Erro') {
        display.value = number;
      } else {
        display.value += number;
      }
    }
  }

  handleCalculatorKeyboard(e) {
    const validKeys = '0123456789+-*/.()';
    if (validKeys.includes(e.key)) {
      e.preventDefault();
      this.handleCalculatorInput({ number: e.key });
    } else if (e.key === 'Enter' || e.key === '=') {
      e.preventDefault();
      this.handleCalculatorInput({ action: 'calculate' });
    } else if (e.key === 'Escape') {
      e.preventDefault();
      this.hideCalculator();
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      this.handleCalculatorInput({ action: 'delete' });
    }
  }

  setupNotifications() {
    if (!this.elements.toastContainer) {
      this.elements.toastContainer = document.createElement('div');
      this.elements.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
      this.elements.toastContainer.style.zIndex = '1100';
      document.body.appendChild(this.elements.toastContainer);
    }
    this.addEventListener(document, 'pandora:notify', (e) => this.showNotification(e.detail));
  }

  showNotification(options = {}) {
    const { title = 'NotificaÃ§Ã£o', message = '', type = 'info', duration = this.config.toastDuration, action = null } = options;
    const id = `toast-${Date.now()}`;
    const toastHTML = `<div id="${id}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true"><div class="d-flex"><div class="toast-body"><strong>${title}</strong>${message ? `<div class="mt-1">${message}</div>` : ''}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>${action ? `<div class="toast-action p-2"><button type="button" class="btn btn-sm btn-light">${action.label}</button></div>` : ''}</div>`;
    this.elements.toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(id);
    const toast = new bootstrap.Toast(toastElement, { delay: duration });
    if (action?.handler) {
      const actionBtn = toastElement.querySelector('.toast-action button');
      if (actionBtn) this.addEventListener(actionBtn, 'click', action.handler);
    }
    toast.show();
    this.addEventListener(toastElement, 'hidden.bs.toast', () => toastElement.remove());
    this.state.notifications.push({ id, title, message, type, timestamp: new Date() });
    this.fireEvent('pandora:notificationShown', { id, title, message, type });
  }

  setupKeyboardShortcuts() {
    this.addEventListener(document, 'keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); this.elements.searchInput?.focus(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') { e.preventDefault(); this.state.isMobile ? this.toggleMobileSidebar() : this.toggleSidebar(); }
      if ((e.ctrlKey || e.metaKey) && e.key === '.') { e.preventDefault(); this.toggleCalculator(); }
      if (e.altKey && e.key === 't') { e.preventDefault(); this.toggleTheme(); }
    });
  }

  setupResponsive() {
    this.checkResponsive();
    const debouncedResize = this.debounce(() => this.checkResponsive(), 250);
    this.addEventListener(window, 'resize', debouncedResize);
  }

  checkResponsive() {
    const wasMobile = this.state.isMobile;
    this.state.isMobile = window.innerWidth <= this.config.mobileBreakpoint;
    if (wasMobile !== this.state.isMobile) this.handleResponsiveChange();
  }

  handleResponsiveChange() {
    if (this.state.isMobile) {
      this.elements.sidebar?.classList.remove(this.cssClasses.sidebarCollapsed);
      this.closeMobileSidebar();
    } else {
      this.elements.sidebar?.classList.remove(this.cssClasses.sidebarMobileVisible);
      this.elements.mobileBackdrop?.classList.remove(this.cssClasses.backdropShow);
      document.body.style.overflow = '';
      if (this.state.sidebarCollapsed) this.elements.sidebar?.classList.add(this.cssClasses.sidebarCollapsed);
    }
    this.fireEvent('pandora:responsiveChanged', { isMobile: this.state.isMobile });
  }

  setupRealTimeUpdates() {
    const checkUpdates = async () => {
      if (Math.random() > 0.9) {
        this.showNotification({ title: 'AtualizaÃ§Ã£o', message: 'Novos dados disponÃ­veis', type: 'info', action: { label: 'Atualizar', handler: () => window.location.reload() } });
      }
    };
    const intervalId = setInterval(checkUpdates, 30000);
    this.activeTimers.add(intervalId);
  }

  setupPerformanceMonitoring() {
    if (!('PerformanceObserver' in window)) return;
    try {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (entry.duration > 50) this.log(`Long task detected: ${entry.duration}ms`);
        }
      });
      observer.observe({ entryTypes: ['longtask'] });
      this.performance.observers.set('longtask', observer);
    } catch (error) {
      this.logError('Failed to setup performance monitoring:', error);
    }
  }

  hideLoadingOverlay() {
    if (!this.elements.loadingOverlay) return;
    setTimeout(() => {
      this.elements.loadingOverlay.classList.add(this.cssClasses.loadingHidden);
      this.addEventListener(this.elements.loadingOverlay, 'transitionend', () => {
        this.elements.loadingOverlay.style.display = 'none';
      }, { once: true });
    }, 300);
  }

  handleQuickAction(action) {
    const actions = {
      newSale: '/vendas/nova/',
      newClient: '/clientes/novo/'
    };
    if (actions[action]) window.location.href = actions[action];
    else this.log(`Unknown action: ${action}`);
  }

  addEventListener(element, event, handler, options = {}) {
    element.addEventListener(event, handler, options);
    if (!this.eventListeners.has(element)) this.eventListeners.set(element, []);
    this.eventListeners.get(element).push({ event, handler, options });
  }

  fireEvent(eventName, detail = {}) {
    const event = new CustomEvent(eventName, { detail, bubbles: true, cancelable: true });
    document.dispatchEvent(event);
    this.log(`Event fired: ${eventName}`, detail);
  }

  debounce(func, wait) {
    let timeout;
    return (...args) => {
      const later = () => {
        clearTimeout(timeout);
        func.apply(this, args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      this.activeTimers.add(timeout);
    };
  }

  throttle(func, limit) {
    let inThrottle;
    return (...args) => {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        const timeoutId = setTimeout(() => { inThrottle = false; }, limit);
        this.activeTimers.add(timeoutId);
      }
    };
  }

  formatCurrency(value) { return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value); }
  formatDate(date, format = 'short') {
    const options = format === 'short' ? { day: '2-digit', month: '2-digit', year: 'numeric' } : { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' };
    return new Intl.DateTimeFormat('pt-BR', options).format(new Date(date));
  }

  // ===== FORM HELPER METHODS =====
  setupFormHelpers() {
    if (!this.elements.mainForm) return;

    this.log('Setting up form helper functions...');

    // Make helper functions available globally
    window.saveAndContinue = () => {
      const form = this.elements.mainForm;
      if (form) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = '_continue';
        input.value = '1';
        form.appendChild(input);
        form.submit();
      }
    };

    window.saveAndNew = () => {
      const form = this.elements.mainForm;
      if (form) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = '_addanother';
        input.value = '1';
        form.appendChild(input);
        form.submit();
      }
    };

    window.saveAndList = () => {
      const form = this.elements.mainForm;
      if (form) {
        form.submit();
      }
    };

    window.duplicateRecord = () => {
      if (confirm('Deseja criar uma cÃ³pia deste registro?')) {
        const url = window.location.href.replace('/edit/', '/duplicate/').replace('/update/', '/duplicate/');
        window.location.href = url;
      }
    };

    // Setup image upload functionality
    this.setupImagePreview();

    this.log('Form helper functions initialized');
  }

  /**
   * Setup image upload preview functionality
   */
  setupImagePreview() {
    // Add double-click to preview functionality for existing images
    const images = document.querySelectorAll('.image-preview-area img');
    images.forEach(img => {
      this.addEventListener(img, 'dblclick', () => {
        const modal = document.getElementById('imagePreviewModal');
        const modalImg = document.getElementById('imagePreview');
        if (modal && modalImg) {
          modalImg.src = img.src;
          const bsModal = new bootstrap.Modal(modal);
          bsModal.show();
        }
      });
    });
  }

  // ===== FORMSET (DYNAMIC FORMS) METHODS =====
  /**
   * Sets up handlers for Django formsets (add/remove rows).
   */
  setupFormsets() {
    if (!this.elements.mainForm) return;
    this.log('Setting up formsets...');

    // Use event delegation for dynamically added/removed elements
    this.addEventListener(this.elements.mainForm, 'click', (e) => {
      const addBtn = e.target.closest('.add-form-row');
      const removeBtn = e.target.closest('.remove-form-row');

      if (addBtn) {
        e.preventDefault();
        const prefix = addBtn.dataset.formsetPrefix;
        if (prefix) {
          this.addForm(prefix);
        } else {
          this.logError('Add button is missing data-formset-prefix attribute.');
        }
      }

      if (removeBtn) {
        e.preventDefault();
        this.removeForm(removeBtn);
      }
    });

    this.log('Formsets setup complete.');
  }

  /**
   * Adds a new form to a formset.
   * @param {string} prefix - The prefix for the formset.
   */
  addForm(prefix) {
    const formsetContainer = document.getElementById(`${prefix}-formset`);
    const totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const template = document.getElementById(`${prefix}-empty-form-template`);

    if (!formsetContainer || !totalFormsInput || !template) {
      this.logError(`Formset elements for prefix "${prefix}" not found.`);
      return;
    }

    let formCount = parseInt(totalFormsInput.value, 10);

    // Clone the template content
    const newFormHtml = template.innerHTML.replace(/__prefix__/g, formCount);
    const newFormElement = document.createElement('div');
    newFormElement.innerHTML = newFormHtml;

    // The actual form is the first child of the container we created
    const formToAdd = newFormElement.firstElementChild;
    formToAdd.style.display = 'block'; // Make it visible

    // Remove any background color that might be applied
    formToAdd.style.backgroundColor = '';
    formToAdd.style.background = '';

    // Also remove background from all child elements
    const allElements = formToAdd.querySelectorAll('*');
    allElements.forEach(el => {
      if (el.style.backgroundColor && el.style.backgroundColor.includes('#fff3cd')) {
        el.style.backgroundColor = '';
      }
      if (el.style.background && el.style.background.includes('#fff3cd')) {
        el.style.background = '';
      }
    });

    formsetContainer.appendChild(formToAdd);

    // Update the total forms count
    totalFormsInput.value = formCount + 1;

    // Re-initialize any plugins or masks on the new form
    this.setupInputMasks(formToAdd);

    this.fireEvent('formset:added', { prefix, newForm: formToAdd });
    this.log(`Added new form to ${prefix} formset. New count: ${totalFormsInput.value}`);
  }

  /**
   * Removes a form from a formset.
   * @param {HTMLElement} removeBtn - The remove button that was clicked.
   */
  removeForm(removeBtn) {
    const formToRemove = removeBtn.closest('[data-formset-form]');
    if (!formToRemove) {
      this.logError('Could not find parent form to remove.');
      return;
    }

    // For existing forms, Django uses a DELETE checkbox. We just check it and hide the form.
    const deleteInput = formToRemove.querySelector('input[type="checkbox"][id$="-DELETE"]');

    if (deleteInput) {
      deleteInput.checked = true;
      formToRemove.style.display = 'none';
      this.log('Marked existing form for deletion.');
    } else {
      // For new forms that haven't been saved, we can just remove them from the DOM.
      formToRemove.remove();
      this.log('Removed new form from DOM.');
      // Note: We don't decrement TOTAL_FORMS here. Django handles this correctly on the backend
      // as long as the forms are indexed sequentially. Removing from the middle is fine.
    }

    this.fireEvent('formset:removed', { removedForm: formToRemove });
  }


  // ===== FORM NAVIGATION METHODS =====
  // ... (todas as funções de formulário permanecem aqui, sem alterações)
  setupFormNavigation() {
    if (!this.elements.formSections || this.elements.formSections.length === 0) {
      if (this.elements.mainForm) {
        this.log('Single-page form detected. Setting up basic features...');
        this.setupAutoSave();
        this.setupFormValidation();
        this.setupInputMasks();
        this.setupFormsets(); // <-- Adicionar a chamada aqui
      }
      return;
    }
    this.log('Multi-step form detected. Setting up navigation...');
    this.state.totalSections = this.elements.formSections.length;
    this.state.currentSection = 0;
    this.state.sectionValidation = new Array(this.state.totalSections).fill(false);
    this.elements.formSections.forEach((section, index) => {
      section.style.display = index === 0 ? 'block' : 'none';
      section.classList.toggle(this.cssClasses.sectionActive, index === 0);
      section.classList.toggle(this.cssClasses.sectionHidden, index !== 0);
    });
    this.setupStepIndicators();
    this.setupNavigationButtons();
    this.setupAutoSave();
    this.setupFormValidation();
    this.setupInputMasks();
    this.setupFormsets(); // <-- E adicionar a chamada aqui também
    this.updateFormProgress();
    this.updateButtonVisibility();
    this.sanitizeAutoSaveData();
    this.restoreAutoSavedData();
    this.log('Form navigation setup complete');
  }
  setupStepIndicators() {
    if (!this.elements.formSteps) return;
    this.elements.formSteps.forEach((step, index) => {
      this.addEventListener(step, 'click', () => {
        if (index < this.state.currentSection || this.state.sectionValidation[index - 1]) {
          this.goToSection(index);
        }
      });
    });
  }
  setupNavigationButtons() {
    this.elements.nextButtons?.forEach(btn => this.addEventListener(btn, 'click', (e) => { e.preventDefault(); this.nextSection(); }));
    this.elements.prevButtons?.forEach(btn => this.addEventListener(btn, 'click', (e) => { e.preventDefault(); this.previousSection(); }));
    if (this.elements.mainForm) {
      this.addEventListener(this.elements.mainForm, 'keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
          if (e.key === 'ArrowRight') { e.preventDefault(); this.nextSection(); }
          if (e.key === 'ArrowLeft') { e.preventDefault(); this.previousSection(); }
        }
      });
    }
  }
  nextSection() {
    if (this.state.currentSection >= this.state.totalSections - 1) return false;
    if (!this.validateCurrentSection()) {
      this.log('Current section validation failed');
      return false;
    }
    const currentIndex = this.state.currentSection;
    this.goToSection(currentIndex + 1);
    this.state.sectionValidation[currentIndex] = true;
    this.autoSaveForm();
    return true;
  }
  previousSection() {
    if (this.state.currentSection <= 0) return false;
    this.goToSection(this.state.currentSection - 1);
    return true;
  }
  goToSection(targetIndex) {
    if (targetIndex < 0 || targetIndex >= this.state.totalSections || targetIndex === this.state.currentSection) return false;
    if (targetIndex > this.state.currentSection) {
      for (let i = this.state.currentSection; i < targetIndex; i++) {
        if (!this.validateSection(i)) {
          this.log(`Cannot skip to section ${targetIndex}, section ${i} is invalid`);
          return false;
        }
      }
    }
    const currentIndex = this.state.currentSection;
    const direction = targetIndex > currentIndex ? 'next' : 'previous';
    const animationClass = direction === 'next' ? this.cssClasses.slideInRight : this.cssClasses.slideInLeft;
    const currentSectionEl = this.elements.formSections[currentIndex];
    const targetSectionEl = this.elements.formSections[targetIndex];
    if (currentSectionEl) {
      currentSectionEl.style.display = 'none';
      currentSectionEl.classList.remove(this.cssClasses.sectionActive);
    }
    if (targetSectionEl) {
      targetSectionEl.style.display = 'block';
      targetSectionEl.classList.add(this.cssClasses.sectionActive, animationClass);
      setTimeout(() => targetSectionEl.classList.remove(animationClass), this.config.animationDuration);
    }
    this.state.currentSection = targetIndex;
    this.updateFormProgress();
    this.updateStepIndicators();
    this.fireEvent('form:sectionChanged', { from: currentIndex, to: targetIndex, direction });
    return true;
  }
  updateFormProgress() {
    if (!this.elements.formProgress) return;
    const progressPercentage = this.state.totalSections > 0 ? ((this.state.currentSection + 1) / this.state.totalSections) * 100 : 0;
    const progressBar = this.elements.formProgress.querySelector('.progress-bar');
    if (progressBar) {
      progressBar.style.width = `${progressPercentage}%`;
      progressBar.setAttribute('aria-valuenow', progressPercentage);
    }
  }
  updateStepIndicators() {
    if (!this.elements.formSteps) return;
    this.elements.formSteps.forEach((step, index) => {
      step.classList.remove(this.cssClasses.sectionActive, this.cssClasses.sectionCompleted);
      if (index === this.state.currentSection) step.classList.add(this.cssClasses.sectionActive);
      else if (index < this.state.currentSection || this.state.sectionValidation[index]) step.classList.add(this.cssClasses.sectionCompleted);
    });
    this.updateButtonVisibility();
  }
  updateButtonVisibility() {
    if (!this.elements.mainForm) return;
    const total = this.state.totalSections;
    if (!total || total <= 0) return;
    const isFirst = this.state.currentSection === 0;
    const isLast = this.state.currentSection === total - 1;
    const isSingle = total <= 1;
    this.elements.prevButtons?.forEach(btn => btn.style.display = isSingle || isFirst ? 'none' : 'inline-flex');
    this.elements.nextButtons?.forEach(btn => btn.style.display = isSingle || isLast ? 'none' : 'inline-flex');
    this.elements.mainForm.querySelectorAll('.btn-save-main, #submit-btn').forEach(btn => {
      btn.style.display = isLast || isSingle ? 'inline-flex' : 'none';
    });
  }
  validateCurrentSection() { return this.validateSection(this.state.currentSection); }
  validateSection(sectionIndex) {
    if (sectionIndex < 0 || sectionIndex >= this.state.totalSections) return false;
    const section = this.elements.formSections[sectionIndex];
    if (!section) return false;
    const requiredFields = section.querySelectorAll('[required], .required');
    let isValid = true;
    requiredFields.forEach(field => { if (!this.validateField(field)) isValid = false; });
    this.state.sectionValidation[sectionIndex] = isValid;
    this.fireEvent('form:sectionValidated', { sectionIndex, isValid });
    return isValid;
  }
  validateField(field) {
    if (!field || (field.closest && field.closest('.d-none'))) return true;
    let isValid = true;

    // ✅ CORREÇÃO: Verificar se field.value existe e é string antes de usar trim()
    let value = '';
    if (field.value !== undefined && field.value !== null) {
      if (typeof field.value === 'string') {
        value = field.value.trim();
      } else {
        // Para campos como checkboxes, selects, etc.
        value = String(field.value || '').trim();
      }
    }

    // Verificar se é um campo especial de FormSet que não precisa de validação
    if (field.name && (field.name.includes('-DELETE') || field.name.includes('-id') || field.type === 'hidden')) {
      return true;
    }

    if (field.hasAttribute('required') || field.classList.contains('required')) {
      if (!value) isValid = false;
    }
    if (value) {
      const type = field.type;
      const mask = field.dataset.mask;
      if (type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) isValid = false;
      if ((mask === 'cpf' || field.classList.contains('cpf-mask')) && !this.validateCPF(value)) isValid = false;
      if ((mask === 'cnpj' || field.classList.contains('cnpj-mask')) && !this.validateCNPJ(value)) isValid = false;
    }
    field.classList.toggle('is-valid', isValid);
    field.classList.toggle('is-invalid', !isValid);
    return isValid;
  }
  setupFormValidation() {
    if (!this.elements.mainForm) return;
    this.addEventListener(this.elements.mainForm, 'input', (e) => {
      if (e.target.matches('input, select, textarea')) {
        this.validateField(e.target);
        this.state.formDirty = true;
      }
    });
    this.addEventListener(this.elements.mainForm, 'blur', (e) => {
      if (e.target.matches('input, select, textarea')) this.validateField(e.target);
    }, true);
  }
  setupAutoSave() {
    if (!this.elements.mainForm) return;
    const handler = () => {
      this.state.formDirty = true;
      this.scheduleAutoSave();
    };
    this.addEventListener(this.elements.mainForm, 'input', handler);
    this.addEventListener(this.elements.mainForm, 'change', handler);
  }
  scheduleAutoSave() {
    if (this.state.autoSaveTimeout) clearTimeout(this.state.autoSaveTimeout);
    this.state.autoSaveTimeout = setTimeout(() => this.autoSaveForm(), this.config.autoSaveInterval);
    this.activeTimers.add(this.state.autoSaveTimeout);
  }
  async autoSaveForm() {
    if (!this.state.formDirty || !this.elements.mainForm) return;
    this.showAutoSaveIndicator();
    const formData = new FormData(this.elements.mainForm);
    const data = {};

    // Filtrar campos de arquivo e senha para não incluir no auto-save
    for (const [key, value] of formData.entries()) {
      const field = this.elements.mainForm.querySelector(`[name="${key}"]`);
      if (field && field.type !== 'file' && field.type !== 'password') {
        data[key] = value;
      }
    }

    this.state.formData = { ...this.state.formData, ...data };
    localStorage.setItem('pandora_form_autosave', JSON.stringify(this.state.formData));
    this.state.formDirty = false;
    this.log('Form auto-saved successfully');
    setTimeout(() => this.hideAutoSaveIndicator(), 2000);
  }
  showAutoSaveIndicator() { if (this.elements.autoSaveIndicator) this.elements.autoSaveIndicator.classList.add(this.cssClasses.autoSaveVisible); }
  hideAutoSaveIndicator() { if (this.elements.autoSaveIndicator) this.elements.autoSaveIndicator.classList.remove(this.cssClasses.autoSaveVisible); }
  restoreAutoSavedData() {
    try {
      const saved = localStorage.getItem('pandora_form_autosave');
      if (!saved || !this.elements.mainForm) return;
      const data = JSON.parse(saved);
      Object.entries(data).forEach(([name, value]) => {
        const field = this.elements.mainForm.querySelector(`[name="${name}"]`);
        if (field && field.type !== 'file' && field.type !== 'password') {
          field.value = value;
        }
      });
      this.log('Auto-saved data restored');
    } catch (error) { this.logError('Failed to restore auto-saved data:', error); }
  }
  clearAutoSavedData() {
    localStorage.removeItem('pandora_form_autosave');
    this.state.formData = {};
    this.log('Auto-saved data cleared');
  }
  sanitizeAutoSaveData() {
    try {
      const saved = localStorage.getItem('pandora_form_autosave');
      if (!saved) return;

      // Tentar parse para verificar se os dados são válidos
      const data = JSON.parse(saved);

      // Se chegou aqui, os dados são válidos JSON
      this.log('Auto-save data is valid');
    } catch (error) {
      // Se deu erro no parse, limpar dados corrompidos
      this.logError('Auto-save data corrupted, clearing:', error);
      this.clearAutoSavedData();
    }
  }
  setupInputMasks() {
    if (!this.elements.mainForm) return;
    const masks = {
      cpf: this.maskCPF,
      cnpj: this.maskCNPJ,
      phone: this.maskPhone,
      cep: this.maskCEP,
      currency: this.maskCurrency
    };
    this.elements.mainForm.querySelectorAll('input[data-mask]').forEach(input => {
      const maskName = input.dataset.mask;
      if (masks[maskName]) {
        this.addEventListener(input, 'input', (e) => {
          e.target.value = masks[maskName].call(this, e.target.value);
        });
      }
    });
  }
  maskCPF(v) { return v.replace(/\D/g, '').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2'); }
  maskCNPJ(v) { return v.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1/$2').replace(/(\d{4})(\d{1,2})$/, '$1-$2'); }
  maskPhone(v) { const n = v.replace(/\D/g, ''); return n.length > 10 ? n.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3') : n.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3'); }
  maskCEP(v) { return v.replace(/\D/g, '').replace(/(\d{5})(\d{3})/, '$1-$2'); }
  maskCurrency(v) {
    let value = v.replace(/\D/g, '');
    if (value === '') return '';
    value = (parseInt(value, 10) / 100).toFixed(2) + '';
    value = value.replace(".", ",");
    value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
    return 'R$ ' + value;
  }
  validateCPF(cpf) {
    const n = cpf.replace(/\D/g, '');
    if (n.length !== 11 || /^(\d)\1+$/.test(n)) return false;
    let add = 0;
    for (let i = 0; i < 9; i++) add += parseInt(n.charAt(i)) * (10 - i);
    let rev = 11 - (add % 11);
    if (rev === 10 || rev === 11) rev = 0;
    if (rev !== parseInt(n.charAt(9))) return false;
    add = 0;
    for (let i = 0; i < 10; i++) add += parseInt(n.charAt(i)) * (11 - i);
    rev = 11 - (add % 11);
    if (rev === 10 || rev === 11) rev = 0;
    return rev === parseInt(n.charAt(10));
  }
  validateCNPJ(cnpj) {
    const n = cnpj.replace(/\D/g, '');
    if (n.length !== 14 || /^(\d)\1+$/.test(n)) return false;
    let size = n.length - 2;
    let numbers = n.substring(0, size);
    const digits = n.substring(size);
    let sum = 0;
    let pos = size - 7;
    for (let i = size; i >= 1; i--) {
      sum += numbers.charAt(size - i) * pos--;
      if (pos < 2) pos = 9;
    }
    let result = sum % 11 < 2 ? 0 : 11 - sum % 11;
    if (result != digits.charAt(0)) return false;
    size = size + 1;
    numbers = n.substring(0, size);
    sum = 0;
    pos = size - 7;
    for (let i = size; i >= 1; i--) {
      sum += numbers.charAt(size - i) * pos--;
      if (pos < 2) pos = 9;
    }
    result = sum % 11 < 2 ? 0 : 11 - sum % 11;
    return result == digits.charAt(1);
  }

  // ===== DASHBOARD ENGINE METHODS =====

  /**
   * Sets up dashboard widgets and grid system
   */
  setupDashboardWidgets() {
    this.log('Setting up dashboard widgets...');

    try {
      // Cache dashboard-specific elements
      this.elements.dashboardGrid = document.getElementById('dashboard-grid');
      this.elements.customizeToggle = document.querySelector('.customize-toggle');
      this.elements.customizationSidebar = document.querySelector('.customization-sidebar');

      // Initialize only if we have dashboard elements
      if (!this.elements.dashboardGrid) {
        this.log('No dashboard grid found, skipping dashboard setup');
        return;
      }

      // Initialize dashboard engine safely
      if (typeof DashboardEngine !== 'undefined') {
        this.dashboardEngine = new DashboardEngine();
        window.dashboardEngine = this.dashboardEngine;
        this.log('Dashboard engine created successfully');
      } else {
        this.logError('DashboardEngine class not found');
      }

      this.log('Dashboard widgets setup complete');
    } catch (error) {
      this.logError('Failed to setup dashboard widgets:', error);
    }
  }

  /**
   * Initializes the dashboard engine when on dashboard pages
   */
  initializeDashboard() {
    if (typeof DashboardEngine === 'undefined') {
      console.warn('[Pandora] DashboardEngine not available');
      return;
    }

    if (!window.dashboardEngine) {
      window.dashboardEngine = new DashboardEngine();
      console.log('[Pandora] Dashboard engine initialized');
    }
  }

  /**
   * Get dashboard data for Alpine.js binding
   */
  getDashboardData() {
    return {
      showCustomization: false,
      theme: localStorage.getItem('dashboard-theme') || 'blue',
      autoRefreshInterval: parseInt(localStorage.getItem('dashboard-refresh') || '0'),
      availableWidgets: [
        { id: 'metrics', name: 'MÃ©tricas', visible: true },
        { id: 'chart', name: 'GrÃ¡fico Principal', visible: true },
        { id: 'actions', name: 'AÃ§Ãµes RÃ¡pidas', visible: true },
        { id: 'list', name: 'Lista Recente', visible: true }
      ],

      toggleCustomization() {
        this.showCustomization = !this.showCustomization;
      },

      setTheme(theme) {
        this.theme = theme;
        localStorage.setItem('dashboard-theme', theme);
        document.body.style.setProperty('--dashboard-gradient-start', `var(--theme-${theme}-start)`);
        console.log(`Tema do dashboard alterado para: ${theme}`);
      },

      toggleWidget(widgetId) {
        const widget = this.availableWidgets.find(w => w.id === widgetId);
        if (widget && window.dashboardEngine) {
          window.dashboardEngine.toggleWidgetVisibility(widgetId, widget.visible);
        }
      },

      applyLayout(layout) {
        if (window.dashboardEngine) {
          window.dashboardEngine.applyLayout(layout);
        }
      },

      setAutoRefresh() {
        localStorage.setItem('dashboard-refresh', this.autoRefreshInterval);
        if (window.dashboardEngine) {
          window.dashboardEngine.setAutoRefresh(this.autoRefreshInterval);
        }
      }
    };
  }

  // ===== LIST VIEW METHODS =====

  /**
   * Setup list view functionality
   */
  setupListView() {
    this.log('Setting up list view...');
    this.initializeBulkActions();
    this.setupViewToggle();
    this.setupFiltering();
    this.setupInfiniteScroll();
    this.setupListActions();
  }

  /**
   * Initialize bulk action controls
   */
  initializeBulkActions() {
    const selectAllCheckbox = document.getElementById('select-all');
    const itemCheckboxes = document.querySelectorAll('.row-select');
    const bulkActions = document.getElementById('bulk-actions-bar');

    if (selectAllCheckbox && itemCheckboxes.length > 0) {
      this.addEventListener(selectAllCheckbox, 'change', () => {
        itemCheckboxes.forEach(checkbox => {
          checkbox.checked = selectAllCheckbox.checked;
        });
        this.updateBulkActionsVisibility();
      });

      itemCheckboxes.forEach(checkbox => {
        this.addEventListener(checkbox, 'change', () => this.updateBulkActionsVisibility());
      });
    }
  }

  /**
   * Update bulk actions visibility based on selection
   */
  updateBulkActionsVisibility() {
    const selectedItems = document.querySelectorAll('.row-select:checked');
    const bulkActions = document.getElementById('bulk-actions-bar');
    const selectedCount = document.querySelector('.selected-count');

    if (bulkActions) {
      const count = selectedItems.length;
      bulkActions.style.display = count > 0 ? 'block' : 'none';

      if (selectedCount) {
        selectedCount.textContent = count + ' itens selecionados';
      }

      // Update select all checkbox state
      const selectAllCheckbox = document.getElementById('select-all');
      const totalCheckboxes = document.querySelectorAll('.row-select');

      if (selectAllCheckbox && totalCheckboxes.length > 0) {
        selectAllCheckbox.checked = count === totalCheckboxes.length;
        selectAllCheckbox.indeterminate = count > 0 && count < totalCheckboxes.length;
      }
    }
  }

  /**
   * Setup view toggle functionality
   */
  setupViewToggle() {
    const viewButtons = document.querySelectorAll('[data-view]');

    viewButtons.forEach(button => {
      this.addEventListener(button, 'click', () => {
        const view = button.dataset.view;

        // Update active button
        viewButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // Hide all view contents
        document.querySelectorAll('.view-content').forEach(viewContent => {
          viewContent.style.display = 'none';
        });

        // Show selected view
        const selectedView = document.getElementById(view + '-view');
        if (selectedView) {
          selectedView.style.display = 'block';
        }

        // Store preference
        localStorage.setItem('pandora_list_view', view);
      });
    });

    // Restore saved view
    const savedView = localStorage.getItem('pandora_list_view');
    if (savedView) {
      const savedButton = document.querySelector(`[data-view="${savedView}"]`);
      if (savedButton) savedButton.click();
    }

    // Setup search panel auto-focus
    const searchPanel = document.getElementById('quick-search-panel');
    if (searchPanel) {
      this.addEventListener(searchPanel, 'shown.bs.collapse', function () {
        const searchInput = this.querySelector('input[name="q"]');
        if (searchInput) {
          searchInput.focus();
        }
      });
    }
  }

  /**
   * Setup filtering functionality
   */
  setupFiltering() {
    const filterForm = document.getElementById('filterForm');
    const clearFilters = document.getElementById('clearFilters');

    if (filterForm) {
      const inputs = filterForm.querySelectorAll('input, select');
      inputs.forEach(input => {
        this.addEventListener(input, 'change', () => {
          clearTimeout(this.filterTimeout);
          this.filterTimeout = setTimeout(() => {
            filterForm.submit();
          }, 300);
        });
      });
    }

    if (clearFilters) {
      this.addEventListener(clearFilters, 'click', () => {
        if (filterForm) {
          filterForm.reset();
          filterForm.submit();
        }
      });
    }
  }

  /**
   * Setup infinite scroll functionality
   */
  setupInfiniteScroll() {
    const loadMoreBtn = document.getElementById('loadMore');
    if (loadMoreBtn) {
      this.addEventListener(loadMoreBtn, 'click', () => this.loadMoreItems());
    }
  }

  /**
   * Load more items functionality
   */
  loadMoreItems() {
    // Implementation for loading more items via AJAX
    this.log('Load more items functionality');
  }

  /**
   * Setup list action handlers
   */
  setupListActions() {
    // Setup delete confirmation
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
      this.addEventListener(button, 'click', (e) => {
        e.preventDefault();
        const href = button.href;
        const itemName = button.dataset.itemName || 'este item';
        this.confirmDelete(e, href, itemName);
      });
    });
  }

  /**
   * Confirm delete dialog
   */
  confirmDelete(event, url, itemName) {
    event.preventDefault();

    if (typeof Swal !== 'undefined') {
      Swal.fire({
        title: 'VocÃª tem certeza?',
        text: `Deseja realmente excluir "${itemName}"? Esta aÃ§Ã£o nÃ£o pode ser desfeita.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sim, excluir!',
        cancelButtonText: 'Cancelar',
        reverseButtons: true
      }).then((result) => {
        if (result.isConfirmed) {
          window.location.href = url;
        }
      });
    } else {
      // Fallback to native confirm
      if (confirm(`Deseja realmente excluir "${itemName}"? Esta aÃ§Ã£o nÃ£o pode ser desfeita.`)) {
        window.location.href = url;
      }
    }
  }

  // ===== END VIEW-SPECIFIC SETUP METHODS =====

  /**
   * Cleanup application state, timers, and event listeners
   */
  cleanup() {
    this.log('Cleaning up application...');
    this.activeTimers.forEach(timer => { clearTimeout(timer); clearInterval(timer); });
    this.activeTimers.clear();
    this.eventListeners.forEach((listeners, element) => {
      listeners.forEach(({ event, handler, options }) => element.removeEventListener(event, handler, options));
    });
    this.eventListeners.clear();
    this.state.realTimeConnection?.close();
    this.performance.observers.forEach(observer => observer.disconnect());
    this.performance.observers.clear();
    this.log('Application cleaned up');
  }

  log(message, ...args) { if (this.config.debug) console.log(`[Pandora] ${message}`, ...args); }
  logError(message, error) {
    console.error(`[Pandora] ${message}`, error);
    if (window.Sentry) window.Sentry.captureException(error);
  }
}

/**
 * Dashboard Engine Class - Complete grid-based dashboard system
 */
class DashboardEngine {
  constructor() {
    this.grid = null;
    this.charts = {};
    this.autoRefreshTimer = null;
    this.editMode = false;
    this.initialized = false;

    // Aguardar um pequeno delay para garantir que todos os scripts tenham carregado
    setTimeout(() => this.init(), 100);
  }

  init() {
    try {
      // Check if we're on a dashboard page
      const dashboardGrid = document.getElementById('dashboard-grid');
      if (!dashboardGrid) {
        console.log('[DashboardEngine] No dashboard grid found, skipping initialization');
        return;
      }

      // Check if GridStack is available
      if (typeof GridStack === 'undefined') {
        console.warn('[DashboardEngine] GridStack not loaded, dashboard features disabled');
        return;
      }

      this.grid = GridStack.init({
        cellHeight: 70,
        verticalMargin: 20,
        horizontalMargin: 20,
        resizable: { handles: 'se, sw' },
        draggable: { handle: '.widget-header' }
      });

      this.loadLayout();
      this.initializeCharts();

      const refreshInterval = localStorage.getItem('dashboard-refresh');
      if (refreshInterval && refreshInterval !== '0') {
        this.setAutoRefresh(parseInt(refreshInterval));
      }

      this.setupEventListeners();
      this.initialized = true;
      console.log('[DashboardEngine] Successfully initialized');

    } catch (error) {
      console.error('[DashboardEngine] Initialization failed:', error);
    }
  }

  initializeCharts() {
    try {
      if (typeof Chart === 'undefined') {
        console.warn('[DashboardEngine] Chart.js not loaded, chart features disabled');
        return;
      }

      const chartCtx = document.getElementById('mainChart');
      if (chartCtx) {
        // Verificar se o contexto 2D está disponível
        const ctx = chartCtx.getContext('2d');
        if (!ctx) {
          console.warn('[DashboardEngine] Canvas context not available');
          return;
        }

        this.charts.main = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: window.tenantGrowthLabels || ['Jan', 'Fev', 'Mar', 'Abr', 'Mai'],
            datasets: [{
              label: 'Dados',
              data: window.tenantGrowthData || [12, 19, 3, 5, 2],
              backgroundColor: 'rgba(255, 255, 255, 0.8)',
              borderColor: 'rgba(255, 255, 255, 1)',
              borderWidth: 2,
              borderRadius: 8,
              barThickness: 'flex'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: { beginAtZero: true, grid: { color: 'rgba(255, 255, 255, 0.2)' }, ticks: { color: '#fff' } },
              x: { grid: { display: false }, ticks: { color: '#fff' } }
            }
          }
        });

        console.log('[DashboardEngine] Main chart initialized successfully');
      }

      // Inicializar gráfico de status se existir
      const statusChartCtx = document.getElementById('statusChart');
      if (statusChartCtx) {
        const ctx = statusChartCtx.getContext('2d');
        if (ctx) {
          this.charts.status = new Chart(ctx, {
            type: 'doughnut',
            data: {
              labels: window.tenantStatusLabels || ['Ativos', 'Inativos', 'Suspensos'],
              datasets: [{
                data: window.tenantStatusData || [80, 15, 5],
                backgroundColor: ['#28a745', '#ffc107', '#dc3545']
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom',
                  labels: { color: '#fff' }
                }
              }
            }
          });

          console.log('[DashboardEngine] Status chart initialized successfully');
        }
      }

    } catch (error) {
      console.error('[DashboardEngine] Chart initialization failed:', error);
    }
  }

  setupEventListeners() {
    if (!this.grid) return;

    this.grid.on('change', (event, items) => {
      console.log('Layout alterado, salvando...');
      this.saveLayout();
    });

    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case 's': e.preventDefault(); this.saveLayout(); break;
          case 'e': e.preventDefault(); this.toggleEditMode(); break;
        }
      }
    });
  }

  saveLayout() {
    if (!this.grid) return;
    const layout = this.grid.save();
    localStorage.setItem('dashboard-layout', JSON.stringify(layout));
    this.showToast('Layout salvo com sucesso!', 'success');
  }

  loadLayout() {
    if (!this.grid) return;
    const saved = localStorage.getItem('dashboard-layout');
    if (saved) {
      try {
        this.grid.load(JSON.parse(saved));
      } catch (e) {
        console.warn('Erro ao carregar layout salvo:', e);
      }
    }
  }

  resetLayout() {
    localStorage.removeItem('dashboard-layout');
    location.reload();
  }

  toggleEditMode() {
    if (!this.grid) return;
    this.editMode = !this.editMode;
    if (this.editMode) this.grid.enable();
    else this.grid.disable();

    document.querySelector('.dashboard-container')?.classList.toggle('edit-mode', this.editMode);
    this.showToast(this.editMode ? 'Modo de ediÃ§Ã£o ativado' : 'Modo de ediÃ§Ã£o desativado', 'info');
  }

  refreshWidget(widgetId) {
    const widget = document.querySelector(`.grid-stack-item[gs-id="${widgetId}"]`);
    if (widget) {
      widget.classList.add('animate-pulse');
      setTimeout(() => {
        widget.classList.remove('animate-pulse');
        this.showToast(`Widget ${widgetId} atualizado`, 'success');
      }, 1000);
    }
  }

  toggleWidgetVisibility(widgetId, isVisible) {
    if (!this.grid) return;
    const el = document.querySelector(`.grid-stack-item[gs-id="${widgetId}"]`);
    if (!el) return;
    if (isVisible) {
      this.grid.makeWidget(el);
    } else {
      this.grid.removeWidget(el, false);
    }
  }

  configureWidget(widgetId) {
    this.showToast(`Configurar widget ${widgetId}`, 'info');
  }

  applyLayout(layoutName) {
    this.showToast(`Aplicando layout: ${layoutName}`, 'info');
  }

  changeChartType(widgetId) {
    const chart = this.charts.main;
    if (chart) {
      const types = ['bar', 'line', 'pie', 'radar'];
      chart.config.type = types[(types.indexOf(chart.config.type) + 1) % types.length];
      chart.update();
      this.showToast(`Tipo de grÃ¡fico alterado`, 'info');
    }
  }

  setAutoRefresh(interval) {
    if (this.autoRefreshTimer) clearInterval(this.autoRefreshTimer);
    if (interval > 0) {
      this.autoRefreshTimer = setInterval(() => this.refreshAllWidgets(), interval * 1000);
    }
  }

  refreshAllWidgets() {
    if (!this.grid) return;
    this.grid.engine.nodes.forEach(node => this.refreshWidget(node.id));
  }

  export(format) {
    this.showToast(`Exportando dashboard em ${format.toUpperCase()}`, 'info');
    setTimeout(() => this.showToast('Dashboard exportado com sucesso!', 'success'), 2000);
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }

  showToast(message, type = 'info') {
    if (window.Pandora && window.Pandora.showNotification) {
      window.Pandora.showNotification({
        title: 'Dashboard',
        message: message,
        type: type
      });
    } else {
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }
}

// Make dashboardData available globally for Alpine.js
window.dashboardData = function () {
  try {
    if (window.Pandora && typeof window.Pandora.getDashboardData === 'function') {
      return window.Pandora.getDashboardData();
    }
  } catch (error) {
    console.error('[dashboardData] Error calling Pandora.getDashboardData:', error);
  }

  // Fallback if Pandora not available or has errors
  return {
    showCustomization: false,
    theme: localStorage.getItem('dashboard-theme') || 'blue',
    autoRefreshInterval: parseInt(localStorage.getItem('dashboard-refresh') || '0'),
    availableWidgets: [
      { id: 'metrics', name: 'Métricas', visible: true },
      { id: 'chart', name: 'Gráfico Principal', visible: true },
      { id: 'actions', name: 'Ações Rápidas', visible: true },
      { id: 'list', name: 'Lista Recente', visible: true }
    ],

    toggleCustomization() {
      this.showCustomization = !this.showCustomization;
    },

    setTheme(theme) {
      this.theme = theme;
      localStorage.setItem('dashboard-theme', theme);
      if (document.body) {
        document.body.style.setProperty('--dashboard-gradient-start', `var(--theme-${theme}-start)`);
      }
      console.log(`Tema do dashboard alterado para: ${theme}`);
    },

    toggleWidget(widgetId) {
      const widget = this.availableWidgets.find(w => w.id === widgetId);
      if (widget && window.dashboardEngine && window.dashboardEngine.initialized) {
        window.dashboardEngine.toggleWidgetVisibility(widgetId, widget.visible);
      }
    },

    applyLayout(layout) {
      if (window.dashboardEngine && window.dashboardEngine.initialized) {
        window.dashboardEngine.applyLayout(layout);
      }
    },

    setAutoRefresh() {
      localStorage.setItem('dashboard-refresh', this.autoRefreshInterval);
      if (window.dashboardEngine && window.dashboardEngine.initialized) {
        window.dashboardEngine.setAutoRefresh(this.autoRefreshInterval);
      }
    }
  };
};

// Global utility functions for templates
window.toggleView = function (view) {
  if (window.Pandora && window.Pandora.updateBulkActions) {
    const button = document.querySelector(`[data-view="${view}"]`);
    if (button) button.click();
  }
};

window.confirmDelete = function (id, name) {
  const modal = document.getElementById('deleteModal');
  if (modal) {
    const nameSpan = modal.querySelector('#deleteItemName');
    const form = modal.querySelector('form');
    if (nameSpan) nameSpan.textContent = name;
    if (form) form.action = form.action.replace(/\/\d+\/$/, `/${id}/`);
    const bootstrapModal = new bootstrap.Modal(modal);
    bootstrapModal.show();
  }
};

window.exportData = function (format = 'xlsx') {
  const params = new URLSearchParams(window.location.search);
  params.set('export', format);
  window.location.href = `${window.location.pathname}?${params.toString()}`;
};

window.changePageSize = function (size) {
  const params = new URLSearchParams(window.location.search);
  params.set('page_size', size);
  params.delete('page');
  window.location.href = `${window.location.pathname}?${params.toString()}`;
};

window.useTemplate = function (templateId) {
  window.location.href = `/formularios-dinamicos/form/create/?template=${templateId}`;
};

window.duplicateForm = function (formId) {
  if (confirm('Tem certeza que deseja duplicar este formulÃ¡rio?')) {
    window.location.href = `/formularios-dinamicos/form/${formId}/duplicate/`;
  }
};

// Image upload preview function
window.previewImage = function (input, fieldName) {
  if (input.files && input.files[0]) {
    const file = input.files[0];

    // Validate file type
    if (!file.type.match('image.*')) {
      alert('Por favor, selecione apenas arquivos de imagem.');
      input.value = '';
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      alert('O arquivo deve ter no mÃ¡ximo 5MB.');
      input.value = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = function (e) {
      const previewArea = input.closest('.image-upload-container').querySelector('.image-preview-area');
      const placeholder = document.getElementById('placeholder-' + fieldName);

      if (previewArea) {
        // Hide placeholder
        if (placeholder) {
          placeholder.style.display = 'none';
        }

        // Create or update image element
        let img = previewArea.querySelector('img');
        if (!img) {
          img = document.createElement('img');
          img.id = 'preview-' + fieldName;
          img.alt = file.name;
          previewArea.appendChild(img);
        }

        img.src = e.target.result;
        img.style.display = 'block';
      }
    };
    reader.readAsDataURL(file);
  }
};

// Initialize when DOM is ready
// Initialize Pandora Ultra Modern instance
window.Pandora = new PandoraUltraModern();
