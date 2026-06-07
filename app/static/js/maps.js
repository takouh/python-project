// Google Maps API integration for listing location display.

function initMap() {
  const mapContainer = document.getElementById('property-map');
  if (!mapContainer) {
    return;
  }

  const address = mapContainer.dataset.address;
  const city = mapContainer.dataset.city;
  const title = mapContainer.dataset.title || 'Property location';
  const fullAddress = `${address}, ${city}`;

  const geocoder = new google.maps.Geocoder();
  const map = new google.maps.Map(mapContainer, {
    zoom: 15,
    center: { lat: 0, lng: 0 },
    mapTypeId: 'roadmap',
    streetViewControl: false,
    mapTypeControl: false,
  });

  geocoder.geocode({ address: fullAddress }, (results, status) => {
    if (status === 'OK' && results[0]) {
      map.setCenter(results[0].geometry.location);
      new google.maps.Marker({
        map,
        position: results[0].geometry.location,
        title,
      });

      new google.maps.InfoWindow({
        content: `<strong>${title}</strong><div>${results[0].formatted_address}</div>`,
      }).open(map);
    } else {
      mapContainer.innerHTML = '<p class="map-error">Unable to display the map for this address.</p>';
      console.error('Geocode failed:', status);
    }
  });
}
