package inventory

import (
	"errors"
	"sync"
	"testing"
	"time"
)

// newTestService 는 시간을 고정한 서비스를 만들고 기본 품목 하나를 등록한다.
func newTestService(t *testing.T) *Service {
	t.Helper()
	s := NewService()
	s.now = func() time.Time { return time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC) }
	if _, err := s.CreateItem(ItemInput{Code: "P-001", Name: "볼트", Unit: "EA", SafetyStock: 10}); err != nil {
		t.Fatalf("기본 품목 생성 실패: %v", err)
	}
	return s
}

func TestCreateItem(t *testing.T) {
	tests := []struct {
		name    string
		input   ItemInput
		wantErr error
	}{
		{"정상 등록", ItemInput{Code: "P-002", Name: "너트", Unit: "EA", SafetyStock: 5}, nil},
		{"품번 중복", ItemInput{Code: "P-001", Name: "볼트2", Unit: "EA"}, ErrDuplicateCode},
		{"품번 누락", ItemInput{Name: "너트", Unit: "EA"}, ErrInvalidInput},
		{"품명 누락", ItemInput{Code: "P-003", Unit: "EA"}, ErrInvalidInput},
		{"단위 누락", ItemInput{Code: "P-004", Name: "와셔"}, ErrInvalidInput},
		{"안전재고 음수", ItemInput{Code: "P-005", Name: "와셔", Unit: "EA", SafetyStock: -1}, ErrInvalidInput},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newTestService(t)
			item, err := s.CreateItem(tt.input)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("오류 = %v, 기대값 %v", err, tt.wantErr)
			}
			if err == nil && (item.Code != tt.input.Code || item.Stock != 0) {
				t.Errorf("생성 결과가 잘못됨: %+v", item)
			}
		})
	}
}

func TestGetUpdateDeleteItem(t *testing.T) {
	tests := []struct {
		name    string
		code    string
		wantErr error
	}{
		{"존재하는 품목", "P-001", nil},
		{"없는 품목", "NOPE", ErrNotFound},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newTestService(t)

			if _, err := s.GetItem(tt.code); !errors.Is(err, tt.wantErr) {
				t.Errorf("GetItem 오류 = %v, 기대값 %v", err, tt.wantErr)
			}

			updated, err := s.UpdateItem(tt.code, ItemInput{Name: "육각볼트", Unit: "BOX", SafetyStock: 3})
			if !errors.Is(err, tt.wantErr) {
				t.Errorf("UpdateItem 오류 = %v, 기대값 %v", err, tt.wantErr)
			}
			if err == nil && (updated.Name != "육각볼트" || updated.Unit != "BOX" || updated.SafetyStock != 3) {
				t.Errorf("수정 결과가 잘못됨: %+v", updated)
			}

			if err := s.DeleteItem(tt.code); !errors.Is(err, tt.wantErr) {
				t.Errorf("DeleteItem 오류 = %v, 기대값 %v", err, tt.wantErr)
			}
			if tt.wantErr == nil {
				if _, err := s.GetItem(tt.code); !errors.Is(err, ErrNotFound) {
					t.Errorf("삭제 후 조회 오류 = %v, 기대값 ErrNotFound", err)
				}
			}
		})
	}
}

func TestUpdateItemValidation(t *testing.T) {
	s := newTestService(t)
	if _, err := s.UpdateItem("P-001", ItemInput{Name: "", Unit: "EA"}); !errors.Is(err, ErrInvalidInput) {
		t.Errorf("품명 없이 수정 시 오류 = %v, 기대값 ErrInvalidInput", err)
	}
}

func TestRegisterMovement(t *testing.T) {
	tests := []struct {
		name      string
		code      string
		setupIn   int // 사전에 입고해 둘 수량 (0 이면 생략)
		input     MovementInput
		wantErr   error
		wantStock int // 처리 후 기대 현재고
	}{
		{"입고 정상", "P-001", 0, MovementInput{Type: MovementIn, Quantity: 30}, nil, 30},
		{"출고 정상", "P-001", 30, MovementInput{Type: MovementOut, Quantity: 20}, nil, 10},
		{"현재고 전량 출고", "P-001", 30, MovementInput{Type: MovementOut, Quantity: 30}, nil, 0},
		{"현재고 초과 출고 거부", "P-001", 30, MovementInput{Type: MovementOut, Quantity: 31}, ErrInsufficientStock, 30},
		{"재고 없음 출고 거부", "P-001", 0, MovementInput{Type: MovementOut, Quantity: 1}, ErrInsufficientStock, 0},
		{"수량 0 거부", "P-001", 0, MovementInput{Type: MovementIn, Quantity: 0}, ErrInvalidQuantity, 0},
		{"수량 음수 거부", "P-001", 0, MovementInput{Type: MovementIn, Quantity: -5}, ErrInvalidQuantity, 0},
		{"잘못된 유형 거부", "P-001", 0, MovementInput{Type: "MOVE", Quantity: 1}, ErrInvalidInput, 0},
		{"없는 품목", "NOPE", 0, MovementInput{Type: MovementIn, Quantity: 1}, ErrNotFound, 0},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newTestService(t)
			if tt.setupIn > 0 {
				if _, err := s.RegisterMovement("P-001", MovementInput{Type: MovementIn, Quantity: tt.setupIn}); err != nil {
					t.Fatalf("사전 입고 실패: %v", err)
				}
			}

			m, err := s.RegisterMovement(tt.code, tt.input)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("오류 = %v, 기대값 %v", err, tt.wantErr)
			}
			if err == nil && m.BalanceAfter != tt.wantStock {
				t.Errorf("처리 후 재고 = %d, 기대값 %d", m.BalanceAfter, tt.wantStock)
			}
			if tt.code == "P-001" {
				item, _ := s.GetItem("P-001")
				if item.Stock != tt.wantStock {
					t.Errorf("현재고 = %d, 기대값 %d", item.Stock, tt.wantStock)
				}
			}
		})
	}
}

func TestListMovements(t *testing.T) {
	s := newTestService(t)
	s.RegisterMovement("P-001", MovementInput{Type: MovementIn, Quantity: 50, Note: "구매입고"})
	s.RegisterMovement("P-001", MovementInput{Type: MovementOut, Quantity: 15, Note: "생산출고"})
	s.RegisterMovement("P-001", MovementInput{Type: MovementOut, Quantity: 100}) // 거부되어 이력에 남지 않아야 함

	list, err := s.ListMovements("P-001")
	if err != nil {
		t.Fatalf("이력 조회 실패: %v", err)
	}
	if len(list) != 2 {
		t.Fatalf("이력 건수 = %d, 기대값 2", len(list))
	}
	if list[0].Type != MovementIn || list[0].BalanceAfter != 50 || list[0].ID != 1 {
		t.Errorf("첫 이력이 잘못됨: %+v", list[0])
	}
	// 이동 번호는 1, 2 로 이어져야 한다. 번호가 겹치면 이력을 하나로 가리킬 수 없다.
	if list[1].Type != MovementOut || list[1].BalanceAfter != 35 || list[1].Note != "생산출고" || list[1].ID != 2 {
		t.Errorf("두 번째 이력이 잘못됨: %+v", list[1])
	}

	if _, err := s.ListMovements("NOPE"); !errors.Is(err, ErrNotFound) {
		t.Errorf("없는 품목 이력 조회 오류 = %v, 기대값 ErrNotFound", err)
	}

	// 품목 삭제 시 이력도 함께 사라진다
	s.DeleteItem("P-001")
	s.CreateItem(ItemInput{Code: "P-001", Name: "볼트", Unit: "EA"})
	list, _ = s.ListMovements("P-001")
	if len(list) != 0 {
		t.Errorf("재등록 품목의 이력 건수 = %d, 기대값 0", len(list))
	}
}

func TestListBelowSafetyStock(t *testing.T) {
	tests := []struct {
		name      string
		stock     int // P-001(안전재고 10)에 입고할 수량
		wantCodes []string
	}{
		{"재고 0 이면 미달", 0, []string{"P-001", "P-003"}},
		{"안전재고 미만이면 미달", 9, []string{"P-001", "P-003"}},
		{"안전재고와 같으면 정상", 10, []string{"P-003"}},
		{"안전재고 초과면 정상", 11, []string{"P-003"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := newTestService(t)
			s.CreateItem(ItemInput{Code: "P-002", Name: "너트", Unit: "EA", SafetyStock: 0}) // 안전재고 0 은 미달 아님
			s.CreateItem(ItemInput{Code: "P-003", Name: "와셔", Unit: "EA", SafetyStock: 1})
			if tt.stock > 0 {
				s.RegisterMovement("P-001", MovementInput{Type: MovementIn, Quantity: tt.stock})
			}

			got := s.ListBelowSafetyStock()
			if len(got) != len(tt.wantCodes) {
				t.Fatalf("미달 품목 = %+v, 기대 품번 %v", got, tt.wantCodes)
			}
			for i, code := range tt.wantCodes {
				if got[i].Code != code {
					t.Errorf("%d번째 품번 = %s, 기대값 %s", i, got[i].Code, code)
				}
			}
		})
	}
}

// 여러 고루틴이 동시에 출고해도 재고가 음수가 되지 않아야 한다.
func TestConcurrentMovements(t *testing.T) {
	s := newTestService(t)
	s.RegisterMovement("P-001", MovementInput{Type: MovementIn, Quantity: 100})

	var wg sync.WaitGroup
	var mu sync.Mutex
	success := 0
	for i := 0; i < 200; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if _, err := s.RegisterMovement("P-001", MovementInput{Type: MovementOut, Quantity: 1}); err == nil {
				mu.Lock()
				success++
				mu.Unlock()
			}
		}()
	}
	wg.Wait()

	item, _ := s.GetItem("P-001")
	if success != 100 || item.Stock != 0 {
		t.Errorf("성공 출고 = %d, 현재고 = %d (기대값 100, 0)", success, item.Stock)
	}
}
