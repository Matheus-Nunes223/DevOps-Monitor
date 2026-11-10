import { describe, expect, it } from "vitest";
import { codeClass, sumStatusCodes } from "@/lib/status-codes";

describe("sumStatusCodes", () => {
  it("adds samples per code and ignores malformed rows", () => {
    const totals = sumStatusCodes([
      { value: 3, labels: { code: "200" } },
      { value: 2, labels: { code: "200" } },
      { value: 1, labels: { code: "502" } },
      { value: null, labels: { code: "404" } },
      { value: 5, labels: {} },
      { value: 5, labels: null },
    ]);
    expect(totals).toEqual([
      { code: "200", total: 5 },
      { code: "502", total: 1 },
    ]);
  });

  it("classifies codes", () => {
    expect(codeClass("503")).toBe("server");
    expect(codeClass("404")).toBe("client");
    expect(codeClass("302")).toBe("redirect");
    expect(codeClass("200")).toBe("ok");
  });
});
