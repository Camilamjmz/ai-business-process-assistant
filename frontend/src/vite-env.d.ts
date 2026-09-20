/// <reference types="vite/client" />

declare module "plotly.js-basic-dist-min" {
  const Plotly: typeof import("plotly.js");
  export default Plotly;
}
