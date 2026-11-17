/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { graphView } from "@web/views/graph/graph_view";
import { pivotView } from "@web/views/pivot/pivot_view";
import { listView } from "@web/views/list/list_view";
import { useRef, useState } from "@odoo/owl";

// Limit the button to this module's views, without patching other applications.
for (const [type, view] of Object.entries({ graph: graphView, pivot: pivotView, list: listView })) {
    class QualityPDFController extends view.Controller {
        setup() {
            super.setup();
            this.pdfORM = useService("orm");
            this.pdfAction = useService("action");
            this.pdfNotification = useService("notification");
            this.pdfRoot = useRef("root");
            this.pdfState = useState({ downloading: false, graphOnly: false });
        }

        async downloadQualityPDF(graphOnly = false) {
            if (this.pdfState.downloading) {
                return;
            }
            this.pdfState.downloading = true;
            this.pdfState.graphOnly = graphOnly;
            try {
                const canvas = this.pdfRoot.el?.querySelector(".o_graph_renderer canvas");
                const graphImage = canvas ? canvas.toDataURL("image/png") : false;
                if (graphOnly && !graphImage) {
                    this.pdfNotification.add("Abre la vista de gráfico para descargarlo en PDF.", { type: "warning" });
                    return;
                }
                const action = await this.pdfORM.call(
                    "techstore.quality.test", "action_download_quality_pdf", [], {
                        domain: this.props.domain,
                        graph_image: graphImage,
                        graph_only: graphOnly,
                        context: this.props.context,
                    }
                );
                await this.pdfAction.doAction(action);
            } finally {
                this.pdfState.downloading = false;
            }
        }
    }

    registry.category("views").add(`techstore_quality_pdf_${type}`, {
        ...view,
        Controller: QualityPDFController,
        buttonTemplate: `practicaUnidad4.QualityPDF.${type}`,
    });
}
