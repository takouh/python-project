document.addEventListener('DOMContentLoaded', function () {
  const searchInput = document.getElementById('dashboard-search');
  const userItems = Array.from(document.querySelectorAll('#user-list li'));
  const listingItems = Array.from(document.querySelectorAll('#listing-list li'));
  const totalUsers = document.getElementById('kpi-total-users');
  const activeListings = document.getElementById('kpi-active-listings');
  const landlordsCount = document.getElementById('kpi-landlords');
  const tenantsCount = document.getElementById('kpi-tenants');

  function updateSummary() {
    const allUsers = userItems;
    const allListings = listingItems;

    const landlords = allUsers.filter((item) => item.dataset.type === 'landlord').length;
    const tenants = allUsers.filter((item) => item.dataset.type === 'tenant').length;

    totalUsers.textContent = allUsers.length;
    landlordsCount.textContent = landlords;
    tenantsCount.textContent = tenants;
    activeListings.textContent = allListings.filter((item) => item.dataset.status === 'active').length;
  }

  function filterDashboard(value) {
    const query = value.trim().toLowerCase();

    userItems.forEach((item) => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(query) ? 'flex' : 'none';
    });

    listingItems.forEach((item) => {
      const text = item.textContent.toLowerCase();
      item.style.display = text.includes(query) ? 'flex' : 'none';
    });

    updateSummary();
  }

  const actionButtons = Array.from(document.querySelectorAll('.admin-action-buttons .pill'));
  const actionPanels = Array.from(document.querySelectorAll('.admin-action-panels .admin-panel'));

  function setActiveAction(panelName) {
    actionButtons.forEach((button) => {
      const active = button.dataset.adminPanel === panelName;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', active);
    });

    actionPanels.forEach((panel) => {
      panel.style.display = panel.dataset.adminPanel === panelName ? 'block' : 'none';
    });

    updateSummary();
  }

  searchInput.addEventListener('input', (event) => {
    filterDashboard(event.target.value);
  });

  actionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      setActiveAction(button.dataset.adminPanel);
    });
  });

  setActiveAction('publish');
});
