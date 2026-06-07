const searchInput = document.querySelector('#home-search');
const listingCards = document.querySelectorAll('.listing-card');

const filterListings = (query) => {
  const normalized = query.trim().toLowerCase();

  listingCards.forEach((card) => {
    const listingText = card.dataset.listing.toLowerCase();
    if (!normalized || listingText.includes(normalized)) {
      card.style.display = 'grid';
    } else {
      card.style.display = 'none';
    }
  });
};

if (searchInput) {
  searchInput.addEventListener('input', (event) => {
    filterListings(event.target.value);
  });
}

window.addEventListener('load', () => {
  if (searchInput && searchInput.value) {
    filterListings(searchInput.value);
  }
});
