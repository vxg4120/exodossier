import { describe, expect, it } from "vitest";
import { visitorMessage } from "../components/States";

/** The raw error strings come from api/client.ts (fetchJson) and the browser; a visitor reads a
    sentence, and the raw line stays in the title for whoever debugs. */
describe("visitorMessage", () => {
  it("translates the browser's network failures", () => {
    expect(visitorMessage("Failed to fetch")).toMatch(/did not answer/);
    expect(visitorMessage("Load failed")).toMatch(/did not answer/);
  });
  it("names the timeout the client enforces", () => {
    expect(visitorMessage("No answer from the API within 30s for /stats")).toMatch(/too long/);
  });
  it("maps the status line the client throws", () => {
    expect(visitorMessage("404 Not Found for /target/x")).toMatch(/Nothing in the catalog/);
    expect(visitorMessage("502 Bad Gateway for /stats")).toMatch(/on its side/);
    expect(visitorMessage("422 Unprocessable Content for /twoskies/passes")).toBe(
      "The API turned the request down (status 422).",
    );
  });
  it("passes the API's own detail text through on a 4xx that has one", () => {
    expect(visitorMessage("422 unknown site 'mars'; presets: kitt_peak for /twoskies/passes")).toBe(
      "The API turned the request down: unknown site 'mars'; presets: kitt_peak",
    );
  });
  it("explains a body that is not JSON instead of quoting the parser", () => {
    expect(visitorMessage("Not JSON from the API for /twoskies/targets")).toMatch(/not data/);
    expect(visitorMessage("Unexpected token '<', \"<!doctype \"... is not valid JSON")).toMatch(/not data/);
  });
  it("leaves an unknown message alone", () => {
    expect(visitorMessage("something else entirely")).toBe("something else entirely");
  });
});
