package tenantmcp

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// Rates runs one PromQL instant query that yields a single number. found is false when the query
// matched no series, which for a request counter means no traffic in the window.
type Rates interface {
	Rate(ctx context.Context, promql string) (value float64, found bool, err error)
}

// Rejections is a tenant's traffic at the BNK front door over the last minute.
type Rejections struct {
	Project      string  `json:"project" jsonschema:"Run:ai project name."`
	RejectedRPS  float64 `json:"rejectedRps" jsonschema:"Requests per second BNK refused with 429 over the last minute."`
	ServedRPS    float64 `json:"servedRps" jsonschema:"Requests per second that got a 2xx answer over the last minute."`
	OfferedRPS   float64 `json:"offeredRps" jsonschema:"rejectedRps + servedRps: the traffic the tenant is sending."`
	RateLimitRPS float64 `json:"rateLimitRps,omitempty" jsonschema:"The tenant's BNK limit in requests per second, from its iRule."`
	Throttled    bool    `json:"throttled" jsonschema:"True when BNK is refusing any of the tenant's requests."`
	Window       string  `json:"window" jsonschema:"The rate window the numbers cover."`
}

const rateWindow = "1m"

// The project name is validated as a DNS label before it reaches these, so it can't escape the label value.
func rejectedQuery(project string) string {
	return fmt.Sprintf(`sum(rate(bnk_requests_total{project=%q,code="429"}[%s]))`, project, rateWindow)
}

func servedQuery(project string) string {
	return fmt.Sprintf(`sum(rate(bnk_requests_total{project=%q,code=~"2.."}[%s]))`, project, rateWindow)
}

// Rejections reports how much of a tenant's traffic BNK is refusing, next to its rate limit.
func (t *Tools) Rejections(ctx context.Context, project string) (Rejections, error) {
	if err := validProject(project); err != nil {
		return Rejections{}, err
	}
	if t.Rates == nil {
		return Rejections{}, errors.New("this server has no Prometheus configured (--prometheus-url), so it can't report 429 rates")
	}
	// The front door read also confirms the tenant exists and is one the controller manages.
	fd, err := t.FrontDoor(ctx, project)
	if err != nil {
		return Rejections{}, err
	}
	rejected, _, err := t.Rates.Rate(ctx, rejectedQuery(project))
	if err != nil {
		return Rejections{}, fmt.Errorf("query 429 rate: %w", err)
	}
	served, _, err := t.Rates.Rate(ctx, servedQuery(project))
	if err != nil {
		return Rejections{}, fmt.Errorf("query served rate: %w", err)
	}
	return Rejections{
		Project:      project,
		RejectedRPS:  rejected,
		ServedRPS:    served,
		OfferedRPS:   rejected + served,
		RateLimitRPS: fd.RateLimitRPS,
		Throttled:    rejected > 0,
		Window:       rateWindow,
	}, nil
}

// PrometheusRates queries a Prometheus server's HTTP API.
type PrometheusRates struct {
	BaseURL string
	Client  *http.Client
}

// Rate runs an instant query and returns its single scalar or vector value.
func (p *PrometheusRates) Rate(ctx context.Context, promql string) (float64, bool, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		p.BaseURL+"/api/v1/query?"+url.Values{"query": {promql}}.Encode(), nil)
	if err != nil {
		return 0, false, err
	}
	c := p.Client
	if c == nil {
		c = http.DefaultClient
	}
	resp, err := c.Do(req)
	if err != nil {
		return 0, false, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return 0, false, err
	}
	if resp.StatusCode != http.StatusOK {
		return 0, false, fmt.Errorf("prometheus answered %s", resp.Status)
	}
	var out struct {
		Status string `json:"status"`
		Data   struct {
			Result []struct {
				Value [2]any `json:"value"`
			} `json:"result"`
		} `json:"data"`
	}
	if err := json.Unmarshal(body, &out); err != nil {
		return 0, false, fmt.Errorf("decode prometheus answer: %w", err)
	}
	if out.Status != "success" {
		return 0, false, fmt.Errorf("prometheus status %q", out.Status)
	}
	if len(out.Data.Result) == 0 {
		return 0, false, nil
	}
	s, ok := out.Data.Result[0].Value[1].(string)
	if !ok {
		return 0, false, errors.New("prometheus value is not a string")
	}
	v, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, false, fmt.Errorf("parse prometheus value %q: %w", s, err)
	}
	return v, true, nil
}
