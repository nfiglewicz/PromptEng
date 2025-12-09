// Simple global namespace for testability
window.TransportApp = (function () {
  const state = {
    mode: "start", // or "end"
    startMarker: null,
    endMarker: null,
    resultMarkers: [],
    routeLayer: null,
    map: null,
  };

  function initMap() {
    const map = L.map("map").setView([51.1079, 17.0385], 13); // central Wrocław
    state.map = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    map.on("click", onMapClick);
  }

  function onMapClick(e) {
    const { lat, lng } = e.latlng;
    const coordString = lat.toFixed(6) + "," + lng.toFixed(6);

    if (state.mode === "start") {
      if (state.startMarker) {
        state.map.removeLayer(state.startMarker);
      }
      state.startMarker = L.marker([lat, lng], { draggable: false }).addTo(state.map);
      document.getElementById("startInput").value = coordString;
    } else {
      if (state.endMarker) {
        state.map.removeLayer(state.endMarker);
      }
      state.endMarker = L.marker([lat, lng], { draggable: false, color: "red" }).addTo(state.map);
      document.getElementById("endInput").value = coordString;
    }
  }

  function setMode(mode) {
    state.mode = mode;
    const btnStart = document.getElementById("btnStartMode");
    const btnEnd = document.getElementById("btnEndMode");
    if (mode === "start") {
      btnStart.classList.add("active");
      btnEnd.classList.remove("active");
    } else {
      btnEnd.classList.add("active");
      btnStart.classList.remove("active");
    }
  }

  function buildClosestDeparturesUrl(params) {
    const city = "Wroclaw";
    const qs = new URLSearchParams(params);
    return `/public_transport/city/${city}/closest_departures?` + qs.toString();
  }

  function clearResults() {
    document.getElementById("resultsList").innerHTML = "";
    document.getElementById("resultsHint").style.display = "block";
    hideError();
    state.resultMarkers.forEach((m) => state.map.removeLayer(m));
    state.resultMarkers = [];
    if (state.routeLayer) {
      state.map.removeLayer(state.routeLayer);
      state.routeLayer = null;
    }
  }

  function showError(msg) {
    const el = document.getElementById("errorBox");
    el.textContent = msg;
    el.style.display = "block";
  }

  function hideError() {
    const el = document.getElementById("errorBox");
    el.style.display = "none";
  }

  function getIsoFromDatetimeLocal(value) {
    if (!value) {
      return null;
    }
    // value like "2025-04-02T08:30"
    return value + ":00Z";
  }

  function groupDeparturesByStop(departures) {
    const groups = {};
    departures.forEach((d) => {
      const stopName = d.stop.name;
      if (!groups[stopName]) {
        groups[stopName] = [];
      }
      groups[stopName].push(d);
    });
    return groups;
  }

  function renderResults(departures) {
    const resultsList = document.getElementById("resultsList");
    const hint = document.getElementById("resultsHint");
    resultsList.innerHTML = "";
    hint.style.display = departures.length === 0 ? "block" : "none";

    departures.forEach((d) => {
      const div = document.createElement("div");
      div.className = "result-item";

      const main = document.createElement("div");
      main.className = "result-main";

      const line = document.createElement("div");
      line.className = "result-line";
      line.innerHTML =
        `<span class="chip">${d.route_id}</span>` +
        `${d.trip_headsign}`;

      const stop = document.createElement("div");
      stop.className = "result-stop";
      stop.textContent = d.stop.name;

      main.appendChild(line);
      main.appendChild(stop);

      const time = document.createElement("div");
      time.className = "result-time";
      const depTime = new Date(d.stop.departure_time).toISOString().substring(11, 16);
      time.textContent = depTime;

      div.appendChild(main);
      div.appendChild(time);
      resultsList.appendChild(div);
    });
  }

  function addMarkersForDepartures(departures) {
    state.resultMarkers.forEach((m) => state.map.removeLayer(m));
    state.resultMarkers = [];

    const groups = groupDeparturesByStop(departures);

    Object.keys(groups).forEach((stopName) => {
      const group = groups[stopName];
      const first = group[0];
      const lat = first.stop.coordinates.latitude;
      const lon = first.stop.coordinates.longitude;

      let html = `<div class="popup-stop-name">${stopName}</div>`;
      group.forEach((d) => {
        const depTime = d.stop.departure_time.substring(11, 16);
        html += `<div class="popup-line"><span class="chip">${d.route_id}</span> ${d.trip_headsign} <span class="time">${depTime}</span> <span class="popup-link" data-trip="${d.trip_id}">Show route</span></div>`;
      });

      const marker = L.marker([lat, lon]).addTo(state.map);
      marker.bindPopup(html);
      marker.on("popupopen", function (e) {
        const popupEl = e.popup.getElement();
        if (!popupEl) return;
        popupEl.querySelectorAll(".popup-link").forEach((el) => {
          el.addEventListener("click", function () {
            const tripId = this.getAttribute("data-trip");
            if (tripId) {
              fetchTripRoute(tripId);
            }
          });
        });
      });

      state.resultMarkers.push(marker);
    });
  }

  async function fetchClosestDepartures() {
    hideError();

    const startInput = document.getElementById("startInput").value.trim();
    const endInput = document.getElementById("endInput").value.trim();
    const timeInput = document.getElementById("timeInput").value;
    const limitInput = document.getElementById("limitInput").value || "5";
    const radiusInput = document.getElementById("radiusInput").value;

    if (!startInput || !endInput) {
      showError("Please select both start and destination on the map.");
      return;
    }

    const iso = getIsoFromDatetimeLocal(timeInput);
    const params = {
      start_coordinates: startInput,
      end_coordinates: endInput,
      limit: limitInput,
      radius_m: radiusInput,
    };
    if (iso) {
      params.start_time = iso;
    }

    const url = buildClosestDeparturesUrl(params);

    try {
      const res = await fetch(url);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "API error");
      }
      const data = await res.json();
      const departures = data.departures || [];
      renderResults(departures);
      addMarkersForDepartures(departures);
    } catch (e) {
      console.error(e);
      showError("Failed to fetch departures. Is the backend running on the same host/port?");
    }
  }

  async function fetchTripRoute(tripId) {
    if (!tripId) return;
    const city = "Wroclaw";
    const url = `/public_transport/city/${city}/trip/${encodeURIComponent(tripId)}`;

    try {
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(await res.text());
      }
      const data = await res.json();
      const stops = (data.trip_details && data.trip_details.stops) || [];

      if (state.routeLayer) {
        state.map.removeLayer(state.routeLayer);
        state.routeLayer = null;
      }

      const latlngs = stops.map((s) => [s.coordinates.latitude, s.coordinates.longitude]);
      state.routeLayer = L.polyline(latlngs, { weight: 4 }).addTo(state.map);
      if (latlngs.length > 0) {
        state.map.fitBounds(state.routeLayer.getBounds(), { padding: [40, 40] });
      }
    } catch (e) {
      console.error(e);
      showError("Failed to fetch trip details.");
    }
  }

  function initControls() {
    document.getElementById("btnStartMode").addEventListener("click", () => setMode("start"));
    document.getElementById("btnEndMode").addEventListener("click", () => setMode("end"));
    document.getElementById("btnSearch").addEventListener("click", fetchClosestDepartures);
    document.getElementById("btnClear").addEventListener("click", clearResults);

    // Default departure time = now (browser local)
    const now = new Date();
    now.setSeconds(0, 0);
    const local = now.toISOString().slice(0, 16);
    document.getElementById("timeInput").value = local;
  }

  function init() {
    initMap();
    initControls();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Public API exposed for tests
  return {
    buildClosestDeparturesUrl,
    groupDeparturesByStop,
    getIsoFromDatetimeLocal,
  };
})();
