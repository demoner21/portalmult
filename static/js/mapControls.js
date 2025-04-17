let mapInstance;
let currentMarker;

export function initMapControls(appContext) {
    mapInstance = L.map('map', {
        attributionControl: false
    }).setView([-17.70894, -40.60899], 12);

    L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        detectRetina: true
    }).addTo(mapInstance);

    // Evento de clique no mapa
    mapInstance.on('click', (e) => {
        if (appContext.currentMode !== 'click') return;
        appContext.selectedCoords = e.latlng;
        updateMarker(appContext);
    });

    appContext.mapInstance = mapInstance;
}

export function updateMarker(appContext) {
    if (currentMarker) {
        mapInstance.removeLayer(currentMarker);
    }
    
    currentMarker = L.marker([appContext.selectedCoords.lat, appContext.selectedCoords.lng])
        .addTo(mapInstance)
        .bindPopup("Local selecionado")
        .openPopup();
}