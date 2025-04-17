export async function fetchMapData(appContext) {
    if (!appContext.selectedCoords) {
        appContext.errorMessage = "Selecione um local primeiro!";
        return;
    }

    appContext.isProcessingMap = true;
    try {
        const response = await fetch(
            `/get_map?latitude=${appContext.selectedCoords.lat}&longitude=${appContext.selectedCoords.lng}` +
            `&data=${appContext.mapParams.dateStart},${appContext.mapParams.dateEnd}` +
            `&filter=CLOUDY_PIXEL_PERCENTAGE,${appContext.mapParams.cloudFilter}`
        );

        if (response.ok) {
            const blob = await response.blob();
            appContext.mapUrl = URL.createObjectURL(blob);
        }
    } catch (error) {
        console.error("API Error:", error);
    } finally {
        appContext.isProcessingMap = false;
    }
}