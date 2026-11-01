// 서버 진입점: 샘플 데이터를 넣고 HTTP 서버를 띄운다
import { createApp } from "./app.js";
import { TodoService, toDateString } from "./todoService.js";

const PORT = Number(process.env.PORT ?? 3000);

/** 오늘 기준으로 days 일 뒤 날짜 (음수면 과거) */
function daysFromToday(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return toDateString(date);
}

const service = new TodoService();
// 화면을 바로 확인할 수 있도록 샘플 데이터를 넣어 둔다
service.create({ title: "주간 보고서 작성", assignee: "김민수", priority: "high", dueDate: daysFromToday(-2) });
service.create({ title: "신규 입사자 온보딩 자료 준비", assignee: "이지은", priority: "medium", dueDate: daysFromToday(3) });
service.create({ title: "회의실 예약 확인", assignee: "김민수", priority: "low", dueDate: daysFromToday(1) });
service.create({ title: "고객 문의 답변", assignee: "박서준", priority: "high", completed: true, dueDate: daysFromToday(-1) });

createApp(service).listen(PORT, () => {
  console.log(`업무 할 일 관리 앱이 http://localhost:${PORT} 에서 실행 중입니다.`);
});
