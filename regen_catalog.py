"""Generate self-contained xena-datasets-catalog.html with vanilla JS pagination."""
import sys
sys.path.insert(0, "src")

from ucscxenatoolspy.core.xena_data import load_xena_data
from pathlib import Path

df = load_xena_data()
cols = ["XenaHostNames", "XenaCohorts", "XenaDatasets", "DataSubtype", "SampleCount", "ProbeMap", "Tags", "Label"]
df = df[cols]
df = df.fillna("")

# Build JS array as JSON
rows_json = df.to_json(orient="split", force_ascii=False)

html_head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Xena Dataset Catalog</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background: #f8f9fa; }
  .container { max-width: 1400px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  h1 { font-size: 1.5rem; margin-bottom: 4px; color: #1a1a1a; }
  .subtitle { color: #666; font-size: .9rem; margin-bottom: 16px; }
  .controls { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .controls input { padding: 6px 10px; font-size: .85rem; border: 1px solid #ccc; border-radius: 4px; min-width: 200px; }
  .controls select, .controls button { padding: 6px 10px; font-size: .85rem; border: 1px solid #ccc; border-radius: 4px; cursor: pointer; }
  .controls button { background: #3b82f6; color: #fff; border: none; }
  .controls button:hover { background: #2563eb; }
  .info { color: #555; font-size: .85rem; margin-left: auto; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #f1f5f9; font-weight: 600; position: sticky; top: 0; white-space: nowrap; padding: 8px 6px; text-align: left; cursor: pointer; user-select: none; }
  th:hover { background: #e2e8f0; }
  th .sort-arrow { margin-left: 4px; font-size: .7rem; }
  td { padding: 6px; border-top: 1px solid #eee; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td:hover { white-space: normal; word-break: break-word; }
  .pagination { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-size: .85rem; }
  .pagination button { padding: 4px 12px; font-size: .85rem; }
  .pagination button:disabled { opacity: .4; cursor: default; }
  #catalogBody tr:hover { background: #f0f7ff; }
</style>
</head>
<body>
<div class="container">
<h1>Xena Dataset Catalog <button onclick="copyTable()">Copy CSV</button></h1>
<p class="subtitle" id="subtitle">Loading...</p>
<div class="controls">
  <input type="text" id="search" placeholder="Search..." oninput="onSearch()">
  <label>Show: <select id="pageSize" onchange="onPageSizeChange()"><option value="10">10</option><option value="25" selected>25</option><option value="50">50</option><option value="100">100</option></select></label>
  <span class="info" id="info"></span>
</div>
<table id="catalog">
  <thead>
    <tr>
      <th data-col="0">XenaHostNames<span class="sort-arrow"></span></th>
      <th data-col="1">XenaCohorts<span class="sort-arrow"></span></th>
      <th data-col="2">XenaDatasets<span class="sort-arrow"></span></th>
      <th data-col="3">DataSubtype<span class="sort-arrow"></span></th>
      <th data-col="4">SampleCount<span class="sort-arrow"></span></th>
      <th data-col="5">ProbeMap<span class="sort-arrow"></span></th>
      <th data-col="6">Tags<span class="sort-arrow"></span></th>
      <th data-col="7">Label<span class="sort-arrow"></span></th>
    </tr>
  </thead>
  <tbody id="catalogBody"></tbody>
</table>
<div class="pagination">
  <button id="prevBtn" onclick="prevPage()">Prev</button>
  <span id="pageInfo"></span>
  <button id="nextBtn" onclick="nextPage()">Next</button>
</div>
</div>

"""

js_data = "const DATA = " + rows_json + ";"

js_code = """
<script>
(function() {
  const headers = DATA.columns;
  const colTypes = {};
  for (let c = 0; c < headers.length; c++) {
    const vals = DATA.data.map(r => r[c]).filter(v => v !== "" && v !== null);
    colTypes[c] = vals.every(v => !isNaN(parseFloat(v)));
  }

  let filtered = DATA.data.slice();
  let sortCol = 0;
  let sortAsc = true;
  let page = 1;
  let pageSize = 25;

  const tbody = document.getElementById("catalogBody");
  const infoEl = document.getElementById("info");
  const pageEl = document.getElementById("pageInfo");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const searchEl = document.getElementById("search");
  const subtitleEl = document.getElementById("subtitle");

  const hubs = new Set(DATA.data.map(r => r[0]));
  subtitleEl.textContent = DATA.data.length + " datasets from " + hubs.size + " hubs \\u00b7 Click column headers to sort \\u00b7 Use search to filter";

  document.querySelectorAll("#catalog thead th").forEach(function(th) {
    th.addEventListener("click", function() {
      var c = parseInt(this.getAttribute("data-col"));
      if (sortCol === c) { sortAsc = !sortAsc; } else { sortCol = c; sortAsc = true; }
      page = 1;
      doSort();
      render();
      updateArrows();
    });
  });

  function doSort() {
    filtered.sort(function(a, b) {
      var va = a[sortCol], vb = b[sortCol];
      if (colTypes[sortCol]) { va = parseFloat(va) || 0; vb = parseFloat(vb) || 0; }
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });
  }

  function updateArrows() {
    document.querySelectorAll("#catalog thead th .sort-arrow").forEach(function(sp, i) {
      sp.textContent = i === sortCol ? (sortAsc ? " \\u25b2" : " \\u25bc") : "";
    });
  }

  window.onSearch = function() {
    var q = searchEl.value.toLowerCase();
    filtered = DATA.data.filter(function(r) { return r.some(function(v) { return String(v).toLowerCase().includes(q); }); });
    if (sortCol >= 0) doSort();
    page = 1;
    render();
  };

  window.onPageSizeChange = function() {
    pageSize = parseInt(document.getElementById("pageSize").value);
    page = 1;
    render();
  };

  window.prevPage = function() { if (page > 1) { page--; render(); } };
  window.nextPage = function() { if (page * pageSize < filtered.length) { page++; render(); } };

  function render() {
    var start = (page - 1) * pageSize;
    var end = Math.min(start + pageSize, filtered.length);
    var slice = filtered.slice(start, end);

    var rows = slice.map(function(r) {
      return "<tr>" + r.map(function(v) { return "<td>" + escapeHtml(String(v)) + "</td>"; }).join("") + "</tr>";
    }).join("");
    tbody.innerHTML = rows;

    var totalPages = Math.ceil(filtered.length / pageSize) || 1;
    pageEl.textContent = "Page " + page + " of " + totalPages;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= totalPages;
    infoEl.textContent = "Showing " + (start + 1) + "\\u2013" + end + " of " + filtered.length + " rows";
  }

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  doSort();
  render();
  updateArrows();

  window.copyTable = function() {
    var NL = String.fromCharCode(10);
    var csv = DATA.columns.join(",") + NL +
      filtered.map(function(r) { return r.map(function(v) { return '"' + String(v).replace(/"/g, '""') + '"'; }).join(","); }).join(NL);
    navigator.clipboard.writeText(csv).then(function() { alert("CSV copied (" + filtered.length + " rows)!"); });
  };
})();
</script>
</body>
</html>
"""

out = Path("docs/xena-datasets-catalog.html")
out.write_text(html_head + js_data + "\n" + js_code, encoding="utf-8")
total = len(df)
nbytes = len(out.read_bytes())
print(f"Written to {out} ({total} rows, {nbytes:,} bytes)")
