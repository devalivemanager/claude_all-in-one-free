// CLI 를 별도 프로세스로 실행해 종료 코드와 안내 문구를 확인한다
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { startFixtureServer } from "./helpers/fixture-server.mjs";

const CLI = fileURLToPath(new URL("../src/cli.mjs", import.meta.url));
const execFileAsync = promisify(execFile);

/** CLI 를 실행하고 { code, stdout, stderr } 를 돌려준다 */
async function runCli(args) {
  try {
    const { stdout, stderr } = await execFileAsync(process.execPath, [CLI, ...args]);
    return { code: 0, stdout, stderr };
  } catch (err) {
    return { code: err.code, stdout: err.stdout, stderr: err.stderr };
  }
}

describe("CLI", () => {
  it("--help 는 사용법을 보여 준다", async () => {
    const r = await runCli(["--help"]);
    assert.equal(r.code, 0);
    assert.match(r.stdout, /사용법: node src\/cli\.mjs <URL>/);
  });

  it("URL 이 없으면 종료 코드 1", async () => {
    const r = await runCli([]);
    assert.equal(r.code, 1);
    assert.match(r.stderr, /URL 을 하나 입력하세요/);
  });

  it("robots.txt 로 금지된 경로는 종료 코드 2", async () => {
    const fixture = await startFixtureServer();
    try {
      const r = await runCli([`${fixture.url}private/`]);
      assert.equal(r.code, 2);
      assert.match(r.stderr, /robots\.txt 가 이 경로의 수집을 허용하지 않아/);
    } finally {
      await fixture.close();
    }
  });
});
