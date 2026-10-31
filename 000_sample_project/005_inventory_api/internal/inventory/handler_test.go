package inventory

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// doRequest 는 핸들러에 요청을 보내고 응답 기록기를 반환한다.
func doRequest(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// newTestHandler 는 품목 P-001(안전재고 10)과 입고 20 이 있는 핸들러를 만든다.
func newTestHandler(t *testing.T) http.Handler {
	t.Helper()
	s := newTestService(t)
	if _, err := s.RegisterMovement("P-001", MovementInput{Type: MovementIn, Quantity: 20}); err != nil {
		t.Fatalf("사전 입고 실패: %v", err)
	}
	return NewHandler(s)
}

func TestHandlerStatusCodes(t *testing.T) {
	tests := []struct {
		name       string
		method     string
		path       string
		body       string
		wantStatus int
	}{
		{"품목 등록", "POST", "/items", `{"code":"P-002","name":"너트","unit":"EA","safetyStock":5}`, http.StatusCreated},
		{"품목 등록 중복", "POST", "/items", `{"code":"P-001","name":"볼트","unit":"EA"}`, http.StatusConflict},
		{"품목 등록 필수값 누락", "POST", "/items", `{"code":"P-009"}`, http.StatusBadRequest},
		{"품목 등록 잘못된 JSON", "POST", "/items", `{bad json`, http.StatusBadRequest},
		{"품목 목록", "GET", "/items", "", http.StatusOK},
		{"품목 조회", "GET", "/items/P-001", "", http.StatusOK},
		{"없는 품목 조회", "GET", "/items/NOPE", "", http.StatusNotFound},
		{"품목 수정", "PUT", "/items/P-001", `{"name":"육각볼트","unit":"EA","safetyStock":3}`, http.StatusOK},
		{"없는 품목 수정", "PUT", "/items/NOPE", `{"name":"x","unit":"EA"}`, http.StatusNotFound},
		{"품목 삭제", "DELETE", "/items/P-001", "", http.StatusNoContent},
		{"없는 품목 삭제", "DELETE", "/items/NOPE", "", http.StatusNotFound},
		{"입고 등록", "POST", "/items/P-001/movements", `{"type":"IN","quantity":5}`, http.StatusCreated},
		{"출고 등록", "POST", "/items/P-001/movements", `{"type":"OUT","quantity":20}`, http.StatusCreated},
		{"현재고 초과 출고", "POST", "/items/P-001/movements", `{"type":"OUT","quantity":21}`, http.StatusConflict},
		{"수량 0", "POST", "/items/P-001/movements", `{"type":"IN","quantity":0}`, http.StatusBadRequest},
		{"수량 음수", "POST", "/items/P-001/movements", `{"type":"OUT","quantity":-1}`, http.StatusBadRequest},
		{"없는 품목 입고", "POST", "/items/NOPE/movements", `{"type":"IN","quantity":1}`, http.StatusNotFound},
		{"이력 조회", "GET", "/items/P-001/movements", "", http.StatusOK},
		{"없는 품목 이력", "GET", "/items/NOPE/movements", "", http.StatusNotFound},
		{"현재고 조회", "GET", "/items/P-001/stock", "", http.StatusOK},
		{"없는 품목 현재고", "GET", "/items/NOPE/stock", "", http.StatusNotFound},
		{"안전재고 미달", "GET", "/reports/below-safety-stock", "", http.StatusOK},
		{"허용되지 않은 메서드", "PATCH", "/items/P-001", "", http.StatusMethodNotAllowed},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h := newTestHandler(t)
			rec := doRequest(t, h, tt.method, tt.path, tt.body)
			if rec.Code != tt.wantStatus {
				t.Errorf("상태 코드 = %d, 기대값 %d (본문: %s)", rec.Code, tt.wantStatus, rec.Body.String())
			}
		})
	}
}

// 입고 → 출고 → 현재고/이력/미달 조회까지 하나의 흐름으로 응답 본문을 검증한다.
func TestHandlerInventoryFlow(t *testing.T) {
	h := NewHandler(NewService())

	rec := doRequest(t, h, "POST", "/items", `{"code":"M-100","name":"강판","unit":"KG","safetyStock":50}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("품목 등록 실패: %d %s", rec.Code, rec.Body.String())
	}

	doRequest(t, h, "POST", "/items/M-100/movements", `{"type":"IN","quantity":80,"note":"구매입고"}`)
	rec = doRequest(t, h, "POST", "/items/M-100/movements", `{"type":"OUT","quantity":40,"note":"생산출고"}`)
	var m Movement
	if err := json.NewDecoder(rec.Body).Decode(&m); err != nil {
		t.Fatalf("출고 응답 파싱 실패: %v", err)
	}
	if m.Type != MovementOut || m.BalanceAfter != 40 {
		t.Errorf("출고 응답이 잘못됨: %+v", m)
	}

	// 현재고 40 < 안전재고 50 이므로 미달 상태
	rec = doRequest(t, h, "GET", "/items/M-100/stock", "")
	var stock stockResponse
	json.NewDecoder(rec.Body).Decode(&stock)
	if stock.Stock != 40 || !stock.BelowSafety || stock.Unit != "KG" {
		t.Errorf("현재고 응답이 잘못됨: %+v", stock)
	}

	rec = doRequest(t, h, "GET", "/items/M-100/movements", "")
	var list []Movement
	json.NewDecoder(rec.Body).Decode(&list)
	if len(list) != 2 || list[0].Note != "구매입고" || list[1].Note != "생산출고" {
		t.Errorf("이력 응답이 잘못됨: %+v", list)
	}

	rec = doRequest(t, h, "GET", "/reports/below-safety-stock", "")
	var below []Item
	json.NewDecoder(rec.Body).Decode(&below)
	if len(below) != 1 || below[0].Code != "M-100" {
		t.Errorf("안전재고 미달 응답이 잘못됨: %+v", below)
	}

	// 초과 출고는 409 이고 재고는 그대로여야 한다
	rec = doRequest(t, h, "POST", "/items/M-100/movements", `{"type":"OUT","quantity":41}`)
	if rec.Code != http.StatusConflict {
		t.Errorf("초과 출고 상태 코드 = %d, 기대값 409", rec.Code)
	}
	rec = doRequest(t, h, "GET", "/items/M-100", "")
	var item Item
	json.NewDecoder(rec.Body).Decode(&item)
	if item.Stock != 40 {
		t.Errorf("초과 출고 후 현재고 = %d, 기대값 40", item.Stock)
	}
}
