import { describe, expect, it, vi } from "vitest";

const getDb = vi.hoisted(() => vi.fn());
vi.mock("../db", () => ({ getDb }));

import { syncDatabaseMetadata } from "./service";

describe("数据库元数据受控同步", () => {
  it("持久化版本、元数据摘要和同步时间", async () => {
    const set = vi.fn();
    const where = vi.fn().mockResolvedValue(undefined);
    set.mockReturnValue({ where });
    getDb.mockResolvedValue({ update: () => ({ set }) });
    const metadata = { objectCount: 42, tableCount: 18, schemaCount: 3 };
    const result = await syncDatabaseMetadata({ instanceId: 9, version: "8.0.36", metadata });
    expect(result.instanceId).toBe(9);
    expect(result.metadata).toEqual(metadata);
    expect(result.syncedAt).toBeInstanceOf(Date);
    expect(set).toHaveBeenCalledWith(expect.objectContaining({ version: "8.0.36", metadata, metadataSyncedAt: expect.any(Date) }));
  });
});
