# 사용: . ./kx.sh 후  kx '<C# 코드>'  — Unity MCP execute_code 결과(result)만 출력
# 예: kx 'return UnityEngine.Time.frameCount.ToString();'
KX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
kx(){
  PYTHONIOENCODING=utf-8 python "$KX_DIR/umcp.py" execute_code \
    "$(python -c "import json,sys;print(json.dumps({'action':'execute','code':sys.argv[1]}))" "$1")" \
  | PYTHONIOENCODING=utf-8 python -c "import json,sys;d=json.load(sys.stdin);print(d.get('data',{}).get('result') if d.get('success') else d)"
}
