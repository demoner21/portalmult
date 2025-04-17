import { initMapControls } from '/static/js/mapControls.js';

document.addEventListener('alpine:init', () => {
    Alpine.data('appData', () => ({
        // Estado inicial
        currentMode: 'click',
        selectedCoords: null,
        manualCoords: { lat: -17.70894, lng: -40.60899 },
        mapParams: {
            dateStart: '',
            dateEnd: '',
            cloudFilter: 15
        },
        isProcessingMap: false,
        isProcessingImage: false,
        errorMessage: '',
        mapResults: false,
        imageResults: false,
        mapUrl: null,
        response: {},
        sortedKeys: [],
        imgSrc: null,
        imgRGB: null,
        
        // Inicialização
        init() {
            this.setDefaultDates();
            initMapControls(this);
            initDrawHandlers(this);
            
            this.$watch('isDrawing', (value) => {
                toggleDrawControls(this, value);
                if (value) activateDrawing(this);
                else deactivateDrawing(this);
            });
        },

        // Métodos simples podem permanecer aqui
        toggleDrawingMode() {
            this.isDrawing = !this.isDrawing;
            this.currentMode = this.isDrawing ? 'draw' : 'click';
        },

        setDefaultDates() {
            const today = new Date();
            const lastMonth = new Date();
            lastMonth.setMonth(today.getMonth() - 1);
            this.mapParams.dateStart = lastMonth.toISOString().split('T')[0];
            this.mapParams.dateEnd = today.toISOString().split('T')[0];
        }
    }));
});