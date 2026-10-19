package tenantmcp

import (
	"context"
	"errors"
	"strings"
	"testing"
)

// fakeRates answers rate queries from a map keyed by the PromQL it receives, and records every query.
type fakeRates struct {
	byQuery map[string]float64
	err     error
	seen    []string
}

func (f *fakeRates) Rate(_ context.Context, promql string) (float64, bool, error) {
	f.seen = append(f.seen, promql)
	if f.err != nil {
		return 0, false, f.err
	}
	v, ok := f.byQuery[promql]
	return v, ok, nil
}

func TestRejections(t *testing.T) {
	tools := fixture(t)
	rates := &fakeRates{byQuery: map[string]float64{
		rejectedQuery("team-a"): 22.5,
		servedQuery("team-a"):   40,
	}}
	tools.Rates = rates

	r, err := tools.Rejections(context.Background(), "team-a")
	if err != nil {
		t.Fatal(err)
	}
	if r.RejectedRPS != 22.5 || r.ServedRPS != 40 || r.OfferedRPS != 62.5 || r.RateLimitRPS != 40 || !r.Throttled {
		t.Errorf("rejections = %+v", r)
	}
	for _, q := range rates.seen {
		if !strings.Contains(q, `project="team-a"`) {
			t.Errorf("query not scoped to the project: %s", q)
		}
	}
}

func TestRejectionsNoTrafficIsZeroNotThrottled(t *testing.T) {
	tools := fixture(t)
	tools.Rates = &fakeRates{byQuery: map[string]float64{}}
	r, err := tools.Rejections(context.Background(), "team-a")
	if err != nil {
		t.Fatal(err)
	}
	if r.RejectedRPS != 0 || r.Throttled {
		t.Errorf("no series must read as 0 and not throttled: %+v", r)
	}
}

func TestRejectionsRefusesBadNamesBeforeQuerying(t *testing.T) {
	tools := fixture(t)
	rates := &fakeRates{}
	tools.Rates = rates
	for _, p := range []string{`team-a"}`, `x",code=~".+`, "Team-A", ""} {
		if _, err := tools.Rejections(context.Background(), p); !errors.Is(err, ErrInvalidProject) {
			t.Errorf("%q: want ErrInvalidProject, got %v", p, err)
		}
	}
	if len(rates.seen) != 0 {
		t.Errorf("no query may reach Prometheus for an invalid name, got %v", rates.seen)
	}
}

func TestRejectionsUnmanagedTenant(t *testing.T) {
	tools := fixture(t)
	tools.Rates = &fakeRates{}
	if _, err := tools.Rejections(context.Background(), "not-ours"); err == nil {
		t.Error("a Gateway the controller doesn't manage must read as no tenant")
	}
}

func TestRejectionsPrometheusDown(t *testing.T) {
	tools := fixture(t)
	tools.Rates = &fakeRates{err: errors.New("connection refused")}
	if _, err := tools.Rejections(context.Background(), "team-a"); err == nil {
		t.Error("a Prometheus failure must be an error, not a zero rate")
	}
}

func TestRejectionsWithoutPrometheusConfigured(t *testing.T) {
	tools := fixture(t)
	if _, err := tools.Rejections(context.Background(), "team-a"); err == nil {
		t.Error("with no Prometheus configured the tool must say so")
	}
}
