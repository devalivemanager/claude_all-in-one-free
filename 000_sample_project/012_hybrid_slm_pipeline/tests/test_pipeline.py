import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from pipeline import run_hybrid_pipeline as runner
from pipeline.preprocess import CATEGORIES, build_clean_data, classify, count_keywords, load_texts, mask_pii, summarize
from pipeline.slm_client import OllamaClient, OllamaUnavailable, SLMError
from tests.fake_ollama import FakeOllama

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "samples" / "comments_sample.json"
MODEL = "example-small-model"  # 시험용 가짜 이름(실제 모델이 아니다)


class FakeServerTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeOllama()
        self.client = OllamaClient(base_url=self.fake.url, model=MODEL)

    def tearDown(self):
        self.fake.close()


class ClientTests(FakeServerTest):
    def test_status_ok_when_model_installed_with_tag(self):
        self.assertIn("example-small-model:latest", self.client.check_status())

    def test_no_model_configured_asks_to_choose_one(self):
        # 기본 모델이 없으므로, SLM_MODEL 을 정하지 않으면 서버에 묻기 전에 안내하고 멈춘다
        client = OllamaClient(base_url=self.fake.url, model=None)
        with self.assertRaises(OllamaUnavailable) as ctx:
            client.check_status()
        self.assertIn("SLM_MODEL", str(ctx.exception))

    def test_missing_model_tells_how_to_install(self):
        client = OllamaClient(base_url=self.fake.url, model="other-model")
        with self.assertRaises(OllamaUnavailable) as ctx:
            client.check_status()
        self.assertIn("ollama pull other-model", str(ctx.exception))

    def test_server_down_tells_to_run_ollama_serve(self):
        client = OllamaClient(base_url="http://127.0.0.1:9", model=MODEL, timeout=1)
        with self.assertRaises(OllamaUnavailable) as ctx:
            client.check_status()
        self.assertIn("ollama serve", str(ctx.exception))

    def test_generate_json_sends_json_format_korean_rule_and_zero_temperature(self):
        self.client.generate_json("요약하라")
        body = self.fake.requests[-1]
        self.assertEqual(body["format"], "json")
        self.assertFalse(body["stream"])
        self.assertIn("한국어", body["system"])
        self.assertEqual(body["options"]["temperature"], 0)

    def test_non_json_answer_is_error_not_success(self):
        self.fake.answer = lambda prompt: "죄송합니다. 분류할 수 없습니다."
        with self.assertRaises(SLMError):
            self.client.generate_json("분류하라")

    def test_metrics_are_measured_values_from_ollama(self):
        self.client.generate_json("a")
        self.client.generate_json("b")
        m = self.client.metrics.to_dict()
        self.assertEqual((m["calls"], m["generated_tokens"], m["prompt_tokens"]), (2, 40, 100))
        self.assertEqual(m["measured_tokens_per_second"], 200.0)  # 40 토큰 / 0.2초


class PiiTests(unittest.TestCase):
    def test_masks_url_email_phone_handle(self):
        text = "문의 me@example.com, 010-1234-5678, https://x.co/a 그리고 @friend_kim 봐"
        self.assertEqual(mask_pii(text), "문의 [메일], [전화], [링크] 그리고 [아이디] 봐")

    def test_load_drops_author_field_and_masks_text(self):
        texts = load_texts(SAMPLE)
        joined = "\n".join(texts)
        self.assertEqual(len(texts), 6)
        self.assertNotIn("시청자", joined)
        self.assertNotIn("me@example.com", joined)
        self.assertNotIn("@friend_kim", joined)

    def test_txt_input_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.txt"
            p.write_text("첫 줄\n\n  \n둘째 줄\n", encoding="utf-8")
            self.assertEqual(load_texts(p), ["첫 줄", "둘째 줄"])

    def test_json_item_without_text_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.json"
            p.write_text('[{"author": "x"}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_texts(p)


class KeywordTests(unittest.TestCase):
    def test_counts_every_occurrence_exactly_with_contexts(self):
        texts = ["쌀 서 말, 쌀 한 말", "도깨비와 쌀", "없음"]
        result = count_keywords(texts, ["쌀", "도깨비", "호랑이"], context=2)
        self.assertEqual(result["쌀"]["count"], 3)
        self.assertEqual(result["도깨비"]["count"], 1)
        self.assertEqual(result["호랑이"], {"count": 0, "contexts": []})
        self.assertEqual(result["쌀"]["contexts"][0], "쌀 서")  # 앞 0자 + 쌀 + 뒤 2자

    def test_does_not_double_count_overlapping_matches(self):
        self.assertEqual(count_keywords(["아아아아"], ["아아"])["아아"]["count"], 2)


class ClassifyTests(FakeServerTest):
    def test_valid_answers_are_classified(self):
        texts = load_texts(SAMPLE)
        items, failures = classify(texts, self.client)
        self.assertEqual(failures, [])
        self.assertEqual({it["category"] for it in items} <= set(CATEGORIES), True)
        self.assertEqual(items[2]["category"], "오류제보")

    def test_unknown_category_and_missing_item_become_failures(self):
        self.fake.answer = lambda prompt: json.dumps({"items": [{"index": 0, "category": "칭찬"}, {"index": 1, "category": "감동"}]})
        items, failures = classify(["좋아요", "최고", "글쎄"], self.client)
        self.assertEqual([it["index"] for it in items], [0])
        self.assertEqual(sorted(f["index"] for f in failures), [1, 2])
        self.assertIn("감동", failures[0]["reason"])
        self.assertIn("없음", failures[1]["reason"])

    def test_broken_batch_fails_every_item_in_it(self):
        self.fake.answer = lambda prompt: "not json"
        items, failures = classify(["a", "b"], self.client)
        self.assertEqual((items, len(failures)), ([], 2))

    def test_large_input_is_split_into_batches_with_global_indexes(self):
        texts = [f"질문 {i}?" for i in range(23)]
        items, failures = classify(texts, self.client, batch_size=10)
        self.assertEqual(len(self.fake.requests), 3)
        self.assertEqual([it["index"] for it in items], list(range(23)))
        self.assertEqual(failures, [])


class SummaryTests(FakeServerTest):
    def test_summary_bullets(self):
        bullets, failure = summarize("본문", self.client)
        self.assertEqual((len(bullets), failure), (3, None))

    def test_too_many_bullets_are_trimmed_with_notice(self):
        self.fake.answer = lambda p: json.dumps({"bullets": ["가", "나", "다", "라"]})
        bullets, failure = summarize("본문", self.client, max_bullets=3)
        self.assertEqual(bullets, ["가", "나", "다"])
        self.assertIn("4개", failure)

    def test_wrong_shape_is_failure(self):
        for answer in [{"bullets": "한 줄"}, {"bullets": []}, {"items": ["가"]}, {"bullets": ["", "나"]}]:
            self.fake.answer = lambda p, a=answer: json.dumps(a)
            bullets, failure = summarize("본문", self.client)
            self.assertEqual(bullets, [])
            self.assertIsNotNone(failure)


class CleanDataTests(FakeServerTest):
    def test_schema_has_counts_failures_keywords_summary_metrics(self):
        texts = load_texts(SAMPLE)
        data = build_clean_data(SAMPLE, texts, self.client, ["쌀", "도깨비"])
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["source"], {"file": "comments_sample.json", "items": 6})
        self.assertEqual(sum(data["classification"]["counts"].values()), 6)
        self.assertEqual(data["keywords"]["도깨비"]["count"], 2)
        self.assertEqual(len(data["summary"]["bullets"]), 3)
        self.assertEqual(data["metrics"]["calls"], 2)
        self.assertNotIn("시청자", json.dumps(data, ensure_ascii=False))


class RunnerTests(FakeServerTest):
    def run_main(self, args, **kw):
        out, err = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as d, redirect_stdout(out), redirect_stderr(err):
            code = runner.main(args, client=self.client, out_root=Path(d), **kw)
            files = sorted(str(p.relative_to(d)) for p in Path(d).rglob("*") if p.is_file())
            contents = {str(p.relative_to(d)): p.read_text(encoding="utf-8") for p in Path(d).rglob("*") if p.is_file()}
        return code, out.getvalue(), err.getvalue(), files, contents

    def test_manual_mode_writes_clean_data_and_instruction(self):
        code, out, err, files, contents = self.run_main(["--input", str(SAMPLE), "--skill", "blog-writer", "--keywords", "쌀,도깨비", "--stage2", "manual"])
        self.assertEqual(code, 0, err)
        self.assertIn("data/processed/clean_data.json", files)
        instruction = next(v for k, v in contents.items() if k.startswith("output/prompts/"))
        self.assertIn("블로그 글 작성 규격", instruction)
        self.assertIn('"classification"', instruction)
        self.assertNotIn("me@example.com", instruction)
        self.assertIn("실측", out)

    def test_headless_mode_saves_claude_output(self):
        code, out, err, files, contents = self.run_main(
            ["--input", str(SAMPLE), "--skill", "scenario-writer", "--stage2", "headless"],
            claude_runner=lambda instruction: "# 시나리오\n본문", which=lambda name: "/usr/bin/claude",
        )
        self.assertEqual(code, 0, err)
        self.assertTrue(any(f.startswith("output/scenario/") for f in files))
        self.assertIn("클로드 코드(claude -p)", out)

    def test_auto_falls_back_to_manual_without_claude_command(self):
        code, out, err, files, _ = self.run_main(["--input", str(SAMPLE), "--skill", "weekly-report"], which=lambda name: None)
        self.assertEqual(code, 0, err)
        self.assertTrue(any(f.startswith("output/prompts/") for f in files))

    def test_headless_failure_is_exit_1_not_silent_success(self):
        def broken(instruction):
            raise RuntimeError("claude -p 실패(종료 코드 1): 로그인 필요")
        code, out, err, files, _ = self.run_main(
            ["--input", str(SAMPLE), "--skill", "blog-writer", "--stage2", "headless"], claude_runner=broken, which=lambda n: "/x/claude")
        self.assertEqual(code, 1)
        self.assertIn("2단계 작성 실패", err)
        self.assertFalse(any(f.startswith("output/blog/") for f in files))

    def test_server_down_is_exit_1_with_hint(self):
        self.client.base_url = "http://127.0.0.1:9"
        self.client.timeout = 1
        code, out, err, files, _ = self.run_main(["--input", str(SAMPLE), "--skill", "blog-writer"])
        self.assertEqual(code, 1)
        self.assertIn("ollama serve", err)
        self.assertEqual(files, [])

    def test_classification_failures_are_warned(self):
        self.fake.answer = lambda p: json.dumps({"items": []}) if "분류하라" in p else json.dumps({"bullets": ["가"]})
        code, out, err, files, _ = self.run_main(["--input", str(SAMPLE), "--skill", "weekly-report", "--stage2", "manual"])
        self.assertEqual(code, 0)
        self.assertIn("분류하지 못한 항목 6건", err)

    def test_bad_arguments_exit_2(self):
        code, *_ = self.run_main(["--input", str(SAMPLE), "--skill", "unknown-skill"])
        self.assertEqual(code, 2)


class SkillFileTests(unittest.TestCase):
    def test_three_skills_have_frontmatter_and_checklist(self):
        for name in ["blog-writer", "scenario-writer", "weekly-report"]:
            text = (ROOT / ".claude" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith(f"---\nname: {name}\ndescription: "), name)
            self.assertIn("끝내기 전 점검", text)
            self.assertIn("clean_data.json", text)


# 가짜 claude 명령 : 받은 인자를 파일에 남기고, FAKE_CLAUDE 값에 따라 claude -p --output-format json 처럼 답한다
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
sys.stdin.read()
open(os.environ["FAKE_CLAUDE_ARGS"], "w", encoding="utf-8").write(json.dumps(sys.argv[1:], ensure_ascii=False))
mode = os.environ.get("FAKE_CLAUDE", "ok")
if mode == "ok":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "# 글\\n본문", "total_cost_usd": 0.01}))
elif mode == "budget":
    print(json.dumps({"type": "result", "subtype": "error_max_budget_usd", "is_error": True, "result": "", "total_cost_usd": 1.2}))
    sys.exit(1)
elif mode == "empty":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "   ", "total_cost_usd": 0.01}))
"""


class ClaudeHeadlessTests(unittest.TestCase):
    """2단계 claude -p 호출 : 도구를 끄고(실측 비용 약 1/5), 결과 JSON 으로 성공을 판정한다(19장)."""

    def setUp(self):
        import os
        self.tmp = tempfile.TemporaryDirectory()
        bin_dir = Path(self.tmp.name)
        exe = bin_dir / "claude"
        exe.write_text(FAKE_CLAUDE, encoding="utf-8")
        exe.chmod(0o755)
        self.args_file = bin_dir / "args.json"
        self.old_env = {k: os.environ.get(k) for k in ("PATH", "FAKE_CLAUDE", "FAKE_CLAUDE_ARGS")}
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
        os.environ["FAKE_CLAUDE_ARGS"] = str(self.args_file)

    def tearDown(self):
        import os
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def test_turns_tools_off_asks_json_and_caps_budget(self):
        runner.run_claude_headless("지시")
        args = json.loads(self.args_file.read_text(encoding="utf-8"))
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertEqual(args[args.index("--output-format") + 1], "json")
        self.assertGreater(float(args[args.index("--max-budget-usd") + 1]), 0)

    def test_returns_only_the_written_text(self):
        # JSON 껍데기 없이 글만, 파일 끝 줄바꿈 하나를 붙여 돌려준다
        self.assertEqual(runner.run_claude_headless("지시"), "# 글\n본문\n")

    def test_budget_stop_is_failure(self):
        import os
        os.environ["FAKE_CLAUDE"] = "budget"
        with self.assertRaises(RuntimeError) as ctx:
            runner.run_claude_headless("지시")
        self.assertIn("error_max_budget_usd", str(ctx.exception))

    def test_success_with_empty_answer_is_failure(self):
        import os
        os.environ["FAKE_CLAUDE"] = "empty"
        with self.assertRaises(RuntimeError):
            runner.run_claude_headless("지시")


if __name__ == "__main__":
    unittest.main()
