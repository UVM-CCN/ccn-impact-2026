const map = L.map("map").setView([39.5, -108], 3);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
	maxZoom: 20,
	attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
}).addTo(map);

const sidebar = document.getElementById("sidebar");
const sidebarContent = document.getElementById("sidebar-content");
const closeBtn = document.getElementById("sidebar-close");

const infoBtn = document.getElementById("info-btn");
const infoTooltip = document.getElementById("info-tooltip");

infoBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  const open = infoBtn.getAttribute("aria-expanded") === "true";
  infoBtn.setAttribute("aria-expanded", String(!open));
  infoTooltip.hidden = open;
});

document.addEventListener("click", () => {
  infoBtn.setAttribute("aria-expanded", "false");
  infoTooltip.hidden = true;
});

const GREEN_STATUSES = new Set(["Continuing"]);

function napColor(status) {
  return GREEN_STATUSES.has(status) ? "green" : "yellow";
}

function markerIcon(color) {
  return L.divIcon({
    className: "",
    html: `<div class="map-marker" style="background:${color}"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
    tooltipAnchor: [0, -7],
  });
}

function openSidebar(university, programs) {
  const programsHtml = programs.map((p) => {
    const name = p["Program Name"] || "Unnamed Program";
    const faculty = p["Lead Faculty Name"] || "—";
    const structure = p["Structure"] || "";
    const status = p["NAP Status"]?.trim() || "";
    const pillColor = napColor(status);

    return `
      <div class="program-card">
        <div class="program-name">
          ${escHtml(name)}
          ${status ? `<span class="nap-pill nap-pill--${pillColor}">${escHtml(status)}</span>` : ""}
        </div>
        <div class="program-meta">Lead Faculty: <span>${escHtml(faculty)}</span></div>
        ${structure ? `<div class="program-structure">${escHtml(structure)}</div>` : ""}
      </div>`;
  }).join("");

  const countLabel = programs.length === 1 ? "1 program" : `${programs.length} programs`;

  sidebarContent.innerHTML = `
    <div class="sidebar-university">${escHtml(university)}</div>
    <div class="program-count">${countLabel}</div>
    ${programsHtml}
  `;

  sidebar.classList.add("open");
  sidebar.setAttribute("aria-hidden", "false");
}

function closeSidebar() {
  sidebar.classList.remove("open");
  sidebar.setAttribute("aria-hidden", "true");
}

closeBtn.addEventListener("click", closeSidebar);

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

Papa.parse("data/ccn-survey-20260501-geocoded.csv", {
  header: true,
  download: true,
  skipEmptyLines: true,
  complete({ data }) {
    const HIDE_FROM_MAP_STATUSES = new Set(["Ended", "Paused"]);

    // remove rows if "NAP Status" is "Ended" or "Paused"
    data = data.filter(row => {
      const status = row["NAP Status"]?.trim();
      return !HIDE_FROM_MAP_STATUSES.has(status);
    });

    // Group rows by institution name
    const byUniversity = new Map();
    for (const row of data) {
      const name = row["Institution Name"]?.trim();
      const lat = parseFloat(row["LATITUDE"]);
      const lon = parseFloat(row["LONGITUD"]);
      if (!name || isNaN(lat) || isNaN(lon)) continue;

      if (!byUniversity.has(name)) {
        byUniversity.set(name, { lat, lon, programs: [] });
      }
      byUniversity.get(name).programs.push(row);
    }

    // Place one marker per university
    for (const [name, { lat, lon, programs }] of byUniversity) {
      const allGreen = programs.every((p) => GREEN_STATUSES.has(p["NAP Status"]?.trim()));
      const color = allGreen ? "#144734" : "#ffc107";
      const marker = L.marker([lat, lon], { icon: markerIcon(color) }).addTo(map);
      marker.bindTooltip(name, { direction: "top", offset: [0, -7] });
      marker.on("click", () => openSidebar(name, programs));
    }
  },
});
