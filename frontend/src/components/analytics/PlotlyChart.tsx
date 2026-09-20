import createPlotlyComponent from "react-plotly.js/factory";
import { Config, Data, Layout } from "plotly.js";
import Plotly from "plotly.js-basic-dist-min";

const Plot = createPlotlyComponent(Plotly);

const baseLayout: Partial<Layout> = {
  autosize: true,
  paper_bgcolor: "#ffffff",
  plot_bgcolor: "#ffffff",
  margin: { l: 52, r: 20, t: 16, b: 44 },
  font: { family: "Inter, ui-sans-serif, system-ui", color: "#475569", size: 12 },
  hoverlabel: { bgcolor: "#0f172a", bordercolor: "#0f172a", font: { color: "#ffffff" } },
};
const config: Partial<Config> = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["lasso2d", "select2d"] };

export function PlotlyChart({ data, layout, height = 300, ariaLabel }: { data: Data[]; layout?: Partial<Layout>; height?: number; ariaLabel: string }) {
  return <div role="img" aria-label={ariaLabel}><Plot data={data} layout={{ ...baseLayout, ...layout, height }} config={config} useResizeHandler className="h-full w-full" style={{ width: "100%", height }} /></div>;
}
