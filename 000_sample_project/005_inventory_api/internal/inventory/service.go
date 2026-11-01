package inventory

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"
)

// Service 는 인메모리 재고 저장소이자 업무 규칙을 담당한다.
// 모든 공개 메서드는 mu 로 보호되어 동시에 호출해도 안전하다.
type Service struct {
	mu        sync.Mutex
	items     map[string]*Item
	movements []Movement
	nextID    int
	now       func() time.Time // 테스트에서 시간을 고정하기 위해 주입 가능
}

// NewService 는 비어 있는 재고 서비스를 만든다.
func NewService() *Service {
	return &Service{
		items:  make(map[string]*Item),
		nextID: 1,
		now:    time.Now,
	}
}

// validateItem 은 품목 입력값의 필수 항목과 범위를 검사한다.
func validateItem(in ItemInput) error {
	if strings.TrimSpace(in.Code) == "" || strings.TrimSpace(in.Name) == "" || strings.TrimSpace(in.Unit) == "" {
		return fmt.Errorf("%w: 품번, 품명, 단위는 필수입니다", ErrInvalidInput)
	}
	if in.SafetyStock < 0 {
		return fmt.Errorf("%w: 안전재고는 0 이상이어야 합니다", ErrInvalidInput)
	}
	return nil
}

// CreateItem 은 새 품목을 등록한다. 현재고는 0 으로 시작한다.
func (s *Service) CreateItem(in ItemInput) (Item, error) {
	if err := validateItem(in); err != nil {
		return Item{}, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.items[in.Code]; ok {
		return Item{}, ErrDuplicateCode
	}
	item := &Item{Code: in.Code, Name: in.Name, Unit: in.Unit, SafetyStock: in.SafetyStock}
	s.items[in.Code] = item
	return *item, nil
}

// GetItem 은 품번으로 품목을 조회한다.
func (s *Service) GetItem(code string) (Item, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	item, ok := s.items[code]
	if !ok {
		return Item{}, ErrNotFound
	}
	return *item, nil
}

// ListItems 는 전체 품목을 품번 순으로 반환한다.
func (s *Service) ListItems() []Item {
	s.mu.Lock()
	defer s.mu.Unlock()

	result := make([]Item, 0, len(s.items))
	for _, item := range s.items {
		result = append(result, *item)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Code < result[j].Code })
	return result
}

// UpdateItem 은 품명, 단위, 안전재고를 수정한다. 품번과 현재고는 바뀌지 않는다.
func (s *Service) UpdateItem(code string, in ItemInput) (Item, error) {
	in.Code = code // 경로의 품번을 기준으로 한다
	if err := validateItem(in); err != nil {
		return Item{}, err
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	item, ok := s.items[code]
	if !ok {
		return Item{}, ErrNotFound
	}
	item.Name = in.Name
	item.Unit = in.Unit
	item.SafetyStock = in.SafetyStock
	return *item, nil
}

// DeleteItem 은 품목과 그 품목의 이동 이력을 함께 삭제한다.
func (s *Service) DeleteItem(code string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.items[code]; !ok {
		return ErrNotFound
	}
	delete(s.items, code)

	kept := s.movements[:0]
	for _, m := range s.movements {
		if m.ItemCode != code {
			kept = append(kept, m)
		}
	}
	s.movements = kept
	return nil
}

// RegisterMovement 는 입고(IN) 또는 출고(OUT) 트랜잭션을 등록하고 현재고를 갱신한다.
// 출고 수량이 현재고보다 크면 ErrInsufficientStock 을 반환하고 아무것도 바꾸지 않는다.
func (s *Service) RegisterMovement(code string, in MovementInput) (Movement, error) {
	if in.Type != MovementIn && in.Type != MovementOut {
		return Movement{}, fmt.Errorf("%w: type 은 IN 또는 OUT 이어야 합니다", ErrInvalidInput)
	}
	if in.Quantity <= 0 {
		return Movement{}, ErrInvalidQuantity
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	item, ok := s.items[code]
	if !ok {
		return Movement{}, ErrNotFound
	}

	if in.Type == MovementOut {
		if in.Quantity > item.Stock {
			return Movement{}, ErrInsufficientStock
		}
		item.Stock -= in.Quantity
	} else {
		item.Stock += in.Quantity
	}

	m := Movement{
		ID:           s.nextID,
		ItemCode:     code,
		Type:         in.Type,
		Quantity:     in.Quantity,
		BalanceAfter: item.Stock,
		Note:         in.Note,
		CreatedAt:    s.now(),
	}
	s.nextID++
	s.movements = append(s.movements, m)
	return m, nil
}

// ListMovements 는 품목의 재고 이동 이력을 등록 순서대로 반환한다.
func (s *Service) ListMovements(code string) ([]Movement, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, ok := s.items[code]; !ok {
		return nil, ErrNotFound
	}
	result := []Movement{}
	for _, m := range s.movements {
		if m.ItemCode == code {
			result = append(result, m)
		}
	}
	return result, nil
}

// ListBelowSafetyStock 은 현재고가 안전재고보다 적은 품목을 품번 순으로 반환한다.
func (s *Service) ListBelowSafetyStock() []Item {
	s.mu.Lock()
	defer s.mu.Unlock()

	result := []Item{}
	for _, item := range s.items {
		if item.Stock < item.SafetyStock {
			result = append(result, *item)
		}
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Code < result[j].Code })
	return result
}
