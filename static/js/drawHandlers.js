let drawnItems;
let drawHandler;

export function initDrawHandlers(appContext) {
    drawnItems = new L.FeatureGroup();
    appContext.mapInstance.addLayer(drawnItems);
    appContext.drawnItems = drawnItems;
}

export function toggleDrawControls(appContext, isDrawing) {
    if (isDrawing && !appContext.drawControlVisible) {
        const drawControls = new L.Control.Draw({
            position: 'topright',
            draw: { /* configurações... */ }
        });
        appContext.mapInstance.addControl(drawControls);
        appContext.drawControlVisible = true;
    } else if (!isDrawing && appContext.drawControlVisible) {
        appContext.mapInstance.removeControl(appContext.mapDrawControls);
        appContext.drawControlVisible = false;
    }
}

export function activateDrawing(appContext) {
    if (!drawHandler) {
        drawHandler = new L.Draw.Polygon(appContext.mapInstance, {
            /* configurações... */
        });
    }
    drawHandler.enable();
    appContext.currentDrawing = null;
}