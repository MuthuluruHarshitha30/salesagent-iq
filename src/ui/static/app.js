/**
 * Mini AI BI Assistant Frontend Application
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const queryForm = document.getElementById("queryForm");
  const questionInput = document.getElementById("questionInput");
  const clearBtn = document.getElementById("clearBtn");
  const submitBtn = document.getElementById("submitBtn");
  const btnText = submitBtn.querySelector(".btn-text");
  const spinner = submitBtn.querySelector(".spinner");

  const resultsSection = document.getElementById("resultsSection");
  const errorBanner = document.getElementById("errorBanner");
  const questionEcho = document.getElementById("questionEcho");
  const answerSummary = document.getElementById("answerSummary");
  const intentBadge = document.getElementById("intentBadge");
  const execTime = document.getElementById("execTime");
  const comparisonBox = document.getElementById("comparisonBox");
  const sqlDisplay = document.getElementById("sqlDisplay");
  const copySqlBtn = document.getElementById("copySqlBtn");
  const chartCard = document.getElementById("chartCard");
  const chartTitle = document.getElementById("chartTitle");
  const analyticsCanvas = document.getElementById("analyticsChart");
  const dataTable = document.getElementById("dataTable");
  const tableHead = document.getElementById("tableHead");
  const tableBody = document.getElementById("tableBody");
  const rowCountBadge = document.getElementById("rowCountBadge");

  // Schema Modal Elements
  const schemaBtn = document.getElementById("schemaBtn");
  const schemaModal = document.getElementById("schemaModal");
  const closeModalBtn = document.getElementById("closeModalBtn");

  // Load KPI overview
  fetchSummary();

  // Clear button logic
  clearBtn.addEventListener("click", () => {
    questionInput.value = "";
    questionInput.focus();
  });

  // Prompt chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-q");
      questionInput.value = q;
      submitQuery(q);
    });
  });

  // Form submit
  queryForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (q) {
      submitQuery(q);
    }
  });

  // Copy SQL
  copySqlBtn.addEventListener("click", () => {
    const sql = sqlDisplay.innerText;
    navigator.clipboard.writeText(sql).then(() => {
      copySqlBtn.innerText = "Copied!";
      setTimeout(() => {
        copySqlBtn.innerText = "Copy SQL";
      }, 2000);
    });
  });

  // Modal open/close
  schemaBtn.addEventListener("click", () => {
    schemaModal.style.display = "flex";
  });
  closeModalBtn.addEventListener("click", () => {
    schemaModal.style.display = "none";
  });
  schemaModal.addEventListener("click", (e) => {
    if (e.target === schemaModal) {
      schemaModal.style.display = "none";
    }
  });

  // Fetch KPI Summary
  async function fetchSummary() {
    try {
      const res = await fetch("/api/summary");
      if (!res.ok) return;
      const data = await res.json();
      const overview = data.dataset_overview;
      const topProd = data.top_product;
      const topReg = data.top_region;

      if (overview) {
        document.getElementById("kpiRevenue").innerText = formatCurrency(overview.total_net_revenue);
        document.getElementById("kpiUnits").innerText = formatNumber(overview.total_units);
      }
      if (topProd) {
        document.getElementById("kpiProduct").innerText = topProd.product;
      }
      if (topReg) {
        document.getElementById("kpiRegion").innerText = topReg.region;
      }
    } catch (e) {
      console.warn("Failed to load initial summary:", e);
    }
  }

  // Submit Query to Backend API
  async function submitQuery(question) {
    setLoading(true);
    hideError();
    resultsSection.style.display = "none";

    try {
      const response = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question })
      });

      const json = await response.json();

      if (!response.ok || !json.success) {
        showError(json.error || "An error occurred while executing the query.");
        setLoading(false);
        return;
      }

      renderResults(json.data);
    } catch (err) {
      showError("Connection error: Unable to reach the BI backend API.");
    } finally {
      setLoading(false);
    }
  }

  // Render Result Payload
  function renderResults(data) {
    questionEcho.innerText = data.question;
    answerSummary.innerText = data.summary;
    intentBadge.innerText = data.intent || "QUERY";
    execTime.innerText = `${data.execution_time_ms}ms`;
    sqlDisplay.innerText = data.sql_query;
    rowCountBadge.innerText = `${data.row_count} ${data.row_count === 1 ? "row" : "rows"}`;

    // Comparison details
    if (data.comparative_metrics) {
      renderComparison(data.comparative_metrics);
    } else {
      comparisonBox.style.display = "none";
    }

    // Chart rendering
    if (data.chart_data && data.chart_data.type && data.chart_data.labels) {
      chartCard.style.display = "block";
      chartTitle.innerText = data.chart_data.title || "Data Visualization";
      renderCanvasChart(data.chart_data);
    } else {
      chartCard.style.display = "none";
    }

    // Table rendering
    renderTable(data.columns, data.supporting_data);

    resultsSection.style.display = "block";
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Render Comparative KPI Box
  function renderComparison(comp) {
    comparisonBox.style.display = "grid";
    const deltaClass = comp.absolute_difference >= 0 ? "delta-pos" : "delta-neg";
    const sign = comp.absolute_difference >= 0 ? "+" : "";

    comparisonBox.innerHTML = `
      <div class="comp-item">
        <div class="comp-item-label">${comp.entity1.name}</div>
        <div class="comp-item-val">${formatCurrency(comp.entity1.revenue)}</div>
        <div class="kpi-sub">${comp.entity1.orders || 0} orders &bull; ${comp.entity1.units || 0} units</div>
      </div>
      <div class="comp-item">
        <div class="comp-item-label">${comp.entity2.name}</div>
        <div class="comp-item-val">${formatCurrency(comp.entity2.revenue)}</div>
        <div class="kpi-sub">${comp.entity2.orders || 0} orders &bull; ${comp.entity2.units || 0} units</div>
      </div>
      <div class="comp-item">
        <div class="comp-item-label">Net Variance</div>
        <div class="comp-item-val ${deltaClass}">${sign}${formatCurrency(comp.absolute_difference)}</div>
        <div class="comp-delta ${deltaClass}">${sign}${comp.percentage_change}% (${comp.direction})</div>
      </div>
    `;
  }

  // Render Table
  function renderTable(cols, rows) {
    tableHead.innerHTML = "";
    tableBody.innerHTML = "";

    if (!cols || cols.length === 0 || !rows || rows.length === 0) {
      tableHead.innerHTML = "<tr><th>Result</th></tr>";
      tableBody.innerHTML = "<tr><td>No records returned</td></tr>";
      return;
    }

    // Header
    const trHead = document.createElement("tr");
    cols.forEach((c) => {
      const th = document.createElement("th");
      th.innerText = c.replace(/_/g, " ").toUpperCase();
      trHead.appendChild(th);
    });
    tableHead.appendChild(trHead);

    // Rows
    rows.forEach((r) => {
      const tr = document.createElement("tr");
      cols.forEach((c) => {
        const td = document.createElement("td");
        let val = r[c];
        if (typeof val === "number") {
          if (c.includes("revenue") || c.includes("discount") || c.includes("price") || c.includes("amount")) {
            td.innerText = formatCurrency(val);
          } else {
            td.innerText = formatNumber(val);
          }
        } else {
          td.innerText = val !== null && val !== undefined ? val : "-";
        }
        tr.appendChild(td);
      });
      tableBody.appendChild(tr);
    });
  }

  // High-DPI Native Canvas Chart Renderer (Zero dependencies!)
  function renderCanvasChart(chart) {
    const canvas = analyticsCanvas;
    const ctx = canvas.getContext("2d");

    // High-DPI scaling
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = 260 * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = 260;
    const padding = { top: 30, right: 30, bottom: 50, left: 70 };
    const chartW = w - padding.left - padding.right;
    const chartH = h - padding.top - padding.bottom;

    ctx.clearRect(0, 0, w, h);

    const labels = chart.labels || [];
    const values = (chart.values || []).map((v) => Number(v) || 0);
    const n = labels.length;
    if (n === 0) return;

    const maxVal = Math.max(...values, 100);
    const roundedMax = Math.ceil(maxVal / 1000) * 1000 || maxVal * 1.1;

    // Grid lines & Y-axis labels
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#94a3b8";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "right";

    const gridSteps = 4;
    for (let i = 0; i <= gridSteps; i++) {
      const y = padding.top + chartH - (i / gridSteps) * chartH;
      const stepVal = (i / gridSteps) * roundedMax;

      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      ctx.fillText(formatCompact(stepVal), padding.left - 10, y + 4);
    }

    if (chart.type === "line") {
      // Draw Line Chart
      const points = [];
      const stepX = chartW / Math.max(1, n - 1);

      for (let i = 0; i < n; i++) {
        const x = padding.left + i * stepX;
        const y = padding.top + chartH - (values[i] / roundedMax) * chartH;
        points.push({ x, y, val: values[i], label: labels[i] });
      }

      // Fill gradient under line
      const gradient = ctx.createLinearGradient(0, padding.top, 0, padding.top + chartH);
      gradient.addColorStop(0, "rgba(59, 130, 246, 0.35)");
      gradient.addColorStop(1, "rgba(59, 130, 246, 0.0)");

      ctx.beginPath();
      ctx.moveTo(points[0].x, padding.top + chartH);
      points.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.lineTo(points[points.length - 1].x, padding.top + chartH);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Line stroke
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      points.forEach((p) => ctx.lineTo(p.x, p.y));
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 3;
      ctx.stroke();

      // Dots & Labels
      points.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#38bdf8";
        ctx.fill();
        ctx.strokeStyle = "#0f172a";
        ctx.lineWidth = 2;
        ctx.stroke();

        // X-axis label
        ctx.fillStyle = "#cbd5e1";
        ctx.font = "11px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(p.label, p.x, h - padding.bottom + 20);
      });
    } else {
      // Draw Bar Chart
      const barSlot = chartW / n;
      const barWidth = Math.min(48, barSlot * 0.65);

      for (let i = 0; i < n; i++) {
        const barH = (values[i] / roundedMax) * chartH;
        const x = padding.left + i * barSlot + (barSlot - barWidth) / 2;
        const y = padding.top + chartH - barH;

        // Bar gradient
        const barGrad = ctx.createLinearGradient(0, y, 0, y + barH);
        barGrad.addColorStop(0, "#38bdf8");
        barGrad.addColorStop(1, "#1d4ed8");

        ctx.fillStyle = barGrad;
        ctx.beginPath();
        // Rounded top
        ctx.roundRect ? ctx.roundRect(x, y, barWidth, barH, [4, 4, 0, 0]) : ctx.rect(x, y, barWidth, barH);
        ctx.fill();

        // X-axis label
        ctx.fillStyle = "#cbd5e1";
        ctx.font = "11px Inter, sans-serif";
        ctx.textAlign = "center";
        const shortLabel = labels[i].length > 12 ? labels[i].substring(0, 10) + ".." : labels[i];
        ctx.fillText(shortLabel, x + barWidth / 2, h - padding.bottom + 20);
      }
    }
  }

  // Utility formatters
  function formatCurrency(n) {
    if (n === null || n === undefined) return "$0.00";
    return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatNumber(n) {
    if (n === null || n === undefined) return "0";
    return Number(n).toLocaleString("en-US");
  }

  function formatCompact(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(0) + "k";
    return n.toString();
  }

  function setLoading(isLoading) {
    submitBtn.disabled = isLoading;
    btnText.style.display = isLoading ? "none" : "inline";
    spinner.style.display = isLoading ? "inline-block" : "none";
  }

  function showError(msg) {
    errorBanner.innerText = msg;
    errorBanner.style.display = "block";
  }

  function hideError() {
    errorBanner.style.display = "none";
  }
});
