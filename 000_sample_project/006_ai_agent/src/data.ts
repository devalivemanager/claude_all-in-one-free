// 인메모리 목업 데이터: 실제 HR/회계 시스템 대신 사용하는 고정 데이터

export interface Employee {
  id: string;
  name: string;
  department: string;
  position: string;
  email: string;
}

export interface LeaveBalance {
  employeeId: string;
  totalDays: number;
  usedDays: number;
}

export interface ExpensePolicy {
  category: string;
  label: string;
  // 1건당 최대 신청 가능 금액(원)
  limitPerClaim: number;
  receiptRequired: boolean;
  note: string;
}

export const employees: Employee[] = [
  { id: 'E001', name: '김민준', department: '개발팀', position: '선임', email: 'minjun.kim@example.com' },
  { id: 'E002', name: '이서연', department: '재무팀', position: '팀장', email: 'seoyeon.lee@example.com' },
  { id: 'E003', name: '박지호', department: '영업팀', position: '사원', email: 'jiho.park@example.com' },
];

export const leaveBalances: LeaveBalance[] = [
  { employeeId: 'E001', totalDays: 15, usedDays: 4.5 },
  { employeeId: 'E002', totalDays: 20, usedDays: 12 },
  { employeeId: 'E003', totalDays: 11, usedDays: 0 },
];

export const expensePolicies: ExpensePolicy[] = [
  { category: 'meal', label: '식대', limitPerClaim: 30000, receiptRequired: true, note: '야근·출장 시 1인 1식 기준' },
  { category: 'taxi', label: '교통비(택시)', limitPerClaim: 50000, receiptRequired: true, note: '22시 이후 퇴근 또는 업무 이동 시' },
  { category: 'travel', label: '출장 숙박비', limitPerClaim: 150000, receiptRequired: true, note: '1박 기준, 사전 출장 승인 필요' },
  { category: 'education', label: '교육비', limitPerClaim: 500000, receiptRequired: true, note: '직무 관련 교육에 한함' },
];
