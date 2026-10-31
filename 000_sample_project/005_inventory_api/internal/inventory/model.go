// Package inventory 는 품목 마스터와 입출고 트랜잭션을 관리하는 재고 도메인 패키지다.
package inventory

import (
	"errors"
	"time"
)

// MovementType 은 재고 이동 유형(입고/출고)이다.
type MovementType string

const (
	MovementIn  MovementType = "IN"  // 입고
	MovementOut MovementType = "OUT" // 출고
)

// Item 은 품목 마스터 정보와 현재고를 담는다.
type Item struct {
	Code        string `json:"code"`        // 품번
	Name        string `json:"name"`        // 품명
	Unit        string `json:"unit"`        // 단위 (예: EA, KG)
	SafetyStock int    `json:"safetyStock"` // 안전재고
	Stock       int    `json:"stock"`       // 현재고 (입출고로만 변경)
}

// ItemInput 은 품목 생성·수정 요청 값이다. 현재고는 직접 수정할 수 없다.
type ItemInput struct {
	Code        string `json:"code"`
	Name        string `json:"name"`
	Unit        string `json:"unit"`
	SafetyStock int    `json:"safetyStock"`
}

// Movement 는 한 건의 입고 또는 출고 트랜잭션 기록이다.
type Movement struct {
	ID           int          `json:"id"`
	ItemCode     string       `json:"itemCode"`
	Type         MovementType `json:"type"`
	Quantity     int          `json:"quantity"`
	BalanceAfter int          `json:"balanceAfter"` // 처리 후 재고
	Note         string       `json:"note,omitempty"`
	CreatedAt    time.Time    `json:"createdAt"`
}

// MovementInput 은 입출고 등록 요청 값이다.
type MovementInput struct {
	Type     MovementType `json:"type"`
	Quantity int          `json:"quantity"`
	Note     string       `json:"note"`
}

// 서비스가 반환하는 도메인 오류. 핸들러에서 HTTP 상태 코드로 변환한다.
var (
	ErrNotFound          = errors.New("품목을 찾을 수 없습니다")
	ErrDuplicateCode     = errors.New("이미 존재하는 품번입니다")
	ErrInvalidInput      = errors.New("입력값이 올바르지 않습니다")
	ErrInvalidQuantity   = errors.New("수량은 양수여야 합니다")
	ErrInsufficientStock = errors.New("출고 수량이 현재고보다 많습니다")
)
