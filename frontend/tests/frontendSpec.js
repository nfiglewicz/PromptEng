describe("TransportApp helpers", function () {
  it("buildClosestDeparturesUrl builds query string correctly", function () {
    const url = window.TransportApp.buildClosestDeparturesUrl({
      start_coordinates: "51.1,17.0",
      end_coordinates: "51.2,17.1",
      limit: 3,
    });
    expect(url).toContain("/public_transport/city/Wroclaw/closest_departures?");
    expect(url).toContain("start_coordinates=51.1%2C17.0");
    expect(url).toContain("end_coordinates=51.2%2C17.1");
    expect(url).toContain("limit=3");
  });

  it("groupDeparturesByStop groups by stop name", function () {
    const deps = [
      { stop: { name: "A" } },
      { stop: { name: "A" } },
      { stop: { name: "B" } },
    ];
    const grouped = window.TransportApp.groupDeparturesByStop(deps);
    expect(Object.keys(grouped)).toEqual(["A", "B"]);
    expect(grouped["A"].length).toBe(2);
    expect(grouped["B"].length).toBe(1);
  });

  it("getIsoFromDatetimeLocal converts correctly", function () {
    const iso = window.TransportApp.getIsoFromDatetimeLocal("2025-04-02T08:30");
    expect(iso).toBe("2025-04-02T08:30:00Z");
  });
});
