"""프레임·시트의 공급원. 로컬 절차 생성이 기본이고, 이미지 생성 API 는 갈아 끼울 수 있다.

외부 API 를 붙일 때의 약속(가이드 수칙 1·10 대응):
- API 키는 절대 인자로 받지 않고 환경변수에서만 읽는다.
- 네트워크를 치는 부분은 `client` 함수 하나로 주입해, 시험에서는 가짜를 끼워 실제 호출 없이 검증한다.
- API 가 나가든 절차 생성이든 돌아오는 건 언제나 PIL Image 묶음이라 그 뒤 흐름(속도·용량 조절,
  GIF 조립)은 하나다.
"""

from __future__ import annotations

import base64
import io
import json
import os
from typing import Callable

from PIL import Image

from .converter import slice_sheet
from .generator import generate_frames

# 외부 이미지 생성 API 의 응답을 받아 시트 PNG 바이트로 돌려주는 함수 형태.
# (예: OpenAI 호환 이미지 생성 API. 키는 절대 코드에 넣지 않고 환경변수로만)
ImageApiClient = Callable[[str], bytes]

DEFAULT_API_URL = "https://api.openai.com/v1/images/generations"
DEFAULT_MODEL = "gpt-image-2.6"  # Flare(빠른 초안) / Sunburst(정밀) 계열. 모델명은 실행 시점에 확인


def frames_from_procedural(motion: str, frames: int, spec) -> list[Image.Image]:
    """절차적 생성(기본 공급원). 외부 연결이 전혀 없다."""
    return generate_frames(motion=motion, frames=frames, spec=spec)


def frames_from_sheet_bytes(data: bytes, cols: int, rows: int, trim: int) -> list[Image.Image]:
    """어디서 왔든 시트 PNG 바이트만 있으면 프레임으로 잘라 돌려준다(수동 다운로드 시트 포함)."""
    sheet = Image.open(io.BytesIO(data))
    return slice_sheet(sheet, cols=cols, rows=rows, trim=trim)


def _default_client(api_url: str, model: str, api_key_env: str) -> ImageApiClient:
    """OpenAI 호환 이미지 생성 API 최소 클라이언트. 프롬프트 하나로 시트 PNG 바이트를 받는다."""
    import urllib.request

    def client(prompt: str) -> bytes:
        key = os.environ[api_key_env]
        payload = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "output_format": "png",  # GIF 는 이 도구가 조립한다: 시트 한 장만 받는다
            }
        ).encode()
        request = urllib.request.Request(
            api_url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.load(response)
        # 응답 규격: {"data": [{"b64_json": "..."}]}. PNG 시트를 디코딩해 돌려준다.
        return base64.b64decode(body["data"][0]["b64_json"])

    return client


def frames_from_api(
    prompt: str,
    cols: int,
    rows: int,
    trim: int,
    client: ImageApiClient | None = None,
    api_url: str = DEFAULT_API_URL,
    model: str = DEFAULT_MODEL,
    api_key_env: str = "OPENAI_API_KEY",
) -> list[Image.Image]:
    """이미지 생성 API 로 스프라이트 시트를 뽑아 바로 프레임으로 자른다.

    client 를 주면 그것을 쓴다(시험용·다른 공급자 갈아끼우기). 없으면 OpenAI 호환
    HTTP 호출을 하며, 이때 api_key_env 환경변수가 필요하다(없으면 바로 안내하고 끝낸다).
    프롬프트에는 가이드 부록의 ⌊고정 문구 6조각⌋(격자·순서·카메라 고정·배경 유지·루프·
    글자/테두리 제외)을 반드시 포함한다.
    """
    if client is None:
        if not os.environ.get(api_key_env):
            raise RuntimeError(
                f"이미지 생성 API 키가 없습니다. 환경변수 {api_key_env} 를 넣거나, "
                "API 없이 쓰려면 절차 생성(motion 옵션)을 쓴다."
            )
        client = _default_client(api_url, model, api_key_env)
    data = client(prompt)
    return frames_from_sheet_bytes(data, cols=cols, rows=rows, trim=trim)
