import "bootstrap/dist/css/bootstrap.css";
import "/AIPscan/static/css/custom.css";
import "typesense";
import TypesenseHelpers from "/AIPscan/static/js/typesense.js";

import $ from "jquery";
window.$ = $;
window.jQuery = $;

import bootstrap from "bootstrap";
window.bootstrap = bootstrap;

import Chart from "chart.js/auto";
window.Chart = Chart;
window.Typesense = Typesense;
window.TypesenseHelpers = TypesenseHelpers;
