// 환경변수에서 설정을 읽는다. API 키는 절대 코드나 파일에 직접 쓰지 않는다.
export const DEFAULT_MODEL = 'claude-opus-5-5';

export function getModel(env: NodeJS.ProcessEnv = process.env): string {
  const model = env.ANTHROPIC_MODEL?.trim();
  return model ? model : DEFAULT_MODEL;
}

export function hasApiKey(env: NodeJS.ProcessEnv = process.env): boolean {
  return Boolean(env.ANTHROPIC_API_KEY?.trim());
}
