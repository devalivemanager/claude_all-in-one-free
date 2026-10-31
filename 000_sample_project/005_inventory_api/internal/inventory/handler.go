package inventory

import (
	"encoding/json"
	"errors"
	"net/http"
)

// NewHandler 는 재고 API 라우팅이 등록된 http.Handler 를 만든다.
// Go 1.22+ 의 "메서드 경로" 패턴과 {code} 경로 변수를 사용한다.
func NewHandler(svc *Service) http.Handler {
	h := &handler{svc: svc}
	mux := http.NewServeMux()

	// 품목 CRUD
	mux.HandleFunc("POST /items", h.createItem)
	mux.HandleFunc("GET /items", h.listItems)
	mux.HandleFunc("GET /items/{code}", h.getItem)
	mux.HandleFunc("PUT /items/{code}", h.updateItem)
	mux.HandleFunc("DELETE /items/{code}", h.deleteItem)

	// 입출고 및 재고 조회
	mux.HandleFunc("POST /items/{code}/movements", h.registerMovement)
	mux.HandleFunc("GET /items/{code}/movements", h.listMovements)
	mux.HandleFunc("GET /items/{code}/stock", h.getStock)

	// 안전재고 미달 품목
	mux.HandleFunc("GET /reports/below-safety-stock", h.belowSafetyStock)

	return mux
}

type handler struct {
	svc *Service
}

// stockResponse 는 현재고 조회 응답 형식이다.
type stockResponse struct {
	Code        string `json:"code"`
	Stock       int    `json:"stock"`
	Unit        string `json:"unit"`
	SafetyStock int    `json:"safetyStock"`
	BelowSafety bool   `json:"belowSafety"`
}

func (h *handler) createItem(w http.ResponseWriter, r *http.Request) {
	var in ItemInput
	if !decodeJSON(w, r, &in) {
		return
	}
	item, err := h.svc.CreateItem(in)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, item)
}

func (h *handler) listItems(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, h.svc.ListItems())
}

func (h *handler) getItem(w http.ResponseWriter, r *http.Request) {
	item, err := h.svc.GetItem(r.PathValue("code"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, item)
}

func (h *handler) updateItem(w http.ResponseWriter, r *http.Request) {
	var in ItemInput
	if !decodeJSON(w, r, &in) {
		return
	}
	item, err := h.svc.UpdateItem(r.PathValue("code"), in)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, item)
}

func (h *handler) deleteItem(w http.ResponseWriter, r *http.Request) {
	if err := h.svc.DeleteItem(r.PathValue("code")); err != nil {
		writeError(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (h *handler) registerMovement(w http.ResponseWriter, r *http.Request) {
	var in MovementInput
	if !decodeJSON(w, r, &in) {
		return
	}
	m, err := h.svc.RegisterMovement(r.PathValue("code"), in)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, m)
}

func (h *handler) listMovements(w http.ResponseWriter, r *http.Request) {
	list, err := h.svc.ListMovements(r.PathValue("code"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, list)
}

func (h *handler) getStock(w http.ResponseWriter, r *http.Request) {
	item, err := h.svc.GetItem(r.PathValue("code"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, stockResponse{
		Code:        item.Code,
		Stock:       item.Stock,
		Unit:        item.Unit,
		SafetyStock: item.SafetyStock,
		BelowSafety: item.Stock < item.SafetyStock,
	})
}

func (h *handler) belowSafetyStock(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, h.svc.ListBelowSafetyStock())
}

// decodeJSON 은 요청 본문을 읽어 v 에 채운다. 실패하면 400 을 쓰고 false 를 반환한다.
func decodeJSON(w http.ResponseWriter, r *http.Request, v any) bool {
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	if err := dec.Decode(v); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "잘못된 JSON 요청입니다"})
		return false
	}
	return true
}

// writeError 는 도메인 오류를 알맞은 HTTP 상태 코드로 변환해 응답한다.
func writeError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	switch {
	case errors.Is(err, ErrNotFound):
		status = http.StatusNotFound
	case errors.Is(err, ErrDuplicateCode), errors.Is(err, ErrInsufficientStock):
		status = http.StatusConflict
	case errors.Is(err, ErrInvalidInput), errors.Is(err, ErrInvalidQuantity):
		status = http.StatusBadRequest
	}
	writeJSON(w, status, map[string]string{"error": err.Error()})
}

// writeJSON 은 상태 코드와 함께 v 를 JSON 으로 응답한다.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}
