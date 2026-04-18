"""Generate self-contained xena-datasets-catalog.html with DataTables CDN."""
import sys
sys.path.insert(0, "src")

from ucscxenatoolspy.core.xena_data import load_xena_data
from pathlib import Path

df = load_xena_data()
cols = ["XenaHostNames", "XenaCohorts", "XenaDatasets", "DataSubtype", "SampleCount", "ProbeMap", "Tags", "Label"]
df = df[cols]
df = df.fillna("")

# Build JS array as JSON
data_json = df.to_json(orient="split", force_ascii=False)

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Xena Dataset Catalog</title>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.7/css/jquery.dataTables.min.css">
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background: #f8f9fa; }
  .container { max-width: 1400px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  h1 { font-size: 1.5rem; margin-bottom: 4px; color: #1a1a1a; }
  .subtitle { color: #666; font-size: .9rem; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th { background: #f1f5f9; font-weight: 600; position: sticky; top: 0; white-space: nowrap; padding: 8px 6px; text-align: left; }
  td { padding: 6px; border-top: 1px solid #eee; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td:hover { white-space: normal; word-break: break-word; }
  #catalogBody tr:hover { background: #f0f7ff; }
</style>
</head>
<body>
<div class="container">
<h1>Xena Dataset Catalog</h1>
<p class="subtitle">Loading...</p>
<table id="catalog">
  <thead>
    <tr>""" + "".join(
    f'\n      <th>{c}</th>' for c in cols
) + """
    </tr>
  </thead>
  <tbody id="catalogBody"></tbody>
</table>
</div>
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<script src="https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js"></script>
<script>
const DATA = """ + data_json + """;
(function() {
  var rows = DATA.data;
  var tbody = document.getElementById("catalogBody");
  rows.forEach(function(row) {
    var tr = document.createElement("tr");
    DATA.columns.forEach(function(h, idx) {
      var td = document.createElement("td");
      td.textContent = row[idx] !== null && row[idx] !== undefined ? row[idx] : "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });

  $("#catalog").DataTable({
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    order: [[0, "asc"]],
    language: { search: "Filter:" }
  });

  var hubs = new Set(rows.map(function(r) { return r[0]; }));
  document.querySelector(".subtitle").textContent = rows.length + " datasets from " + hubs.size + " hubs";
})();
</script>
</body>
</html>
"""

out = Path("docs/xena-datasets-catalog.html")
out.write_text(html, encoding="utf-8")
total = len(df)
nbytes = len(out.read_bytes())
print(f"Written to {out} ({total} rows, {nbytes:,} bytes)")
