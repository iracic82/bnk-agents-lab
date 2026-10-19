package tenantmcp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

// Prometheus' instant-query answers, as /api/v1/query returns them.
func promServer(t *testing.T, status int, body string, gotQuery *string) *httptest.Server {
	t.Helper()
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/query" {
			t.Errorf("path = %s", r.URL.Path)
		}
		if gotQuery != nil {
			*gotQuery = r.URL.Query().Get("query")
		}
		w.WriteHeader(status)
		_, _ = w.Write([]byte(body))
	}))
	t.Cleanup(ts.Close)
	return ts
}

func TestPrometheusRatesVector(t *testing.T) {
	var q string
	ts := promServer(t, 200, `{"status":"success","data":{"resultType":"vector","result":[{"metric":{},"value":[1760000000.1,"22.5"]}]}}`, &q)
	v, found, err := (&PrometheusRates{BaseURL: ts.URL}).Rate(context.Background(), rejectedQuery("tenant-b"))
	if err != nil || !found || v != 22.5 {
		t.Fatalf("got %v %v %v", v, found, err)
	}
	if q != `sum(rate(bnk_requests_total{project="tenant-b",code="429"}[1m]))` {
		t.Errorf("query sent = %s", q)
	}
}

func TestPrometheusRatesEmptyIsNotFound(t *testing.T) {
	ts := promServer(t, 200, `{"status":"success","data":{"resultType":"vector","result":[]}}`, nil)
	v, found, err := (&PrometheusRates{BaseURL: ts.URL}).Rate(context.Background(), "x")
	if err != nil || found || v != 0 {
		t.Fatalf("got %v %v %v", v, found, err)
	}
}

func TestPrometheusRatesErrors(t *testing.T) {
	for name, tc := range map[string]struct {
		status int
		body   string
	}{
		"http 503":      {503, `{"status":"error"}`},
		"status error":  {200, `{"status":"error","error":"bad query"}`},
		"not json":      {200, `<html>`},
		"value non-num": {200, `{"status":"success","data":{"result":[{"value":[1,"abc"]}]}}`},
	} {
		ts := promServer(t, tc.status, tc.body, nil)
		if _, _, err := (&PrometheusRates{BaseURL: ts.URL}).Rate(context.Background(), "x"); err == nil {
			t.Errorf("%s: want an error", name)
		}
	}
}
