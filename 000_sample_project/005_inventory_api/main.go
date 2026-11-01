// 재고(MM) 관리 REST API 서버의 진입점이다.
package main

import (
	"log"
	"net/http"
	"os"

	"example.com/inventory/internal/inventory"
)

func main() {
	addr := ":8080"
	if v := os.Getenv("ADDR"); v != "" {
		addr = v
	}

	svc := inventory.NewService()
	handler := inventory.NewHandler(svc)

	log.Printf("재고 API 서버 시작: %s", addr)
	if err := http.ListenAndServe(addr, handler); err != nil {
		log.Fatal(err)
	}
}
