#!/usr/bin/env node
// CLI 진입점: 인자를 읽고 분석을 실행한 뒤 결과 위치를 알려 준다
import path from "node:path";
import { parseCliArgs, USAGE } from "./args.mjs";
import { analyzeSite, PlaywrightMissingError, RobotsBlockedError } from "./crawler.mjs";

async function main() {
  let options;
  try {
    options = parseCliArgs(process.argv.slice(2));
  } catch (err) {
    console.error(`오류: ${err.message}\n\n${USAGE}`);
    return 1;
  }
  if (options.help) {
    console.log(USAGE);
    return 0;
  }

  const outDir = path.resolve(options.outDir);
  console.log(`분석 시작: ${options.url}`);
  try {
    const report = await analyzeSite({ ...options, outDir, log: (m) => console.log(`  ${m}`) });
    console.log(`\n완료: 페이지 ${report.pages.length}개 분석, ${report.skipped.length}개 건너뜀`);
    console.log(`  보고서: ${path.join(outDir, "report.md")}`);
    console.log(`  데이터: ${path.join(outDir, "report.json")}`);
    console.log(`  스크린샷: ${path.join(outDir, "screenshots")}`);
    return report.pages.length > 0 ? 0 : 1;
  } catch (err) {
    if (err instanceof RobotsBlockedError) {
      console.error(`중단: ${err.message}`);
      return 2;
    }
    if (err instanceof PlaywrightMissingError) {
      console.error(err.message);
      return 3;
    }
    console.error(`오류: ${err.message}`);
    return 1;
  }
}

process.exitCode = await main();
